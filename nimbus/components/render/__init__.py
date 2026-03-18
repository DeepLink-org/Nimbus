from .base_renderer import BaseRenderer

renderer_dict = {}


def register(type_name: str, cls: BaseRenderer):
    renderer_dict[type_name] = cls
