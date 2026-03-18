import sys
import time
from abc import abstractmethod
from typing import Optional

from nimbus.components.data.iterator import Iterator
from nimbus.components.data.scene import Scene
from nimbus.components.data.sequence import Sequence
from nimbus.daemon.decorators import status_monitor
from nimbus.utils.flags import is_debug_mode
from nimbus.utils.types import ARGS, TYPE

from .planner import path_planner_dict


class SequencePlanner(Iterator):
    """
    A base class for sequence planning in a simulation environment. This class defines the structure for generating
    sequences based on scenes and tracking the planning process. It manages the current scene, episode count
    and provides hooks for subclasses to implement specific sequence generation logic.

    Args:
        scene_iter (Iterator): An iterator that provides scenes to be processed for sequence planning.
        planner_cfg (dict): A dictionary containing configuration parameters for the planner,
            such as the type of planner to use and its arguments.
        episodes (int): The number of episodes to generate for each scene before moving to the next one. Default is 1.
    """

    def __init__(self, scene_iter: Iterator[Scene], planner_cfg: dict, episodes: int = 1):
        super().__init__()
        self.scene_iter = scene_iter
        self.planner_cfg = planner_cfg
        self.episodes = episodes
        self.current_episode = sys.maxsize
        self.scene: Optional[Scene] = None

    @status_monitor()
    def _plan_with_status(self) -> Optional[Sequence]:
        seq = self.generate_sequence()
        return seq

    def _next(self) -> tuple[Scene, Sequence]:
        try:
            if self.scene is None or self.current_episode >= self.episodes:
                try:
                    self.scene = next(self.scene_iter)
                    self.current_episode = 0
                    if self.scene is None:
                        return None, None
                    self.initialize(self.scene)
                except StopIteration:
                    raise StopIteration("No more scene to process.")
                except Exception as e:
                    self.logger.exception(f"Error loading next scene: {e}")
                    if is_debug_mode():
                        raise e
                    self.current_episode = sys.maxsize
                    return None, None

            while True:
                compute_start_time = time.time()
                seq = self._plan_with_status()
                compute_end_time = time.time()
                self.current_episode += 1

                if seq is not None:
                    self.collect_compute_frame_info(seq.get_length(), compute_end_time - compute_start_time)
                    return self.scene, seq

                if self.current_episode >= self.episodes:
                    return self.scene, None

                self.logger.info(f"Generate seq failed and retry. Current episode id is {self.current_episode}")

        except StopIteration:
            raise StopIteration("No more scene to process.")
        except Exception as e:
            scene_name = getattr(self.scene, "name", "<unknown>")
            self.logger.exception(
                f"Error during idx {self.current_episode} sequence generation for scene {scene_name}: {e}"
            )
            if is_debug_mode():
                raise e
            self.current_episode += 1
            return self.scene, None

    @abstractmethod
    def generate_sequence(self) -> Optional[Sequence]:
        raise NotImplementedError("This method should be overridden by subclasses")

    def _initialize(self, scene):
        if self.planner_cfg is not None:
            self.logger.info(f"init {self.planner_cfg[TYPE]} planner in seq_planner")
            self.planner = path_planner_dict[self.planner_cfg[TYPE]](scene, **self.planner_cfg.get(ARGS, {}))
        else:
            self.planner = None
            self.logger.info("planner config is None in seq_planner and skip initialize")

    def initialize(self, scene):
        init_start_time = time.time()
        self._initialize(scene)
        self.record_init_time(time.time() - init_start_time)
