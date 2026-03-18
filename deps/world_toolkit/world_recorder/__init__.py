import pickle

import numpy as np
from omni.isaac.core.articulations.articulation import Articulation
from omni.isaac.core.robots.robot import Robot
from omni.isaac.core.utils.numpy.transformations import get_local_from_world
from omni.isaac.core.utils.prims import get_prim_at_path, get_prim_parent
from omni.isaac.core.utils.xforms import get_world_pose
from pxr import Gf, Usd, UsdGeom

from workflows.utils.utils import get_link


class WorldRecorder:
    """
    WorldRecorder handles recording and replaying simulation states.

    Two modes are supported:
    - step_replay=False: Records prim poses for fast geometric replay
    - step_replay=True: Records robot joint positions and object world poses
      for physics-accurate replay via set_joint_positions / set_world_pose
    """

    def __init__(self, world, robots: list, objs: list, step_replay: bool = False):
        self.world = world
        self.stage = world.stage
        self.xform_prims = []
        self.prim_poses = []
        self.prim_visibilities = []
        self.replay_counter = 0
        self.num_steps = 0

        for robot_name, robot in robots.items():
            if not isinstance(robot, Robot):
                raise TypeError(
                    f"Robot '{robot_name}' must be an instance of omni.isaac.core.robots.robot.Robot "
                    f"or its subclass, got {type(robot).__name__} instead."
                )

        self.robots = robots
        self.objs = objs
        self.step_replay = step_replay

        self._initialize_xform_prims()

        if self.step_replay:
            print("use joint_position to replay, WorldRecorder will record joint positions and object poses")
            self.robot_joint_data = {name: [] for name in robots}
            self.object_state_data = {name: [] for name in objs}
        else:
            print("use prim poses to replay, WorldRecorder will record prim poses for replay")

    def _initialize_xform_prims(self):
        self.robots_prim = []
        robots_prim_paths = [robot.prim_path for robot in self.robots.values()]
        for robot_prim_path in robots_prim_paths:
            robot_prim_path = get_prim_at_path(robot_prim_path)
            link_dict = get_link(robot_prim_path)
            robots_paths = list(link_dict.values())
            print(robots_paths)
            self.robots_prim.extend(robots_paths)

        self.objects_prim = []
        record_objects = self.objs
        for _, obj in record_objects.items():
            object_prim_path = obj.prim
            if isinstance(obj, Articulation):
                link_dict = get_link(object_prim_path)
                object_paths = list(link_dict.values())
                self.objects_prim.extend(object_paths)
            else:
                self.objects_prim.append(object_prim_path)
        self.xform_prims.extend(self.robots_prim)
        self.xform_prims.extend(self.objects_prim)
        print(f"Found {len(self.xform_prims)} xformable prims")

    def record(self):
        """Record current frame state."""
        if self.step_replay:
            for robot_name, robot in self.robots.items():
                joint_positions = robot.get_joint_positions()
                self.robot_joint_data[robot_name].append(joint_positions)

            for obj_name, obj in self.objs.items():
                translation, orientation = obj.get_world_pose()
                state = {
                    "translation": translation,
                    "orientation": orientation,
                }
                if isinstance(obj, Articulation):
                    state["joint_positions"] = obj.get_joint_positions()
                self.object_state_data[obj_name].append(state)

            frame_visibilities = []
            for prim in self.xform_prims:
                visibility = prim.GetAttribute("visibility").Get()
                frame_visibilities.append(visibility)
            self.prim_visibilities.append(frame_visibilities)

            self.num_steps += 1
        else:
            frame_poses = []
            frame_visibilities = []
            for prim in self.xform_prims:
                world_pose = get_world_pose(prim.GetPath().pathString)
                frame_poses.append([world_pose[0].tolist(), world_pose[1].tolist()])

                visibility = prim.GetAttribute("visibility").Get()
                frame_visibilities.append(visibility)

            self.prim_poses.append(frame_poses)
            self.prim_visibilities.append(frame_visibilities)
            self.num_steps += 1

    def warmup(self):
        """Internal warmup logic for different modes."""
        if self.step_replay:
            print("Warming up simulation (joint_position mode)...")
            if self.num_steps > 0:
                self._replay_from_joint_positions(increment_counter=False)
                for _ in range(10):
                    self.world.step(render=True)
                    self.world.get_observations()
            print("Warmup completed. Starting replay...")
        else:
            print("Warming up (prim poses mode)...")
            if self.num_steps > 0:
                self._replay_from_prim_poses(increment_counter=False)
                for _ in range(10):
                    self.world.render()
                    self.world.get_observations()
            print("Warmup completed. Starting replay...")

    def get_total_steps(self):
        return self.num_steps

    def replay(self):
        """
        Unified replay interface. Automatically selects the appropriate replay method
        based on mode setting.

        Returns:
            bool: True if replay is complete, False otherwise
        """
        if self.step_replay:
            return self._replay_from_joint_positions()
        else:
            return self._replay_from_prim_poses()

    def _replay_from_joint_positions(self, increment_counter: bool = True):
        """
        Replay from recorded joint position / world pose data.
        Uses world.step(render=True) for proper physics and joint constraints.
        """
        if self.num_steps == 0:
            print("No steps to replay")
            return True

        if self.replay_counter == 0:
            print(f"Starting replay of {self.num_steps} steps from joint position data...")

        if self.replay_counter < self.num_steps:
            self._apply_recorded_states()
            self.world.step(render=True)
            if increment_counter:
                self.replay_counter += 1
            return False
        else:
            print("Replay complete")
            return True

    def _replay_from_prim_poses(self, increment_counter: bool = True):
        if self.replay_counter == 0:
            print(f"Re-found {len(self.xform_prims)} xformable prims")
        if self.replay_counter < self.num_steps:
            frame_poses = self.prim_poses[self.replay_counter]
            frame_visibilities = self.prim_visibilities[self.replay_counter]
            for prim, world_pose, frame_visibility in zip(self.xform_prims, frame_poses, frame_visibilities):
                parent_transforms = np.array(
                    [UsdGeom.Xformable(get_prim_parent(prim)).ComputeLocalToWorldTransform(Usd.TimeCode.Default())]
                )
                translations, orientations = get_local_from_world(
                    parent_transforms, np.array([world_pose[0]]), np.array([world_pose[1]])
                )

                properties = prim.GetPropertyNames()
                translation = Gf.Vec3d(*translations[0].tolist())
                if "xformOp:translate" in properties:
                    xform_op = prim.GetAttribute("xformOp:translate")
                    xform_op.Set(translation)

                if "xformOp:orient" in properties:
                    xform_op = prim.GetAttribute("xformOp:orient")
                    if xform_op.GetTypeName() == "quatf":
                        rotq = Gf.Quatf(*orientations[0].tolist())
                    else:
                        rotq = Gf.Quatd(*orientations[0].tolist())
                    xform_op.Set(rotq)

                if frame_visibility == UsdGeom.Tokens.invisible:
                    prim.GetAttribute("visibility").Set("invisible")
                else:
                    prim.GetAttribute("visibility").Set("inherited")

            self.world.render()
            if increment_counter:
                self.replay_counter += 1
            return False
        else:
            print("Replay complete")
            return True

    def _apply_recorded_states(self):
        """Apply recorded robot joint positions, object world poses, and visibilities for the current step."""
        step = self.replay_counter

        for robot_name, robot in self.robots.items():
            joint_positions = self.robot_joint_data[robot_name][step]
            robot.set_joint_positions(positions=joint_positions)

        for obj_name, obj in self.objs.items():
            state = self.object_state_data[obj_name][step]
            obj.set_world_pose(state["translation"], state["orientation"])

            if "joint_positions" in state and state["joint_positions"] is not None:
                obj.set_joint_positions(state["joint_positions"])

        frame_visibilities = self.prim_visibilities[step]
        for prim, frame_visibility in zip(self.xform_prims, frame_visibilities):
            if frame_visibility == UsdGeom.Tokens.invisible:
                prim.GetAttribute("visibility").Set("invisible")
            else:
                prim.GetAttribute("visibility").Set("inherited")

    def dumps(self):
        """Serialize recorder data based on mode."""
        if self.step_replay:
            record_data = {
                "mode": "joint_position",
                "num_steps": self.num_steps,
                "robot_joint_data": self.robot_joint_data,
                "object_state_data": self.object_state_data,
                "prim_visibilities": self.prim_visibilities,
            }
        else:
            record_data = {
                "mode": "prim_pose",
                "num_steps": self.num_steps,
                "prim_poses": self.prim_poses,
                "prim_visibilities": self.prim_visibilities,
            }

        return pickle.dumps(record_data)

    def loads(self, data):
        """Deserialize recorder data based on mode."""
        record_data = pickle.loads(data)
        mode = record_data.get("mode", "prim_pose")

        if mode == "prim_pose" and not self.step_replay:
            self.num_steps = record_data["num_steps"]
            self.prim_poses = record_data["prim_poses"]
            self.prim_visibilities = record_data["prim_visibilities"]
        elif mode == "joint_position" and self.step_replay:
            self.num_steps = record_data["num_steps"]
            self.robot_joint_data = record_data["robot_joint_data"]
            self.object_state_data = record_data["object_state_data"]
            self.prim_visibilities = record_data["prim_visibilities"]
        else:
            mode_name = "prim_pose" if not self.step_replay else "joint_position"
            raise ValueError(f"Mode mismatch: data is '{mode}', recorder is '{mode_name}'")

        return record_data

    def reset(self):
        self.num_steps = 0
        self.replay_counter = 0
        self.prim_poses = []
        self.prim_visibilities = []
        if self.step_replay:
            self.robot_joint_data = {name: [] for name in self.robots}
            self.object_state_data = {name: [] for name in self.objs}
        print("WorldRecorder reset")
