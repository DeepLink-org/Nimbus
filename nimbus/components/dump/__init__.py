from .base_dumper import BaseDumper

dumper_dict = {}


def register(type_name: str, cls: BaseDumper):
    dumper_dict[type_name] = cls
