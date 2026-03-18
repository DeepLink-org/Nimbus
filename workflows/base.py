from abc import ABC, abstractmethod
from copy import deepcopy
from functools import wraps


class NimbusWorkFlow(ABC):
    workflows = {}

    # pylint: disable=W0613
    def __init__(self, world, task_cfg_path: str, **kwargs):
        """Initialize the workflow.

        Args:
            world: The simulation world instance.
            task_cfg_path (str): Path to the task configuration file.
                Each workflow subclass is responsible for parsing this file.
            **kwargs: Workflow-specific parameters.
                Subclasses declare only the kwargs they need; unused ones are silently ignored.
        """
        self.world = world
        self.task_cfg_path = task_cfg_path
        self.task_cfgs = self.parse_task_cfgs(task_cfg_path)

    def init_task(self, index, need_preload: bool = True):
        assert index < len(self.task_cfgs), "Index out of range for task configurations."
        self.task_cfg = self.task_cfgs[index]
        self.reset(need_preload)

    def __copy__(self):
        new_wf = type(self).__new__(type(self))
        new_wf.__dict__.update(self.__dict__)

        if hasattr(self, "logger"):
            new_wf.logger = deepcopy(self.logger)

        if hasattr(self, "recoder"):
            new_wf.recoder = deepcopy(self.recoder)

        return new_wf

    @abstractmethod
    def parse_task_cfgs(self, task_cfg_path) -> list:
        """
        Parse the task configuration file.
        Args:
            task_cfg_path (str): Path to the task configuration file.
        Returns:
            list: List of task configurations.
        """
        pass

    @abstractmethod
    def get_task_name(self) -> str:
        """Get the name of the current task.
        Returns:
            str: name of the current task
        """
        pass

    @abstractmethod
    def reset(self, need_preload):
        """Reset the environment to the initial state of the current task.
        Args:
            need_preload (bool): Whether to preload objects in the environment. Defaults to True.
        """
        pass

    @abstractmethod
    def randomization(self, layout_path=None) -> bool:
        """Randomize the environment layout in one task.
        Args:
            layout_path (str, optional): Path to the layout file. Defaults to None.
        Returns:
            bool: True if randomization is successful, False otherwise.
        """
        pass

    @abstractmethod
    def generate_seq(self) -> list:
        """Generate a sequence of states for the current task.
        Returns:
            list: Sequence of states which be replayed for the current task.
            If the sequence is not generated, return an empty list.
        """
        pass

    @abstractmethod
    def seq_replay(self, sequence: list) -> int:
        """Replay the sequence and generate observations.
        Args:
            sequence (list): Sequence of states to be replayed.
        Returns:
            int: Length of the replayed sequence.
        """
        pass

    @abstractmethod
    def save(self, save_path: str) -> int:
        """Save the all information.
        Args:
            save_path (str): Path to save the observations.
        Returns:
            int: Length of the saved observations.
        """
        pass

    # plan mode
    def save_seq(self, save_path: str) -> int:
        """Save the generated sequence without observations.
        Args:
            save_path (str): Path to save the sequence.
        Returns:
            int: Length of the saved sequence.
        """
        raise NotImplementedError("This method should be implemented in the subclass.")

    # render mode
    def recover_seq(self, seq_path: str) -> list:
        """Recover sequence from a sequence file.

        Args:
            seq_path (str): Path to the sequence file.
        """
        raise NotImplementedError("This method should be implemented in the subclass.")

    # plan with render mode
    def generate_seq_with_obs(self) -> int:
        """Generate a sequence with observation for the current task.
            (For debug or future RL)
        Returns:
            int: Length of the generated sequence.
        """
        raise NotImplementedError("This method should be implemented in the subclass.")

    # pipeline mode
    def dump_plan_info(self) -> bytes:
        """Dump the layout and sequence plan information of the current task.

        Returns:
            bytes: Serialized plan information including layout and sequence data.
        """
        raise NotImplementedError("This method should be implemented in the subclass.")

    # pipeline mode
    def dedump_plan_info(self, ser_obj: bytes) -> object:
        """Deserialize the layout and plan information of the current task.

        Args:
            ser_obj (bytes): Serialized plan information generated from dump_plan_info().

        Returns:
            object: Deserialized layout and sequence information.
                This will be used as input for randomization_from_mem() and recover_seq_from_mem().
        """
        raise NotImplementedError("This method should be implemented in the subclass.")

    # pipeline mode
    def randomization_from_mem(self, data: object) -> bool:
        """Perform randomization using in-memory plan data.

        Args:
            data (object): Deserialized layout and sequence information.

        Returns:
            bool: True if randomization succeeds, False otherwise.
        """
        raise NotImplementedError("This method should be implemented in the subclass.")

    # pipeline mode
    def recover_seq_from_mem(self, data: object) -> list:
        """Recover sequence from in-memory plan data.

        Args:
            data (object): Deserialized layout and sequence information.

        Returns:
            list: Recovered sequence of states.
        """
        raise NotImplementedError("This method should be implemented in the subclass.")

    @classmethod
    def register(cls, name: str):
        """
        Register a workflow with its name(decorator).
        Args:
            name(str): name of the workflow
        """

        def decorator(wfs_class):
            cls.workflows[name] = wfs_class

            @wraps(wfs_class)
            def wrapped_function(*args, **kwargs):
                return wfs_class(*args, **kwargs)

            return wrapped_function

        return decorator


def create_workflow(workflow_type: str, world, task_cfg_path: str, **kwargs):
    wf_cls = NimbusWorkFlow.workflows[workflow_type]
    return wf_cls(world, task_cfg_path, **kwargs)
