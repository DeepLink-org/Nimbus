import os

from nimbus.components.store import BaseWriter


class EnvWriter(BaseWriter):
    """
    A writer that saves generated sequences and observations to disk for environment simulations.
    This class extends the BaseWriter to provide specific implementations for handling data related
    to environment simulations.

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
            Default is 1, and it will be capped at 8 to prevent potential issues with too many concurrent operations.
    """

    def __init__(
        self, data_iter, seq_output_dir=None, output_dir=None, batch_async=True, async_threshold=1, batch_size=1
    ):
        super().__init__(
            data_iter,
            seq_output_dir,
            output_dir,
            batch_async=batch_async,
            async_threshold=async_threshold,
            batch_size=batch_size,
        )

    def flush_to_disk(self, task, scene_name, seq, obs):
        try:
            scene_name = self.scene.name
            if obs is not None and self.obs_output_dir is not None:
                log_dir = os.path.join(self.obs_output_dir, scene_name)
                self.logger.info(f"Try to save obs in {log_dir}")
                length = task.save(log_dir)
                self.logger.info(f"Saved {length} obs output saved in {log_dir}")
            elif seq is not None and self.seq_output_dir is not None:
                log_dir = os.path.join(self.seq_output_dir, scene_name)
                self.logger.info(f"Try to save seq in {log_dir}")
                length = task.save_seq(log_dir)
                self.logger.info(f"Saved {length} seq output saved in {log_dir}")
            else:
                self.logger.info("Skip this storage")
            return length
        except Exception as e:
            self.logger.info(f"Failed to save data for scene {scene_name}: {e}")
            raise e
