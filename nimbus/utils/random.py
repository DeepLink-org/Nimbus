import os
import random

import numpy as np
import torch

# Try to import open3d, but don't fail if it's not installed
try:
    import open3d as o3d
except ImportError:
    o3d = None


def set_all_seeds(seed):
    """
    Sets seeds for all relevant random number generators to ensure reproducibility.
    """
    os.environ["PYTHONHASHSEED"] = str(seed)
    print(f"set seed {seed} for all libraries")
    seed = int(seed)
    np.random.seed(seed)
    random.seed(seed)

    if o3d and hasattr(o3d, "utility") and hasattr(o3d.utility, "random"):
        o3d.utility.random.seed(seed)

    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)

    # These settings are crucial for deterministic results with CuDNN
    torch.backends.cudnn.deterministic = True
    torch.backends.cudnn.benchmark = False
