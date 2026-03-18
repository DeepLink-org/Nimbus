from omegaconf import OmegaConf


def load_config(*yaml_files, cli_args=None):
    if cli_args is None:
        cli_args = []
    yaml_confs = [OmegaConf.load(f) for f in yaml_files]
    cli_conf = OmegaConf.from_cli(cli_args)
    conf = OmegaConf.merge(*yaml_confs, cli_conf)
    OmegaConf.resolve(conf)
    return conf


def config_to_primitive(config, resolve=True):
    return OmegaConf.to_container(config, resolve=resolve)


def save_config(config, path):
    with open(path, "w", encoding="utf-8") as fp:
        OmegaConf.save(config=config, f=fp)
