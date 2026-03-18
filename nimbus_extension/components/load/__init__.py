import nimbus.components.load as _load

from .env_loader import EnvLoader
from .env_randomizer import EnvRandomizer
from .mock_loader import MockLoader

_load.register_loader("env_loader", EnvLoader)
_load.register_loader("mock_loader", MockLoader)

_load.register_randomizer("env_randomizer", EnvRandomizer)

