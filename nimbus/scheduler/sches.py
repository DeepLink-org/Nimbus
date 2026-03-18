from nimbus.scheduler.inner_pipe import make_pipe
from nimbus.scheduler.stages import (
    DedumpStage,
    DumpStage,
    LoadStage,
    PlanStage,
    PlanWithRenderStage,
    RenderStage,
    StoreStage,
)
from nimbus.utils.types import (
    DEDUMP_STAGE,
    DUMP_STAGE,
    LOAD_STAGE,
    PLAN_STAGE,
    PLAN_WITH_RENDER_STAGE,
    RENDER_STAGE,
    STAGE_DEV,
    STAGE_NUM,
    STAGE_PIPE,
    STORE_STAGE,
    WORKER_NUM,
)


def gen_scheduler(config):
    stages = []
    if LOAD_STAGE in config:
        stages.append(LoadStage(config[LOAD_STAGE]))
    if PLAN_WITH_RENDER_STAGE in config:
        stages.append(PlanWithRenderStage(config[PLAN_WITH_RENDER_STAGE]))
    if PLAN_STAGE in config:
        stages.append(PlanStage(config[PLAN_STAGE]))
    if DUMP_STAGE in config:
        stages.append(DumpStage(config[DUMP_STAGE]))
    if DEDUMP_STAGE in config:
        stages.append(DedumpStage(config[DEDUMP_STAGE]))
    if RENDER_STAGE in config:
        stages.append(RenderStage(config[RENDER_STAGE]))
    if STORE_STAGE in config:
        stages.append(StoreStage(config[STORE_STAGE]))
    return stages


def gen_pipe(config, stage_list, exp_name, master_seed=None):
    if STAGE_PIPE in config:
        pipe_stages_num = config[STAGE_PIPE][STAGE_NUM]
        pipe_stages_dev = config[STAGE_PIPE][STAGE_DEV]
        pipe_worker_num = config[STAGE_PIPE][WORKER_NUM]
        inner_pipes = []
        pipe_num = 0
        total_processes = 0
        for worker_num in config[STAGE_PIPE][WORKER_NUM]:
            total_processes += worker_num
        for num, dev, worker_num in zip(pipe_stages_num, pipe_stages_dev, pipe_worker_num):
            stages = stage_list[:num]
            print("===========================")
            print(f"inner stage num: {num}, device type: {dev}")
            print(f"stages: {stages}")
            print("===========================")
            stage_list = stage_list[num:]
            pipe_name = "pipe"
            for stage in stages:
                pipe_name += f"_{stage.__class__.__name__}"
            pipe_workers = make_pipe(
                pipe_name,
                exp_name,
                pipe_num,
                stages,
                dev,
                worker_num,
                total_processes,
                config[STAGE_PIPE],
                master_seed=master_seed,
            )
            inner_pipes.append(pipe_workers)
            pipe_num += 1
        return inner_pipes
    else:
        return [make_pipe.InnerPipe(stage_list)]
