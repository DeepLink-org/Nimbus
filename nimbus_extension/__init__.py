"""
nimbus_extension — official component implementations for the nimbus framework.

Importing this package registers all built-in components into the nimbus
component registries (dumper_dict, renderer_dict, etc.) so they are
available for use in pipeline configs.

Usage in launcher.py::

    import nimbus_extension  # registers all components
    from nimbus import run_data_engine
"""

from . import components  # noqa: F401  triggers all register() calls
