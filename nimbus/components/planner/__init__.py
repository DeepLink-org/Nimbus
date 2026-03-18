from .base_seq_planner import SequencePlanner

seq_planner_dict = {}


def register(type_name: str, cls: SequencePlanner):
    seq_planner_dict[type_name] = cls
