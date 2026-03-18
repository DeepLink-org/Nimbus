import logging
import time
from abc import abstractmethod
from collections.abc import Iterator
from typing import Generic, TypeVar

T = TypeVar("T")


# pylint: disable=E0102
class Iterator(Iterator, Generic[T]):
    def __init__(self, max_retry=3):
        self._next_calls = 0.0
        self._next_total_time = 0.0
        self._init_time_costs = 0.0
        self._init_times = 0
        self._frame_compute_time = 0.0
        self._frame_compute_frames = 0.0
        self._frame_io_time = 0.0
        self._frame_io_frames = 0.0
        self._wait_time = 0.0
        self._seq_num = 0.0
        self._seq_time = 0.0
        self.logger = logging.getLogger("de_logger")
        self.max_retry = max_retry
        self.retry_num = 0

    def record_init_time(self, time_costs):
        self._init_times += 1
        self._init_time_costs += time_costs

    def __iter__(self):
        return self

    def __next__(self):
        start_time = time.time()
        try:
            result = self._next()
        except StopIteration:
            self._log_statistics()
            raise
        end_time = time.time()
        self._next_calls += 1
        self._next_total_time += end_time - start_time
        return result

    def collect_compute_frame_info(self, length, time_costs):
        self._frame_compute_frames += length
        self._frame_compute_time += time_costs

    def collect_io_frame_info(self, length, time_costs):
        self._frame_io_frames += length
        self._frame_io_time += time_costs

    def collect_wait_time_info(self, time_costs):
        self._wait_time += time_costs

    def collect_seq_info(self, length, time_costs):
        self._seq_num += length
        self._seq_time += time_costs

    @abstractmethod
    def _next(self):
        raise NotImplementedError("Subclasses should implement this method.")

    def _log_statistics(self):
        class_name = self.__class__.__name__
        self.logger.info(
            f"{class_name}: Next method called {self._next_calls} times, total time:"
            f" {self._next_total_time:.6f} seconds"
        )
        if self._init_time_costs > 0:
            self.logger.info(
                f"{class_name}: Init time: {self._init_time_costs:.6f} seconds, init {self._init_times} times"
            )
        if self._frame_compute_time > 0:
            avg_compute_time = self._frame_compute_time / self._frame_compute_frames
            self.logger.info(
                f"{class_name}: compute frame num: {self._frame_compute_frames}, total time:"
                f" {self._frame_compute_time:.6f} seconds, average time: {avg_compute_time:.6f} seconds per frame"
            )
        if self._frame_io_frames > 0:
            avg_io_time = self._frame_io_time / self._frame_io_frames
            self.logger.info(
                f"{class_name}: io frame num: {self._frame_io_frames}, total time: {self._frame_io_time:.6f} seconds,"
                f" average time: {avg_io_time:.6f} seconds per frame"
            )
        if self._wait_time > 0:
            self.logger.info(f"{class_name}: wait time: {self._wait_time:.6f} seconds")
        if self._seq_time > 0:
            avg_seq_time = self._seq_time / self._seq_num
            self.logger.info(
                f"{class_name}: seq num: {self._seq_num:.6f}, total time: {self._seq_time:.6f} seconds, average time:"
                f" {avg_seq_time:.6f} seconds per sequence"
            )
