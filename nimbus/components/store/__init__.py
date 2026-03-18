from .base_writer import BaseWriter

writer_dict = {}


def register(type_name: str, cls: BaseWriter):
    writer_dict[type_name] = cls
