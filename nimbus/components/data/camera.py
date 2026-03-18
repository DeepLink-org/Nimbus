from dataclasses import dataclass
from typing import Any, Dict, List, Optional

import numpy as np


@dataclass
class C2W:
    """
    Represents a camera-to-world transformation matrix.

    Attributes:
        matrix (List[float]): A list of 16 floats representing the 4x4 transformation matrix in row-major order.
    """

    matrix: List[float]


@dataclass
class Camera:
    """
    Represents a single camera pose in the trajectory.

    Attributes:
        trajectory (List[C2W]): List of C2W transformations for this camera pose.
        intrinsic (Optional[List[float]]): 3x3 camera intrinsic matrix: [[fx, 0, cx], [0, fy, cy], [0, 0, 1]].
        extrinsic (Optional[List[float]]): 4x4 tobase_extrinsic matrix representing the camera mounting offset
            relative to the robot base (height + pitch).
        length (Optional[int]): Length of the trajectory in number of frames.
        depths (Optional[list[np.ndarray]]): List of depth images captured by this camera.
        rgbs (Optional[list[np.ndarray]]): List of RGB images captured by this camera.
        uv_tracks (Optional[Dict[str, Any]]): UV tracking data in the format
            {mesh_name: {"per_frame": list, "width": W, "height": H}}.
        uv_mesh_names (Optional[List[str]]): List of mesh names being tracked in the UV tracking data.
    """

    trajectory: List[C2W]
    intrinsic: List[float] = None
    extrinsic: List[float] = None
    length: int = None
    depths: list[np.ndarray] = None
    rgbs: list[np.ndarray] = None
    uv_tracks: Optional[Dict[str, Any]] = None
    uv_mesh_names: Optional[List[str]] = None

    def __len__(self):
        if self.length is not None:
            return self.length
        self._check_length()
        self.length = len(self.trajectory)
        return len(self.trajectory)

    def _check_length(self):
        if self.depths is not None and len(self.depths) != len(self.trajectory):
            raise ValueError("Length of depths does not match length of trajectory")
        if self.rgbs is not None and len(self.rgbs) != len(self.trajectory):
            raise ValueError("Length of rgbs does not match length of trajectory")
        if self.uv_tracks is not None:
            for mesh_name, track_data in self.uv_tracks.items():
                if len(track_data["per_frame"]) != len(self.trajectory):
                    raise ValueError(f"Length of uv_tracks for mesh {mesh_name} does not match length of trajectory")

    def append_rgb(self, rgb_image: np.ndarray):
        if self.rgbs is None:
            self.rgbs = []
        self.rgbs.append(rgb_image)

    def append_depth(self, depth_image: np.ndarray):
        if self.depths is None:
            self.depths = []
        self.depths.append(depth_image)
