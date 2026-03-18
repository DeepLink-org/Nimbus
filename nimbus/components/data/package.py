import pickle


class Package:
    """
    A class representing a data package that can be serialized and deserialized for pipeline.

    Args:
        data: The actual data contained in the package, which can be of any type.
        task_id (int): The ID of the task associated with this package.
        task_name (str): The name of the task associated with this package.
        stop_sig (bool): Whether this package signals the pipeline to stop.
    """

    def __init__(self, data, task_id: int = -1, task_name: str = None, stop_sig: bool = False):
        self.is_ser = False
        self.data = data
        self.task_id = task_id
        self.task_name = task_name
        self.stop_sig = stop_sig

    def serialize(self):
        assert self.is_ser is False, "data is already serialized"
        self.data = pickle.dumps(self.data)
        self.is_ser = True

    def deserialize(self):
        assert self.is_ser is True, "data is already deserialized"
        self.data = pickle.loads(self.data)
        self.is_ser = False

    def is_serialized(self):
        return self.is_ser

    def get_data(self):
        return self.data

    def should_stop(self):
        return self.stop_sig is True
