from time import time

from nimbus.dist_sim.head_node import HeadNode
from nimbus.scheduler.sches import gen_pipe, gen_scheduler
from nimbus.utils.logging import configure_logging
from nimbus.utils.random import set_all_seeds
from nimbus.utils.types import (
    NAME,
    SAFE_THRESHOLD,
    STAGE_PIPE,
    WORKER_SCHEDULE,
    StageInput,
)
from nimbus.utils.utils import consume_stage


class DataEngine:
    def __init__(self, config, master_seed=None):
        if master_seed is not None:
            master_seed = int(master_seed)
            set_all_seeds(master_seed)
        exp_name = config[NAME]
        configure_logging(exp_name, config=config)
        self._sche_list = gen_scheduler(config)
        self._stage_input = StageInput()

    def run(self):
        for stage in self._sche_list:
            self._stage_input = stage.run(self._stage_input)
        consume_stage(self._stage_input)


class DistPipeDataEngine:
    def __init__(self, config, master_seed=None):
        self._sche_list = gen_scheduler(config)
        self.config = config
        self._stage_input = StageInput()
        exp_name = config[NAME]
        self.logger = configure_logging(exp_name, config=config)
        master_seed = int(master_seed) if master_seed is not None else None
        self.pipe_list = gen_pipe(config, self._sche_list, exp_name, master_seed=master_seed)
        self.head_nodes = {}

    def run(self):
        self.logger.info("[DistPipeDataEngine]: %s", self.pipe_list)
        st_time = time()
        cur_pipe_queue = None
        pre_worker_num = 0
        worker_schedule = self.config[STAGE_PIPE].get(WORKER_SCHEDULE, False)
        for idx, pipe in enumerate(self.pipe_list):
            self.head_nodes[idx] = HeadNode(
                cur_pipe_queue,
                pipe,
                pre_worker_num,
                self.config[STAGE_PIPE][SAFE_THRESHOLD],
                worker_schedule,
                self.logger,
                idx,
            )
            self.head_nodes[idx].run()
            cur_pipe_queue = self.head_nodes[idx].result_queue()
            pre_worker_num = len(pipe)
        for _, value in self.head_nodes.items():
            value.wait_stop()
        et_time = time()
        self.logger.info("execution duration: %s", et_time - st_time)
