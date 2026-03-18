import nimbus.components.dedump as _dedump

from .base_dedumper import Dedumper

_dedump.register("de", Dedumper)
