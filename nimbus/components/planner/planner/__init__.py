path_planner_dict = {}


def register(type_name: str, cls):
    path_planner_dict[type_name] = cls
