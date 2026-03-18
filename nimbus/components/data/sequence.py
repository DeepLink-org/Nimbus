import json
import os

import numpy as np
import open3d as o3d

from nimbus.components.data.camera import C2W, Camera


class Sequence:
    """
    Represents a camera trajectory sequence with associated metadata.

    Args:
        scene_name (str): The name of the scene (e.g., room identifier).
        index (str): The index or ID of this sequence within the scene.
        length (int): Optional explicit sequence length. Calculated from camera trajectories if not provided.
        data (dict): Optional additional arbitrary data associated with the sequence.
    """

    def __init__(self, scene_name: str, index: str, length: int = None, data: dict = None):
        self.scene_name = scene_name
        self.seq_name = scene_name + "_" + index
        self.index = index
        self.cam_items: list[Camera] = []
        self.path_pcd = None
        self.length = length
        self.data = data

    def __getstate__(self):
        state = self.__dict__.copy()
        state["path_pcd_color"] = np.asarray(state["path_pcd"].colors)
        state["path_pcd"] = o3d.io.write_point_cloud_to_bytes(state["path_pcd"], "mem::xyz")
        return state

    def __setstate__(self, state):
        self.__dict__.update(state)
        self.path_pcd = o3d.io.read_point_cloud_from_bytes(state["path_pcd"], "mem::xyz")
        self.path_pcd.colors = o3d.utility.Vector3dVector(state["path_pcd_color"])

    def __len__(self):
        if self.length is not None:
            return self.length
        self.length = 0
        for cam in self.cam_items:
            self.length += len(cam)
        return self.length

    def append_cam(self, item: Camera):
        self.cam_items.append(item)

    def update_pcd(self, path_pcd):
        self.path_pcd = path_pcd

    def get_length(self):
        return len(self)

    def flush_to_disk(self, path):
        path_to_save = os.path.join(path, "trajectory_" + self.index)
        print(f"seq {self.seq_name} try to save path in {path_to_save}")
        os.makedirs(path_to_save, exist_ok=True)
        if self.path_pcd is not None:
            pcd_path = os.path.join(path_to_save, "path.ply")
            o3d.io.write_point_cloud(pcd_path, self.path_pcd)

        # Single camera: save in root directory
        if len(self.cam_items) == 1:
            cam = self.cam_items[0]
            camera_trajectory_list = [t.matrix for t in cam.trajectory]
            save_dict = {
                "camera_intrinsic": cam.intrinsic if cam.intrinsic is not None else None,
                "camera_extrinsic": cam.extrinsic if cam.extrinsic is not None else None,
                "camera_trajectory": camera_trajectory_list,
            }
            traj_path = os.path.join(path_to_save, "data.json")
            json_object = json.dumps(save_dict, indent=4)
            with open(traj_path, "w", encoding="utf-8") as outfile:
                outfile.write(json_object)
        # Multiple cameras: save in camera_0/, camera_1/, etc.
        else:
            for idx, cam in enumerate(self.cam_items):
                camera_dir = os.path.join(path_to_save, f"camera_{idx}")
                os.makedirs(camera_dir, exist_ok=True)
                camera_trajectory_list = [t.matrix for t in cam.trajectory]
                save_dict = {
                    "camera_intrinsic": cam.intrinsic if cam.intrinsic is not None else None,
                    "camera_extrinsic": cam.extrinsic if cam.extrinsic is not None else None,
                    "camera_trajectory": camera_trajectory_list,
                }
                traj_path = os.path.join(camera_dir, "data.json")
                json_object = json.dumps(save_dict, indent=4)
                with open(traj_path, "w", encoding="utf-8") as outfile:
                    outfile.write(json_object)

    def load_from_disk(self, path):
        print(f"seq {self.seq_name} try to load path from {path}")

        pcd_path = os.path.join(path, "path.ply")
        if os.path.exists(pcd_path):
            self.path_pcd = o3d.io.read_point_cloud(pcd_path)

        # Clear existing camera items
        self.cam_items = []

        # Check if single camera format (data.json in root)
        traj_path = os.path.join(path, "data.json")
        if os.path.exists(traj_path):
            with open(traj_path, "r", encoding="utf-8") as infile:
                data = json.load(infile)

            camera_trajectory_list = []
            for trajectory in data["camera_trajectory"]:
                camera_trajectory_list.append(C2W(matrix=trajectory))

            cam = Camera(
                trajectory=camera_trajectory_list,
                intrinsic=data.get("camera_intrinsic"),
                extrinsic=data.get("camera_extrinsic"),
            )
            self.cam_items.append(cam)
        else:
            # Multiple camera format (camera_0/, camera_1/, etc.)
            idx = 0
            while True:
                camera_dir = os.path.join(path, f"camera_{idx}")
                camera_json = os.path.join(camera_dir, "data.json")
                if not os.path.exists(camera_json):
                    break

                with open(camera_json, "r", encoding="utf-8") as infile:
                    data = json.load(infile)

                camera_trajectory_list = []
                for trajectory in data["camera_trajectory"]:
                    camera_trajectory_list.append(C2W(matrix=trajectory))

                cam = Camera(
                    trajectory=camera_trajectory_list,
                    intrinsic=data.get("camera_intrinsic"),
                    extrinsic=data.get("camera_extrinsic"),
                )
                self.cam_items.append(cam)
                idx += 1

            assert len(self.cam_items) > 0, f"No camera data found in {path}"
