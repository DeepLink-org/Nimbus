import os

from nimbus.components.data.iterator import Iterator
from nimbus.components.data.scene import Scene
from nimbus.components.load import LayoutRandomizer


class EnvRandomizer(LayoutRandomizer):
    """
    Environment randomizer that extends the base layout randomizer to include additional randomization
    capabilities specific to the simulation environment.
    This class can be used to randomize various aspects of the environment, such as object placements,
    textures, lighting conditions, and other scene parameters, based on the provided configuration.
    The randomization process can be controlled through the number of randomizations to perform and
    whether to operate in strict mode.

    Args:
        scene_iter (Iterator[Scene]): An iterator that yields scenes to be randomized.
        random_num (int): How many randomizations to perform for each scene.
        strict_mode (bool): Whether to operate in strict mode, which enforces certain constraints
            on the randomization process.
        input_dir (str): Directory from which to load additional randomization data such as object
            placements or textures. If None, randomization is performed without loading additional data.
    """

    def __init__(
        self, scene_iter: Iterator[Scene], random_num: int = 1, strict_mode: bool = False, input_dir: str = None
    ):
        super().__init__(scene_iter, random_num, strict_mode)
        assert self.random_num > 0, "random_num must be greater than 0"
        self.input_dir = input_dir
        if self.input_dir is not None:
            self.paths_names = os.listdir(self.input_dir)
            self.random_num = len(self.paths_names)

    def randomize_scene(self, scene) -> Scene:
        if scene.plan_info is None:
            path = None
            if self.input_dir is not None:
                path = os.path.join(self.input_dir, self.paths_names[self.cur_index])
            if not scene.wf.randomization(path):
                return None
        else:
            if not scene.wf.randomization_from_mem(scene.plan_info):
                return None
        return scene
