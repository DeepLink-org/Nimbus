import os

import cv2
import imageio
import numpy as np

from nimbus.components.data.camera import Camera


class Observations:
    """
    Represents a single observation of a scene, which may include multiple camera trajectories and associated data.
    Each observation is identified by a unique name and index, and can contain multiple Camera items that capture
    different viewpoints or modalities of the same scene.

    Args:
        scene_name (str): The name of the scene associated with this observation.
        index (str): The index or ID of this observation within the scene.
        length (int): Optional total length of the observation. Calculated from camera trajectories if not provided.
        data (dict): Optional dictionary for storing additional arbitrary data, such as metadata or annotations.
    """

    def __init__(self, scene_name: str, index: str, length: int = None, data: dict = None):
        self.scene_name = scene_name
        self.obs_name = scene_name + "_" + index
        self.index = index
        self.cam_items = []
        self.length = length
        self.data = data

    def __getstate__(self):
        state = self.__dict__.copy()
        return state

    def __setstate__(self, state):
        self.__dict__.update(state)

    def append_cam(self, item: Camera):
        self.cam_items.append(item)

    def __len__(self):
        if self.length is not None:
            return self.length
        self.length = 0
        for cam in self.cam_items:
            self.length += len(cam)
        return self.length

    def get_length(self):
        return len(self)

    def flush_to_disk(self, path, video_fps=10):
        path_to_save = os.path.join(path, "trajectory_" + self.index)
        print(f"obs {self.obs_name} try to save path in {path_to_save}")
        os.makedirs(path_to_save, exist_ok=True)

        # Single camera: save in root directory
        if len(self.cam_items) == 1:
            cam = self.cam_items[0]
            self._save_camera_data(path_to_save, cam, video_fps)
        # Multiple cameras: save in camera_0/, camera_1/, etc.
        else:
            for idx, cam in enumerate(self.cam_items):
                camera_dir = os.path.join(path_to_save, f"camera_{idx}")
                os.makedirs(camera_dir, exist_ok=True)
                self._save_camera_data(camera_dir, cam, video_fps)

    def _save_camera_data(self, save_dir, cam: Camera, video_fps):
        """Helper method to save camera visualization data (rgbs, depths) to a directory."""
        # Save RGB and depth images if available
        if cam.rgbs is not None and len(cam.rgbs) > 0:
            rgb_images_path = os.path.join(save_dir, "rgb/")
            os.makedirs(rgb_images_path, exist_ok=True)

            fps_path = os.path.join(save_dir, "fps.mp4")

            for idx, rgb_item in enumerate(cam.rgbs):
                rgb_filename = os.path.join(rgb_images_path, f"{idx}.jpg")
                cv2.imwrite(rgb_filename, cv2.cvtColor(rgb_item, cv2.COLOR_BGR2RGB))

            imageio.mimwrite(fps_path, cam.rgbs, fps=video_fps)

        if cam.depths is not None and len(cam.depths) > 0:
            depth_images_path = os.path.join(save_dir, "depth/")
            os.makedirs(depth_images_path, exist_ok=True)

            depth_path = os.path.join(save_dir, "depth.mp4")

            # Create a copy for video (8-bit version)
            depth_video_frames = []
            for idx, depth_item in enumerate(cam.depths):
                depth_filename = os.path.join(depth_images_path, f"{idx}.png")
                cv2.imwrite(depth_filename, depth_item)
                depth_video_frames.append((depth_item >> 8).astype(np.uint8))

            imageio.mimwrite(depth_path, depth_video_frames, fps=video_fps)

        # Save UV tracking visualizations if available
        if cam.uv_tracks is not None and cam.uv_mesh_names is not None and cam.rgbs is not None:
            num_frames = len(cam.rgbs)
            try:
                from nimbus_extension.components.render.brpc_utils.point_tracking import (
                    make_uv_overlays_and_video,
                )
            except ImportError as e:
                raise ImportError(
                    "UV tracking visualization requires nimbus_extension. "
                    "Please add `import nimbus_extension` before running the pipeline."
                ) from e

            make_uv_overlays_and_video(
                cam.rgbs,
                cam.uv_tracks,
                cam.uv_mesh_names,
                start_frame=0,
                end_frame=num_frames,
                fps=video_fps,
                path_to_save=save_dir,
            )
