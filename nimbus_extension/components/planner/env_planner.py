from nimbus.components.data.iterator import Iterator
from nimbus.components.data.scene import Scene
from nimbus.components.data.sequence import Sequence
from nimbus.components.planner import SequencePlanner


class EnvSeqPlanner(SequencePlanner):
    """
    A sequence planner that generates sequences based on the environment's workflow.

    Args:
        scene_iter (Iterator[Scene]): An iterator that provides scenes to be processed for sequence planning.
        planner_cfg (dict): A dictionary containing configuration parameters for the planner,
            such as the type of planner to use and its arguments.
    """

    def __init__(self, scene_iter: Iterator[Scene], planner_cfg: dict):
        super().__init__(scene_iter, planner_cfg, episodes=1)

    def generate_sequence(self):
        wf = self.scene.wf
        sequence = wf.generate_seq()
        if len(sequence) <= 0:
            return None
        return Sequence(self.scene.name, str(self.current_episode), length=len(sequence), data=sequence)
