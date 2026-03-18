"""
Config Processor: Responsible for identifying, converting, and loading configuration files.
"""

from omegaconf import DictConfig, OmegaConf

from nimbus.utils.config import load_config


class ConfigProcessor:
    """Config processor class"""

    def __init__(self):
        pass

    def _check_config_path_exists(self, config, path):
        """
        Check if a configuration path exists in the config object

        Args:
            config: OmegaConf config object
            path: String path like 'stage_pipe.worker_num' or 'load_stage.scene_loader.args.random_num'

        Returns:
            bool: Whether the path exists in the config
        """
        try:
            keys = path.split(".")
            current = config
            for key in keys:
                if isinstance(current, DictConfig):
                    if key not in current:
                        return False
                    current = current[key]
                else:
                    return False
            return True
        except Exception:
            return False

    def _validate_cli_args(self, config, cli_args):
        """
        Validate that all CLI arguments correspond to existing paths in the config

        Args:
            config: OmegaConf config object
            cli_args: List of command line arguments

        Raises:
            ValueError: If any CLI argument path doesn't exist in the config
        """
        if not cli_args:
            return

        # Clean up CLI args to remove -- prefix if present
        cleaned_cli_args = []
        for arg in cli_args:
            if arg.startswith("--"):
                cleaned_cli_args.append(arg[2:])  # Remove the -- prefix
            else:
                cleaned_cli_args.append(arg)

        # Parse CLI args to get the override paths
        try:
            cli_conf = OmegaConf.from_cli(cleaned_cli_args)
        except Exception as e:
            raise ValueError(f"Invalid CLI argument format: {e}. Please use format like: stage_pipe.worker_num='[2,4]'")

        def check_nested_paths(conf, prefix=""):
            """Recursively check all paths in the CLI config"""
            for key, value in conf.items():
                current_path = f"{prefix}.{key}" if prefix else key

                if isinstance(value, DictConfig):
                    # Check if this intermediate path exists
                    if not self._check_config_path_exists(config, current_path):
                        raise ValueError(f"Configuration path '{current_path}' does not exist in the config file")
                    # Recursively check nested paths
                    check_nested_paths(value, current_path)
                else:
                    # Check if this leaf path exists
                    if not self._check_config_path_exists(config, current_path):
                        raise ValueError(f"Configuration path '{current_path}' does not exist in the config file")

        try:
            check_nested_paths(cli_conf)
        except ValueError:
            raise
        except Exception:
            # If there's an issue parsing CLI args, provide helpful error message
            raise ValueError("Invalid CLI argument format. Please use format like: --key=value or --nested.key=value")

    def process_config(self, config_path, cli_args=None):
        """
        Process the config file

        Args:
            config_path: Path to the config file
            cli_args: List of command line arguments

        Returns:
            OmegaConf: Processed config object
        """
        # Clean up CLI args to remove -- prefix if present
        cleaned_cli_args = []
        if cli_args:
            for arg in cli_args:
                if arg.startswith("--"):
                    cleaned_cli_args.append(arg[2:])  # Remove the -- prefix
                else:
                    cleaned_cli_args.append(arg)

        # Load config first without CLI args to validate paths
        try:
            base_config = load_config(config_path)
        except Exception as e:
            raise ValueError(f"Error loading config: {e}")

        # Validate that CLI arguments correspond to existing paths
        if cli_args:
            self._validate_cli_args(base_config, cli_args)

        # Now load config with CLI args (validation passed)
        config = load_config(config_path, cli_args=cleaned_cli_args)

        return config

    def print_final_config(self, config):
        """
        Print the final running config

        Args:
            config: OmegaConf config object
        """
        print("=" * 50)
        print("final config:")
        print("=" * 50)
        print(OmegaConf.to_yaml(config))
