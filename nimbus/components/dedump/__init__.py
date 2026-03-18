from nimbus.components.data.iterator import Iterator

dedumper_dict = {}


def register(type_name: str, cls: Iterator):
    dedumper_dict[type_name] = cls
