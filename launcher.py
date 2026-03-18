# pylint: disable=C0413
# flake8: noqa: E402

from nimbus.utils.utils import init_env

init_env()

import argparse

from nimbus import run_data_engine
from nimbus.utils.config_processor import ConfigProcessor
from nimbus.utils.flags import set_debug_mode, set_random_seed


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", required=True, help="path to config file")
    parser.add_argument("--random_seed", help="random seed")
    parser.add_argument("--debug", action="store_true", help="enable debug mode: all errors raised immediately")
    args, extras = parser.parse_known_args()

    processor = ConfigProcessor()

    try:
        config = processor.process_config(args.config, cli_args=extras)
    except ValueError as e:
        print(f"Configuration Error: {e}")
        print(f"\n Available configuration paths can be found in: {args.config}")
        print("   Use dot notation to override nested values, e.g.:")
        print("   --stage_pipe.worker_num='[2,4]'")
        print("   --load_stage.layout_random_generator.args.random_num=500")
        return 1

    processor.print_final_config(config)

    if args.debug:
        set_debug_mode(True)

    if args.random_seed is not None:
        set_random_seed(int(args.random_seed))

    try:
        run_data_engine(config, args.random_seed)
    except Exception as e:
        raise e


if __name__ == "__main__":
    main()
