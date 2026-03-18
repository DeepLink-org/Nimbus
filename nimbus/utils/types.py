from dataclasses import dataclass
from typing import Dict, Optional, Tuple

NAME = "name"

# stage name
LOAD_STAGE = "load_stage"
PLAN_STAGE = "plan_stage"
RENDER_STAGE = "render_stage"
PLAN_WITH_RENDER_STAGE = "plan_with_render_stage"
STORE_STAGE = "store_stage"
STAGE_PIPE = "stage_pipe"
DUMP_STAGE = "dump_stage"
DEDUMP_STAGE = "dedump_stage"

# instruction name
# LOAD_STAGE
SCENE_LOADER = "scene_loader"
LAYOUT_RANDOM_GENERATOR = "layout_random_generator"
INDEX_GENERATOR = "index_generator"
DEDUMPER = "dedumper"

# PLAN_STAGE
SEQ_PLANNER = "seq_planner"
PLANNER = "planner"
SIMULATOR = "simulator"

# RENDER_STAGE
RENDERER = "renderer"

# PLAN_WITH_RENDER_STAGE
PLAN_WITH_RENDER = "plan_with_render"

# PIPE_STAGE
STAGE_NUM = "stage_num"
STAGE_DEV = "stage_dev"
WORKER_NUM = "worker_num"
WORKER_SCHEDULE = "worker_schedule"
SAFE_THRESHOLD = "safe_threshold"
STATUS_TIMEOUTS = "status_timeouts"
MONITOR_CHECK_INTERVAL = "monitor_check_interval"

# STORE_STAGE
WRITER = "writer"
DUMPER = "dumper"

OUTPUT_PATH = "output_path"
INPUT_PATH = "input_path"

TYPE = "type"
ARGS = "args"


@dataclass
class StageInput:
    """
    A data class that encapsulates the input for a stage in the processing pipeline.

    Args:
        Args (Optional[Tuple]): Positional arguments passed to the stage's processing function.
        Kwargs (Optional[Dict]): Keyword arguments passed to the stage's processing function.
    """

    Args: Optional[Tuple] = None
    Kwargs: Optional[Dict] = None
