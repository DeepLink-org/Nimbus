from nimbus.components.data.iterator import Iterator

plan_with_render_dict = {}


def register(type_name: str, cls: Iterator):
    plan_with_render_dict[type_name] = cls
