import os

_DEBUG_KEY = "NIMBUS_DEBUG"
_RANDOM_SEED_KEY = "NIMBUS_RANDOM_SEED"


def set_debug_mode(enabled: bool) -> None:
    """Set debug mode. Must be called before ray.init() to propagate to Ray workers."""
    os.environ[_DEBUG_KEY] = "1" if enabled else "0"


def is_debug_mode() -> bool:
    return os.environ.get(_DEBUG_KEY, "0") == "1"


def set_random_seed(seed: int) -> None:
    """Set global random seed. Must be called before ray.init() to propagate to Ray workers."""
    os.environ[_RANDOM_SEED_KEY] = str(seed)


def get_random_seed() -> int | None:
    val = os.environ.get(_RANDOM_SEED_KEY)
    return int(val) if val is not None else None
