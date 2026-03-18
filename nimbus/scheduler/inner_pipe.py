import math
import os
import threading
import time

import ray

from nimbus.daemon.status_monitor import StatusMonitor
from nimbus.scheduler.stages import DedumpStage, DumpStage
from nimbus.utils.logging import configure_logging
from nimbus.utils.random import set_all_seeds
from nimbus.utils.types import MONITOR_CHECK_INTERVAL, STATUS_TIMEOUTS, StageInput
from nimbus.utils.utils import init_env, pipe_consume_stage


def iter_to_obj(iter_obj):
    return pipe_consume_stage(iter_obj), True


def _consume_N(iter_obj, N=1):
    print("consume: ", iter_obj)
    results = []
    finish = False
    for _ in range(N):
        try:
            obj = next(iter_obj)
            results.append(obj)
        except StopIteration:
            finish = True
    return results, finish


def consume_N(stage_input):
    finish = False
    if hasattr(stage_input, "Args"):
        stage_input.Args, finish = _consume_N(stage_input.Args[0])
    if hasattr(stage_input, "Kwargs"):
        if stage_input.Kwargs is not None:
            stage_input.Kwargs = {key: _consume_N(value) for key, value in stage_input.Kwargs.items()}
    return stage_input, finish


class PipeWorkerGroup:
    """
    Manages a group of pipe workers and their supervisors.
    Supports dynamic worker spawning for worker_schedule feature.
    """

    def __init__(
        self,
        pipe_name,
        exp_name,
        pipe_num,
        stage_list,
        master_seed,
        supervisor_class,
        inner_pipe_class,
        initial_instances=0,
    ):
        self.workers = {}
        self._next_worker_idx = 0
        self.pipe_name = pipe_name
        self.exp_name = exp_name
        self.pipe_num = pipe_num
        self.stage_list = stage_list
        self.master_seed = master_seed
        self.supervisor_class = supervisor_class
        self.inner_pipe_class = inner_pipe_class

        if initial_instances > 0:
            self.spawn(initial_instances)

    def spawn(self, count):
        """
        Spawn new workers dynamically.
        Returns list of (name, bundle) tuples for created workers.
        """
        created = []
        for _ in range(count):
            name = f"p{self.pipe_num}_w{self._next_worker_idx}"
            worker_seed = self.master_seed + self._next_worker_idx if self.master_seed is not None else None
            supervisor = self.supervisor_class.remote(name)
            pipe_actor = self.inner_pipe_class.remote(self.stage_list, name, supervisor, seed=worker_seed)
            ray.get(supervisor.set_pipe.remote(pipe_actor))
            supervisor.run.remote()
            bundle = {"worker": pipe_actor, "supervisor": supervisor}
            self.workers[name] = bundle
            created.append((name, bundle))
            self._next_worker_idx += 1
            time.sleep(3)

        if created:
            print(f"{self.pipe_name}: spawned {len(created)} workers - {[name for name, _ in created]}")
        return created

    def items(self):
        """Return items view of workers dictionary."""
        return self.workers.items()

    def values(self):
        """Return values view of workers dictionary."""
        return self.workers.values()

    def keys(self):
        """Return keys view of workers dictionary."""
        return self.workers.keys()

    def __len__(self):
        """Return number of workers in the group."""
        return len(self.workers)

    def __repr__(self):
        worker_names = list(self.workers.keys())
        return f"PipeWorkerGroup({worker_names})"

    def __getitem__(self, key):
        """Support dictionary-style access."""
        return self.workers[key]

    def remove(self, name, logger):
        """Remove a worker from the group."""
        ray.kill(self.workers[name]["worker"])
        logger.info(f"killed worker actor {name} to release GPU resouces")
        ray.kill(self.workers[name]["supervisor"])
        logger.info(f"Supervisor {name} killed successfully")
        if name in self.workers:
            del self.workers[name]


def make_pipe(pipe_name, exp_name, pipe_num, stage_list, dev, instance_num, total_processes, config, master_seed=None):
    gpu_num = 0
    if dev == "gpu":
        resources = ray.cluster_resources()
        total_gpus = resources.get("GPU", 0)
        assert total_gpus > 0, "not enough gpu resources"
        processes_per_gpu = math.ceil(total_processes / total_gpus)
        gpu_num = 1.0 / processes_per_gpu

    @ray.remote
    class Supervisor:
        def __init__(self, name):
            self.name = "supervisor_" + name
            self.pipe_worker = None
            self.logger = configure_logging(exp_name, self.name)
            self.logger.info("Supervisor started")
            self.monitor = StatusMonitor.get_instance()
            self.monitor.set_logger(self.logger)

            self._last_status_check = 0.0
            self.check_interval = config.get(MONITOR_CHECK_INTERVAL, 120)
            self.logger.info(f"Monitor check interval: {self.check_interval} seconds")
            if config.get(STATUS_TIMEOUTS, None) is not None:
                self.monitor.set_component_timeouts(config[STATUS_TIMEOUTS])

        def set_pipe(self, pipe_worker):
            self.logger.info("set pipe worker")
            self.pipe_worker = pipe_worker

        def set_queue(self, input_queue, output_queue):
            self.input_queue = input_queue
            self.output_queue = output_queue

        def _restart_worker(self):
            try:
                ray.kill(self.pipe_worker, no_restart=False)
                self.logger.info("trigger restart of the actor")
            except Exception as ke:
                self.logger.error(f"restart actor error: {ke}")

        def update_component_state(self, components_state):
            for _, state in components_state.items():
                self.monitor.register_update(state)

        def _start_daemon(self):
            miss_cnt = 0
            while True:
                now = time.time()
                if now - self._last_status_check >= self.check_interval:
                    try:
                        timeout_components = self.monitor.check_and_update_timeouts()
                        if len(timeout_components) > 0:
                            self.logger.warning(f"Components timeout: {timeout_components}, restart the pipe worker")
                            self._restart_worker()
                            self.monitor.clear()
                        else:
                            if self.monitor.get_components_length() == 0:
                                miss_cnt += 1
                                self.logger.info(f"No components timeout detected, miss count: {miss_cnt}")
                            if miss_cnt >= 5:
                                self.logger.info("No components detected for 5 consecutive checks, restart pipe worker")
                                self._restart_worker()
                                self.monitor.clear()
                                miss_cnt = 0
                    except Exception as e:
                        self.logger.error(f"Get components status failed: {e}")
                        self._restart_worker()
                        self.monitor.clear()
                    self._last_status_check = now
                time.sleep(1)

        def run(self):
            assert self.pipe_worker is not None, "pipe worker is not set"
            thread = threading.Thread(target=self._start_daemon, daemon=True)
            thread.start()

    @ray.remote(num_gpus=gpu_num, max_restarts=3, max_task_retries=3)
    class InnerPipe:
        def __init__(self, stage_list, name, supervisor, seed=None):
            if seed is not None:
                set_all_seeds(seed)
            self.stages = stage_list
            self.name = name
            self.supervisor = supervisor
            init_env()
            self.logger = configure_logging(exp_name, self.name)
            self.logger.info(f"Working on gpu {os.environ.get('CUDA_VISIBLE_DEVICES')}")
            if ray.get_runtime_context().was_current_actor_reconstructed is True:
                msg = (
                    f"{'='*80}\n"
                    "!!! ATTENTION !!!\n"
                    f"!!! InnerPipe {name} WAS RECONSTRUCTED due to SYSTEM ERROR !!!\n"
                    "!!! Please CHECK LOGS in /tmp/ray/session_latest/logs/ for details !!!\n"
                    f"{'='*80}\n"
                )
                self.logger.info(msg)

            self.monitor = StatusMonitor.get_instance()
            self.monitor.set_logger(self.logger)

            self.monitor_check_interval = config.get(MONITOR_CHECK_INTERVAL, 120)

        def _update_supervisor(self):
            while True:
                for _ in range(self.monitor_check_interval):
                    time.sleep(1)
                components_status = self.monitor.get_all_status()
                ray.get(self.supervisor.update_component_state.remote(components_status))

        def run(self, input_queue, output_queue):
            self.logger.info(f"[InnerPipe stages]: {self.stages}")

            thread = threading.Thread(target=self._update_supervisor, daemon=True)
            thread.start()
            self.logger.info("Reporter started, start running pipe")

            mid_results = StageInput()
            # if input_queue is None:
            #     mid_results = StageInput()
            # else:
            #     mid_results = StageInput((input_queue,), {})
            for _, stage in enumerate(self.stages):
                if isinstance(stage, DumpStage):
                    mid_results = stage.run(mid_results, output_queue)
                elif isinstance(stage, DedumpStage):
                    mid_results = stage.run(mid_results, input_queue)
                else:
                    mid_results = stage.run(mid_results)
            result, finish = iter_to_obj(mid_results)
            self.logger.info("====================================")
            self.logger.info(f"result: {result}, finish: {finish}")
            self.logger.info("====================================")
            ray.kill(self.supervisor)
            self.logger.info("actor finished")
            return finish

    group = PipeWorkerGroup(
        pipe_name=pipe_name,
        exp_name=exp_name,
        pipe_num=pipe_num,
        stage_list=stage_list,
        master_seed=master_seed,
        supervisor_class=Supervisor,
        inner_pipe_class=InnerPipe,
        initial_instances=instance_num,
    )
    print(pipe_name, group)
    return group
