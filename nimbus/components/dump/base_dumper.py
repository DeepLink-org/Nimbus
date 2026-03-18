import time
from abc import abstractmethod

from pympler import asizeof

from nimbus.components.data.iterator import Iterator
from nimbus.components.data.package import Package
from nimbus.utils.utils import unpack_iter_data


class BaseDumper(Iterator):
    def __init__(self, data_iter, output_queue, max_queue_num=1):
        super().__init__()
        self.data_iter = data_iter
        self.scene = None
        self.output_queue = output_queue
        self.total_case = 0
        self.success_case = 0
        self.max_queue_num = max_queue_num

    def __iter__(self):
        return self

    def _next(self):
        try:
            data = next(self.data_iter)
            scene, seq, obs = unpack_iter_data(data)
            self.total_case += 1
            if scene is not None:
                if self.scene is not None and (
                    scene.task_id != self.scene.task_id
                    or scene.name != self.scene.name
                    or scene.task_exec_num != self.scene.task_exec_num
                ):
                    self.logger.info(
                        f"Scene {self.scene.name} generate finish, success rate: {self.success_case}/{self.total_case}"
                    )
                    self.total_case = 1
                    self.success_case = 0
                self.scene = scene
            if obs is None and seq is None:
                self.logger.info(f"generate failed, skip once! success rate: {self.success_case}/{self.total_case}")
                if self.scene is not None:
                    self.scene.update_generate_status(success=False)
                return None
            io_start_time = time.time()
            if self.output_queue is not None:
                obj = self.dump(seq, obs)
                pack = Package(obj, task_id=scene.task_id, task_name=scene.name)
                pack.serialize()

                wait_time = time.time()
                while self.output_queue.qsize() >= self.max_queue_num:
                    time.sleep(1)
                end_time = time.time()
                self.collect_wait_time_info(end_time - wait_time)

                st = time.time()
                self.output_queue.put(pack)
                ed = time.time()
                self.logger.info(f"put time: {ed - st}, data size: {asizeof.asizeof(obj)}")
            else:
                obj = self.dump(seq, obs)
            self.success_case += 1
            self.scene.update_generate_status(success=True)
            self.collect_seq_info(1, time.time() - io_start_time)
        except StopIteration:
            if self.output_queue is not None:
                pack = Package(None, stop_sig=True)
                self.output_queue.put(pack)
            if self.scene is not None:
                self.logger.info(
                    f"Scene {self.scene.name} generate finish, success rate: {self.success_case}/{self.total_case}"
                )
            raise StopIteration("no data")
        except Exception as e:
            self.logger.exception(f"Error during data dumping: {e}")
            raise e

    @abstractmethod
    def dump(self, seq, obs):
        raise NotImplementedError("This method should be overridden by subclasses")
