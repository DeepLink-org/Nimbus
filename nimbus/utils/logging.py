import logging
import os
import time
from datetime import datetime

from nimbus.utils.config import save_config


def configure_logging(exp_name, name=None, config=None):
    pod_name = os.environ.get("POD_NAME", None)
    if pod_name is not None:
        exp_name = f"{exp_name}/{pod_name}"
    log_dir = os.path.join("./output", exp_name)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    if name is None:
        log_name = f"de_time_profile_{timestamp}.log"
    else:
        log_name = f"de_{name}_time_profile_{timestamp}.log"

    log_file = os.path.join(log_dir, log_name)

    max_retries = 3
    for attempt in range(max_retries):
        try:
            os.makedirs(log_dir, exist_ok=True)
            break
        except Exception as e:
            print(f"Warning: Stale file handle when creating {log_dir}, attempt {attempt + 1}/{max_retries}")
            if attempt < max_retries - 1:
                time.sleep(3)
                continue
            else:
                raise RuntimeError(f"Failed to create log directory {log_dir} after {max_retries} attempts") from e

    if config is not None:
        config_log_file = os.path.join(log_dir, "de_config.yaml")
        save_config(config, config_log_file)

    logger = logging.getLogger("de_logger")
    logger.setLevel(logging.INFO)

    fh = logging.FileHandler(log_file, mode="a")
    formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
    fh.setFormatter(formatter)
    logger.addHandler(fh)
    logger.info("Start Data Engine")

    return logger
