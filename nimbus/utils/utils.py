import functools
import os
import re
import sys
import time
from typing import Tuple, Type, Union

from nimbus.components.data.observation import Observations
from nimbus.components.data.scene import Scene
from nimbus.components.data.sequence import Sequence


def init_env():
    sys.path.append("./")
    sys.path.append("./data_engine")
    sys.path.append("workflows/simbox")


def unpack_iter_data(data: tuple):
    assert len(data) <= 3, "not support yet"
    scene = None
    seq = None
    obs = None
    for item in data:
        if isinstance(item, Scene):
            scene = item
        elif isinstance(item, Sequence):
            seq = item
        elif isinstance(item, Observations):
            obs = item
    return scene, seq, obs


def consume_stage(stage_input):
    if hasattr(stage_input, "Args"):
        consume_iterators(stage_input.Args)
        for value in stage_input.Args:
            if hasattr(value, "__del__"):
                value.__del__()  # pylint: disable=C2801
    if hasattr(stage_input, "Kwargs"):
        if stage_input.Kwargs is not None:
            for value in stage_input.Kwargs.values():
                consume_iterators(value)
                if hasattr(value, "__del__"):
                    value.__del__()  # pylint: disable=C2801


# prevent isaac sim close pipe worker in advance
def pipe_consume_stage(stage_input):
    if hasattr(stage_input, "Args"):
        consume_iterators(stage_input.Args)
    if hasattr(stage_input, "Kwargs"):
        if stage_input.Kwargs is not None:
            for value in stage_input.Kwargs.values():
                consume_iterators(value)


def consume_iterators(obj):
    # from pdb import set_trace; set_trace()
    if isinstance(obj, (str, bytes)):
        return obj
    if isinstance(obj, dict):
        return {key: consume_iterators(value) for key, value in obj.items()}
    if isinstance(obj, list):
        return [consume_iterators(item) for item in obj]
    if isinstance(obj, tuple):
        return tuple(consume_iterators(item) for item in obj)
    if hasattr(obj, "__iter__"):
        for item in obj:
            consume_iterators(item)
    return obj


def scene_names_postprocess(scene_names: list) -> list:
    """
    Distributes a list of scene names (folders) among multiple workers in a distributed environment.
    This function is designed to work with Deep Learning Container (DLC) environments, where worker
    information is extracted from environment variables. It assigns a subset of the input scene names
    to the current worker based on its rank and the total number of workers, using a round-robin strategy.
    If not running in a DLC environment, all scene names are assigned to a single worker.
    Args:
        scene_names (list): List of scene names (typically folder names) to be distributed.
    Returns:
        list: The subset of scene names assigned to the current worker.
    Raises:
        PermissionError: If there is a permission issue accessing the input directory.
        RuntimeError: For any other errors encountered during processing.
    Notes:
        - The function expects certain environment variables (e.g., POD_NAME, WORLD_SIZE) to be set
          in DLC environments.
        - If multiple workers are present, the input list is sorted before distribution to ensure
          consistent assignment across workers.
    """

    def _get_dlc_worker_info():
        """Extract worker rank and world size from DLC environment variables."""
        pod_name = os.environ.get("POD_NAME")

        if pod_name:
            # Match worker-N or master-N patterns
            match = re.search(r"dlc.*?-(worker|master)-(\d+)$", pod_name)
            if match:
                node_type, node_id = match.groups()
                world_size = int(os.environ.get("WORLD_SIZE", "1"))

                if node_type == "worker":
                    rank = int(node_id)
                else:  # master node
                    rank = world_size - 1

                return rank, world_size

        # Default for non-DLC environment
        return 0, 1

    def _distribute_folders(all_folders, rank, world_size):
        """Distribute folders among workers using round-robin strategy."""
        if not all_folders:
            return []

        # Only sort when there are multiple workers to ensure consistency
        if world_size > 1:
            all_folders.sort()

        # Distribute using slicing: worker i gets folders at indices i, i+world_size, ...
        return all_folders[rank::world_size]

    try:
        # Get all subfolders
        all_subfolders = scene_names
        if not all_subfolders:
            print(f"Warning: No scene found in {scene_names}")
            return []

        # Get worker identity and distribute folders
        rank, world_size = _get_dlc_worker_info()
        assigned_folders = _distribute_folders(all_subfolders, rank, world_size)

        print(
            f"DLC Worker {rank}/{world_size}: Assigned {len(assigned_folders)} out of "
            f"{len(all_subfolders)} total folders"
        )

        return assigned_folders

    except PermissionError:
        raise PermissionError(f"No permission to access directory: {scene_names}")
    except Exception as e:
        raise RuntimeError(f"Error reading input directory {scene_names}: {e}")


def retry_on_exception(
    max_retries: int = 3, retry_exceptions: Union[bool, Tuple[Type[Exception], ...]] = True, delay: float = 1.0
):
    def decorator(func):
        @functools.wraps(func)
        def wrapper(self, *args, **kwargs):
            last_exception = None
            for attempt in range(max_retries + 1):
                try:
                    if attempt > 0:
                        print(f"Retry attempt {attempt}/{max_retries} for {func.__name__}")
                    return func(self, *args, **kwargs)
                except Exception as e:
                    last_exception = e
                    should_retry = False
                    if retry_exceptions is True:
                        should_retry = True
                    elif isinstance(retry_exceptions, (tuple, list)):
                        should_retry = isinstance(e, retry_exceptions)

                    if should_retry and attempt < max_retries:
                        print(f"Error in {func.__name__}: {e}. Retrying in {delay} seconds...")
                        time.sleep(delay)
                    else:
                        raise
            if last_exception:
                raise last_exception

        return wrapper

    return decorator
