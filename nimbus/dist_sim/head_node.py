import traceback
from threading import Thread
from time import sleep, time

import ray
from ray.util.queue import Queue

from nimbus.components.data.package import Package
from nimbus.dist_sim.task_board import TaskBoard
from nimbus.scheduler.inner_pipe import PipeWorkerGroup


class HeadNode:
    def __init__(
        self, data_queue, workers: PipeWorkerGroup, pre_worker_num, safe_threshold, worker_schedule, logger, idx
    ):
        self.idx = idx
        self.data_queue = data_queue
        self.logger = logger
        self.worker_group = workers
        logger.info(f"workers: {list(workers.keys())}")
        self.pre_worker_num = pre_worker_num
        self.safe_threshold = safe_threshold
        self.worker_schedule = worker_schedule
        logger.info(f"safe_threshold: {self.safe_threshold}")
        logger.info(f"worker_schedule: {self.worker_schedule}")
        self.task_queue = Queue() if data_queue is not None else None
        self.output_queue = Queue()
        self.GEN_STOP_SIG = False
        self.task_board = TaskBoard()
        self.gen_thread = Thread(target=self.gen_tasks, args=())
        self.gen_thread.start()
        self.should_stop = False
        self.run_thread = None
        # Map runner ObjectRef to worker name for proper cleanup
        self.runner_to_worker = {}
        self.all_workers_spawned = False

    def gen_tasks(self):
        self.logger.info(f"headnode: {self.idx}: =============start gen task=============")
        pre_worker_stop_num = 0
        while not self.GEN_STOP_SIG:
            if self.data_queue is None:
                self.logger.info(f"headnode: {self.idx}: =============Gen Tasks stop==============")
                self.all_workers_spawned = True
                return
            if self.data_queue.empty():
                sleep(0)
                continue
            if self.task_queue is not None and self.task_queue.size() >= self.safe_threshold:
                sleep(1)
                continue
            task = self.data_queue.get()
            assert isinstance(
                task, Package
            ), f"the transfered type of data should be Package type, but it is {type(task)}"
            if task.should_stop():
                pre_worker_stop_num += 1
                self.logger.info(
                    f"headnode: {self.idx}: Received stop signal from upstream worker"
                    f" ({pre_worker_stop_num}/{self.pre_worker_num})"
                )

                # Dynamic worker scheduling: spawn new worker when upstream worker finishes
                if self.worker_schedule:
                    self.logger.info(
                        f"headnode: {self.idx}: Worker schedule enabled, will spawn 1 new worker after resource release"
                    )
                    # Wait for upstream resources to be released by upstream HeadNode's wait_stop()
                    # Retry mechanism to handle resource release timing
                    max_retries = 30  # 30 * 2s = 60s max wait
                    retry_interval = 2

                    for retry in range(max_retries):
                        try:
                            self.logger.info(
                                f"headnode: {self.idx}: Attempting to spawn new worker (attempt"
                                f" {retry + 1}/{max_retries})..."
                            )
                            created_workers = self.worker_group.spawn(1)
                            if created_workers:
                                for worker_name, worker_bundle in created_workers:
                                    # Start the new worker
                                    runner = worker_bundle["worker"].run.remote(self.task_queue, self.output_queue)
                                    self.runner_to_worker[runner] = worker_name
                                    self.logger.info(
                                        f"headnode: {self.idx}: Successfully spawned and started new worker:"
                                        f" {worker_name}"
                                    )
                                    sleep(5)
                                break  # Success, exit retry loop
                        except Exception as e:
                            if retry < max_retries - 1:
                                self.logger.warning(
                                    f"headnode: {self.idx}: Failed to spawn worker (attempt {retry + 1}), will retry in"
                                    f" {retry_interval}s: {e}"
                                )
                                sleep(retry_interval)
                            else:
                                self.logger.error(
                                    f"headnode: {self.idx}: Failed to spawn new worker after"
                                    f" {max_retries} attempts: {e}"
                                )
                                self.logger.error(traceback.format_exc())

                if pre_worker_stop_num == self.pre_worker_num:
                    for _ in range(len(self.worker_group)):
                        self.logger.info(f"headnode: {self.idx}: get stop signal")
                        stop_pack = Package(None, stop_sig=True)
                        self.task_board.reg_task(stop_pack)
                    self.all_workers_spawned = True
                    return
            else:
                self.task_board.reg_task(task)
        if self.data_queue and not self.data_queue.empty():
            task = self.data_queue.get_nowait()
            self.task_board.reg_task(task)
        self.logger.info("=============Gen Tasks stop==============")
        self.all_workers_spawned = True

    def result_queue(self):
        return self.output_queue

    def run(self):
        self.logger.info(f"headnode: {self.idx}: ==============Running Head Node================")
        for worker_name, worker_bundle in self.worker_group.items():
            runner = worker_bundle["worker"].run.remote(self.task_queue, self.output_queue)
            self.runner_to_worker[runner] = worker_name
            sleep(5)

        def inner_run():
            while not self.should_stop:
                tasks = self.task_board.get_tasks(timeout=0.05)
                if len(tasks) == 0:
                    sleep(0)
                    continue
                while self.task_queue.size() >= self.safe_threshold and not self.should_stop:
                    sleep(1)
                for _, task in enumerate(tasks):
                    self.task_queue.put(task)

        self.run_thread = Thread(target=inner_run)
        self.run_thread.start()

    def sig_stop(self):
        self.logger.info(f"headnode: {self.idx}: ============Gen Stop===============")
        self.GEN_STOP_SIG = True
        self.gen_thread.join()

    def wait_stop(self):
        if self.worker_schedule and self.idx != 0:
            self.logger.info(f"headnode: {self.idx}: Waiting for all worker spawning to complete...")
            timeout = 600  # 600 seconds timeout
            start_time = time()
            while not self.all_workers_spawned:
                if time() - start_time > timeout:
                    self.logger.warning(
                        f"headnode: {self.idx}: Timeout waiting for worker spawning completion after {timeout}s"
                    )
                    break
                sleep(0.1)

            if self.all_workers_spawned:
                self.logger.info(f"headnode: {self.idx}: All worker spawning completed, proceeding to wait for runners")

        remaining_runners = list(self.runner_to_worker.keys())
        for runner in remaining_runners:
            self.logger.info(f"headnode: {self.idx}: remaining runner include: {self.runner_to_worker[runner]}")

        while remaining_runners:
            ready, _ = ray.wait(remaining_runners, num_returns=len(remaining_runners), timeout=1.0)

            for finished_runner in ready:
                worker_name = self.runner_to_worker.get(finished_runner, "unknown")
                self.logger.info(f"headnode: {self.idx}: Worker {worker_name} finished")
                try:
                    ray.get(finished_runner)
                    self.logger.info(f"headnode: {self.idx}: Worker {worker_name} completed successfully")
                    self.worker_group.remove(worker_name, self.logger)
                except Exception as e:
                    self.logger.error(f"Worker {worker_name} failed, error stack:")
                    self.logger.error(e)
                    if worker_name in self.worker_group.keys():
                        self.worker_group.remove(worker_name, self.logger)

                remaining_runners.remove(finished_runner)
                self.runner_to_worker.pop(finished_runner, None)

            if not ready:
                sleep(1)

        self.logger.info(f"headnode: {self.idx}: ==============stop head================")
        self.should_stop = True
        if self.run_thread is not None:
            self.run_thread.join()
        self.sig_stop()

    def __del__(self):
        if self.task_queue is not None:
            self.task_queue.shutdown()
        self.output_queue.shutdown()
