import nimbus.components.dump as _dump

from .env_dumper import EnvDumper

_dump.register("env", EnvDumper)
