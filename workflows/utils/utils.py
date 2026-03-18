from omni.isaac.core.utils.prims import get_prim_at_path
from pxr import UsdPhysics


def get_all_joints(robot_prim, joint_dict):
    for child in robot_prim.GetChildren():
        if child.IsA(UsdPhysics.Joint):
            joint_dict[child.GetName()] = UsdPhysics.Joint(child)
        else:
            get_all_joints(child, joint_dict)
    return joint_dict


def get_link(robot_prim):
    joint_dict = {}
    joint_dict = get_all_joints(robot_prim, joint_dict)
    # print(self.joint_dict)
    link_dict = {}
    for value in joint_dict.values():
        body0_rel = value.GetBody0Rel()
        body0_path = body0_rel.GetTargets()
        if len(body0_path) > 0:
            body0_prim = get_prim_at_path(str(body0_path[0]))
            if body0_prim.IsValid():
                link_dict[str(body0_prim.GetPath())] = body0_prim
        body1_rel = value.GetBody1Rel()
        body1_path = body1_rel.GetTargets()
        if len(body1_path) > 0:
            body1_prim = get_prim_at_path(str(body1_path[0]))
            if body1_prim.IsValid():
                link_dict[str(body1_prim.GetPath())] = body1_prim
    return link_dict
