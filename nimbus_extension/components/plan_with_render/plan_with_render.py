import sys
import time

from nimbus.components.data.iterator import Iterator
from nimbus.components.data.observation import Observations
from nimbus.components.data.scene import Scene
from nimbus.daemon.decorators import status_monitor
from nimbus.utils.flags import is_debug_mode


class EnvPlanWithRender(Iterator):
    """
    A component that integrates planning and rendering for a given scene. It takes an iterator of scenes as
    input, performs planning and rendering for each scene, and produces sequences and observations as output.
    The component manages the planning and rendering process, including tracking the current episode and
    collecting performance metrics.

    Args:
        scene_iter (Iterator[Scene]): An iterator that yields scenes to be processed for planning and rendering.
    """

    def __init__(self, scene_iter: Iterator[Scene]):
        super().__init__()
        self.scene_iter = scene_iter
        self.episodes = 1
        self.current_episode = sys.maxsize
        self.scene = None

    @status_monitor()
    def plan_with_render(self):
        wf = self.scene.wf
        obs_num = wf.plan_with_render()
        if obs_num <= 0:
            return None
        # Assuming rgb is a dictionary of lists, get the length from one of the lists.
        obs = Observations(self.scene.name, str(self.current_episode), length=obs_num)
        return obs

    def _next(self):
        try:
            if self.scene is None or self.current_episode >= self.episodes:
                try:
                    self.scene = next(self.scene_iter)
                    self.current_episode = 0
                    if self.scene is None:
                        return None, None, None
                except StopIteration:
                    raise StopIteration("No more scene to process.")
                except Exception as e:
                    self.logger.exception(f"Error loading next scene: {e}")
                    if is_debug_mode():
                        raise e
                    self.current_episode = sys.maxsize
                    return None, None, None

            while True:
                compute_start_time = time.time()
                obs = self.plan_with_render()
                compute_end_time = time.time()
                self.current_episode += 1

                if obs is not None:
                    self.collect_compute_frame_info(obs.get_length(), compute_end_time - compute_start_time)
                    return self.scene, None, obs

                if self.current_episode >= self.episodes:
                    return self.scene, None, None

                self.logger.info(f"Generate seq failed and retry. Current episode id is {self.current_episode}")
        except StopIteration:
            raise StopIteration("No more scene to process.")
        except Exception as e:
            scene_name = getattr(self.scene, "name", "<unknown>")
            self.logger.exception(
                f"Error during idx {self.current_episode} sequence plan with render for scene {scene_name}: {e}"
            )
            if is_debug_mode():
                raise e
            self.current_episode += 1
            return self.scene, None, None
