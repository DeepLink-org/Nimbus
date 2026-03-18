class Scene:
    """
    Represents a loaded scene in the simulation environment, holding workflow context and task execution state.

    Args:
        name (str): The name of the scene or task.
        pcd: Point cloud data associated with the scene.
        scale (float): Scale factor for the scene geometry.
        materials: Material data for the scene.
        textures: Texture data for the scene.
        floor_heights: Floor height information for the scene.
        wf: The task workflow instance managing this scene.
        task_id (int): The index of the current task within the workflow.
        task_exec_num (int): The execution count for the current task, used for task repetition tracking.
        simulation_app: The Isaac Sim SimulationApp instance.
    """

    def __init__(
        self,
        name: str = None,
        pcd=None,
        scale: float = 1.0,
        materials=None,
        textures=None,
        floor_heights=None,
        wf=None,
        task_id: int = None,
        task_exec_num: int = 1,
        simulation_app=None,
    ):
        self.name = name
        self.pcd = pcd
        self.materials = materials
        self.textures = textures
        self.floor_heights = floor_heights
        self.scale = scale
        self.wf = wf
        self.simulation_app = simulation_app
        self.task_id = task_id
        self.plan_info = None
        self.generate_success = False
        self.task_exec_num = task_exec_num

    def __getstate__(self):
        state = self.__dict__.copy()
        del state["pcd"]
        return state

    def __setstate__(self, state):
        self.__dict__.update(state)
        self.pcd = None

    def add_plan_info(self, plan_info):
        self.plan_info = plan_info

    def flush_to_disk(self, path):
        pass

    def load_from_disk(self, path):
        pass

    def update_generate_status(self, success):
        self.generate_success = success

    def get_generate_status(self):
        return self.generate_success

    def update_task_exec_num(self, num):
        self.task_exec_num = num
