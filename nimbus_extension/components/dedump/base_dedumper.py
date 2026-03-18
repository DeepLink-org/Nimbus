import time

from nimbus.components.data.iterator import Iterator
from nimbus.components.data.package import Package


class Dedumper(Iterator):
    def __init__(self, input_queue=None):
        super().__init__()
        self.input_queue = input_queue

    def __iter__(self):
        return self

    def _next(self) -> Package:
        try:
            self.logger.info("Dedumper try to get package from queue")
            package = self.input_queue.get()
            self.logger.info(f"get task {package.task_name} package from queue")
            st = time.time()

            assert isinstance(package, Package), f"the transfered data type must be Package, but it is {type(package)}"
            if package.should_stop():
                self.logger.info("received stop signal")
                raise StopIteration()
            else:
                assert (
                    package.is_serialized() and package.task_id >= 0
                ), "received data must be deserialized and task id must be greater than 0"
                package.deserialize()
            self.collect_compute_frame_info(1, time.time() - st)
            return package
        except StopIteration:
            raise StopIteration("No more packages to process.")
        except Exception as e:
            self.logger.exception(f"Error during dedumping: {e}")
            raise e
