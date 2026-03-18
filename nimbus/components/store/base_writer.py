import time
from abc import abstractmethod
from concurrent.futures import ThreadPoolExecutor
from copy import copy

from nimbus.components.data.iterator import Iterator
from nimbus.components.data.observation import Observations
from nimbus.components.data.scene import Scene
from nimbus.components.data.sequence import Sequence
from nimbus.daemon import ComponentStatus, StatusReporter
from nimbus.utils.flags import is_debug_mode
from nimbus.utils.utils import unpack_iter_data


def run_batch(func, args):
    for arg in args:
        func(*arg)


class BaseWriter(Iterator):
    """
    A base class for writing generated sequences and observations to disk. This class defines the structure for
    writing data and tracking the writing process. It manages the current scene, success and total case counts,
    and provides hooks for subclasses to implement specific data writing logic. The writer supports both synchronous
    and asynchronous batch writing modes, allowing for efficient data handling in various scenarios.

    Args:
        data_iter (Iterator): An iterator that provides data to be written, typically containing scenes,
            sequences, and observations.
        seq_output_dir (str): The directory where generated sequences will be saved. Can be None
            if sequence output is not needed.
        obs_output_dir (str): The directory where generated observations will be saved. Can be None
            if observation output is not needed.
        batch_async (bool): If True, the writer will use asynchronous batch writing to improve performance
            when handling large amounts of data. Default is True.
        async_threshold (int): The maximum number of asynchronous write operations that can be in progress
            at the same time. If the threshold is reached, the writer will wait for the oldest operation
            to complete before starting a new one. Default is 1.
        batch_size (int): The number of data items to write in each batch when using asynchronous writing.
            Default is 2, and it will be capped at 8 to prevent potential issues with too many concurrent operations.
    """

    def __init__(
        self,
        data_iter: Iterator[tuple[Scene, Sequence, Observations]],
        seq_output_dir: str,
        obs_output_dir: str,
        batch_async: bool = True,
        async_threshold: int = 1,
        batch_size: int = 2,
    ):
        super().__init__()
        assert (
            seq_output_dir is not None or obs_output_dir is not None
        ), "At least one output directory must be provided"
        self.data_iter = data_iter
        self.seq_output_dir = seq_output_dir
        self.obs_output_dir = obs_output_dir
        self.scene = None
        self.async_mode = batch_async
        self.batch_size = batch_size if batch_size <= 8 else 8
        if batch_async and batch_size > self.batch_size:
            self.logger.info("Batch size is larger than 8(probably cause program hang), batch size will be set to 8")
        self.async_threshold = async_threshold
        self.flush_executor = ThreadPoolExecutor(max_workers=max(1, 64 // self.batch_size))
        self.flush_threads = []
        self.data_buffer = []
        self.logger.info(
            f"Batch Async Write Mode: {self.async_mode}, async threshold: {self.async_threshold}, batch size:"
            f" {self.batch_size}"
        )
        self.total_case = 0
        self.success_case = 0
        self.last_scene_key = None
        self.status_reporter = StatusReporter(self.__class__.__name__)

    def _next(self):
        try:
            data = next(self.data_iter)
            scene, seq, obs = unpack_iter_data(data)

            new_key = (scene.task_id, scene.name, scene.task_exec_num) if scene is not None else None

            self.scene = scene

            if new_key != self.last_scene_key:
                if self.scene is not None and self.last_scene_key is not None:
                    self.logger.info(
                        f"Scene {self.scene.name} generate finish, success rate: {self.success_case}/{self.total_case}"
                    )
                self.success_case = 0
                self.total_case = 0
                self.last_scene_key = new_key

            if self.scene is None:
                return None

            self.total_case += 1

            self.status_reporter.update_status(ComponentStatus.RUNNING)
            if seq is None and obs is None:
                self.logger.info(f"generate failed, skip once! success rate: {self.success_case}/{self.total_case}")
                self.scene.update_generate_status(success=False)
                return None
            scene_name = self.scene.name
            io_start_time = time.time()
            if self.async_mode:
                cp_start_time = time.time()
                cp = copy(self.scene.wf)
                cp_end_time = time.time()
                if self.scene.wf is not None:
                    self.logger.info(f"Scene {scene_name} workflow copy time: {cp_end_time - cp_start_time:.2f}s")
                self.data_buffer.append((cp, scene_name, seq, obs))
                if len(self.data_buffer) >= self.batch_size:
                    self.flush_threads = [t for t in self.flush_threads if not t.done()]

                    if len(self.flush_threads) >= self.async_threshold:
                        self.logger.info("Max async workers reached, waiting for the oldest thread to finish")
                        self.flush_threads[0].result()
                        self.flush_threads = self.flush_threads[1:]

                    to_flush_buffer = self.data_buffer.copy()
                    async_flush = self.flush_executor.submit(run_batch, self.flush_to_disk, to_flush_buffer)
                    if is_debug_mode():
                        async_flush.result()  # surface exceptions immediately in debug mode
                    self.flush_threads.append(async_flush)
                    self.data_buffer = []
                flush_length = len(obs) if obs is not None else len(seq)
            else:
                flush_length = self.flush_to_disk(self.scene.wf, scene_name, seq, obs)
            self.success_case += 1
            self.scene.update_generate_status(success=True)
            self.collect_io_frame_info(flush_length, time.time() - io_start_time)
            self.status_reporter.update_status(ComponentStatus.COMPLETED)
            return None
        except StopIteration:
            if self.async_mode:
                if len(self.data_buffer) > 0:
                    async_flush = self.flush_executor.submit(run_batch, self.flush_to_disk, self.data_buffer)
                    self.flush_threads.append(async_flush)
                for thread in self.flush_threads:
                    thread.result()
            if self.scene is not None:
                self.logger.info(
                    f"Scene {self.scene.name} generate finish, success rate: {self.success_case}/{self.total_case}"
                )
            raise StopIteration("no data")
        except Exception as e:
            self.logger.exception(f"Error during data writing: {e}")
            raise e

    def __del__(self):
        for thread in self.flush_threads:
            thread.result()
        self.logger.info(f"Writer {len(self.flush_threads)} threads closed")
        # Close the simulation app if it exists
        if self.scene is not None and self.scene.simulation_app is not None:
            self.logger.info("Closing simulation app")
            self.scene.simulation_app.close()

    @abstractmethod
    def flush_to_disk(self, task, scene_name, seq, obs):
        raise NotImplementedError("This method should be overridden by subclasses")
