from abc import abstractmethod

from nimbus.components.data.iterator import Iterator
from nimbus.components.data.scene import Scene


class SceneLoader(Iterator):
    """
    Base class for scene loading in a simulation environment. This class defines the structure for loading scenes
    and tracking the loading process. It manages the current package iterator and provides hooks for subclasses
    to implement specific scene loading logic.

    Args:
        pack_iter (Iterator): An iterator that provides packages containing scene information to be loaded.
    """

    def __init__(self, pack_iter):
        super().__init__()
        self.pack_iter = pack_iter

    @abstractmethod
    def load_asset(self) -> Scene:
        """
        Abstract method to load and initialize a scene.

        Subclasses must implement this method to define the specific logic for creating and configuring
        a scene object based on the current state of the iterator.

        Returns:
            Scene: A fully initialized Scene object.
        """
        raise NotImplementedError("This method must be implemented by subclasses")

    def _next(self) -> Scene:
        try:
            return self.load_asset()
        except StopIteration:
            raise StopIteration("No more scenes to load.")
        except Exception as e:
            self.logger.exception(f"Error during scene loading: {e}")
            raise e
