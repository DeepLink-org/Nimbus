import sys
import time
from abc import abstractmethod
from typing import Optional

from nimbus.components.data.iterator import Iterator
from nimbus.components.data.scene import Scene
from nimbus.daemon.decorators import status_monitor


class LayoutRandomizer(Iterator):
    """
    Base class for layout randomization in a scene. This class defines the structure for randomizing scenes and
    tracking the randomization process. It manages the current scene, randomization count, and provides hooks for
    subclasses to implement specific randomization logic.

    Args:
        scene_iter (Iterator): An iterator that provides scenes to be randomized.
        random_num (int): The number of randomizations to perform for each scene before moving to the next one.
        strict_mode (bool): If True, the randomizer will check the generation status of the current scene and retry
                            randomization if it was not successful. This ensures that only successfully generated
                            scenes are counted towards the randomization limit.
    """

    def __init__(self, scene_iter: Iterator, random_num: int, strict_mode: bool = False):
        super().__init__()
        self.scene_iter = scene_iter
        self.random_num = random_num
        self.strict_mode = strict_mode
        self.cur_index = sys.maxsize
        self.scene: Optional[Scene] = None

    def reset(self, scene):
        self.cur_index = 0
        self.scene = scene

    def _fetch_next_scene(self):
        scene = next(self.scene_iter)
        self.reset(scene)

    @status_monitor()
    def _randomize_with_status(self, scene) -> Scene:
        scene = self.randomize_scene(self.scene)
        return scene

    def _next(self) -> Scene:
        try:
            if self.strict_mode and self.scene is not None:
                if not self.scene.get_generate_status():
                    self.logger.info("strict_mode is open, retry the randomization to generate sequence.")
                    st = time.time()
                    scene = self._randomize_with_status(self.scene)
                    self.collect_seq_info(1, time.time() - st)
                    return scene
            if self.cur_index >= self.random_num:
                self._fetch_next_scene()
            if self.cur_index < self.random_num:
                st = time.time()
                scene = self._randomize_with_status(self.scene)
                self.collect_seq_info(1, time.time() - st)
                self.cur_index += 1
            return scene
        except StopIteration:
            raise StopIteration("No more scenes to randomize.")
        except Exception as e:
            self.logger.exception(f"Error during scene idx {self.cur_index} randomization: {e}")
            self.cur_index += 1
            raise e

    @abstractmethod
    def randomize_scene(self, scene) -> Scene:
        raise NotImplementedError("This method should be overridden by subclasses")
