import time
from abc import abstractmethod
from typing import Optional

from nimbus.components.data.iterator import Iterator
from nimbus.components.data.observation import Observations
from nimbus.components.data.scene import Scene
from nimbus.components.data.sequence import Sequence
from nimbus.daemon.decorators import status_monitor


class BaseRenderer(Iterator):
    """
    Base class for rendering in a simulation environment. This class defines the structure for rendering scenes and
    tracking the rendering process. It manages the current scene and provides hooks for subclasses to implement
    specific rendering logic.

    Args:
        scene_seq_iter (Iterator): An iterator that provides pairs of scenes and sequences to be rendered. Each item
                                  from the iterator should be a tuple containing a scene and its corresponding sequence.
    """

    def __init__(self, scene_seq_iter: Iterator[tuple[Scene, Sequence]]):
        super().__init__()
        self.scene_seq_iter = scene_seq_iter
        self.scene: Optional[Scene] = None

    @status_monitor()
    def _generate_obs_with_status(self, seq) -> Optional[Observations]:
        compute_start_time = time.time()
        obs = self.generate_obs(seq)
        end_start_time = time.time()
        if obs is not None:
            self.collect_compute_frame_info(len(obs), end_start_time - compute_start_time)
        return obs

    def _next(self):
        try:
            scene, seq = next(self.scene_seq_iter)
            if scene is not None:
                if self.scene is None:
                    self.reset(scene)
                elif scene.task_id != self.scene.task_id or scene.name != self.scene.name:
                    self.logger.info(f"Scene changed: {self.scene.name} -> {scene.name}")
                    self.reset(scene)
            if seq is None:
                return scene, None, None
            obs = self._generate_obs_with_status(seq)
            if obs is None:
                return scene, None, None
            return scene, seq, obs
        except StopIteration:
            raise StopIteration("No more sequences to process.")
        except Exception as e:
            self.logger.exception(f"Error during rendering: {e}")
            raise e

    @abstractmethod
    def generate_obs(self, seq) -> Optional[Observations]:
        raise NotImplementedError("This method should be overridden by subclasses")

    @abstractmethod
    def _lazy_init(self):
        raise NotImplementedError("This method should be overridden by subclasses")

    @abstractmethod
    def _close_resource(self):
        raise NotImplementedError("This method should be overridden by subclasses")

    def reset(self, scene):
        try:
            self.scene = scene
            self._close_resource()
            init_start_time = time.time()
            self._lazy_init()
            self.record_init_time(time.time() - init_start_time)
        except Exception as e:
            self.logger.exception(f"Error initializing renderer: {e}")
            self.scene = None
            raise e
