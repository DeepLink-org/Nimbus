# flake8: noqa: F401
# pylint: disable=C0413

from .base_randomizer import LayoutRandomizer
from .base_scene_loader import SceneLoader

scene_loader_dict = {}
layout_randomizer_dict = {}


def register_loader(type_name: str, cls: SceneLoader):
    scene_loader_dict[type_name] = cls


def register_randomizer(type_name: str, cls: LayoutRandomizer):
    layout_randomizer_dict[type_name] = cls
