"""Validate headset and grip targets and apply them to a USD avatar."""
import math

from pxr import Gf, UsdGeom

AVATAR = "/World/Avatar"
REST_POSE = {
    "head": {"position": [0, 0, 1.66], "orientation_xyzw": [0, 0, 0, 1]},
    "left": {"position": [.343, -.105, .949], "orientation_xyzw": [0, 0, 0, 1]},
    "right": {"position": [-.343, -.105, .949], "orientation_xyzw": [0, 0, 0, 1]},
}


def vector(values, length):
    if not isinstance(values, list) or len(values) != length or not all(
        type(value) in (int, float) and abs(value) <= 1000 for value in values
    ):
        raise ValueError(f"Expected {length} finite numeric values of magnitude at most 1000")
    return values


def decode_pose(packet):
    if not isinstance(packet, dict):
        raise ValueError("Expected a JSON object")
    result = {}
    for name in REST_POSE:
        target = packet.get(name)
        if not isinstance(target, dict):
            raise ValueError(f"Missing target {name}")
        position = Gf.Vec3d(*vector(target.get("position"), 3))
        x, y, z, w = vector(target.get("orientation_xyzw"), 4)
        magnitude = math.hypot(x, y, z, w)
        if magnitude < 1e-8:
            raise ValueError(f"Invalid quaternion for {name}")
        result[name] = (position, Gf.Quatd(w, Gf.Vec3d(x, y, z)).GetNormalized())
    return result


def apply_pose(stage, packet):
    decoded = decode_pose(packet)

    def set_transform(name, position, orientation=None, length=None):
        transform = UsdGeom.Xformable(stage.GetPrimAtPath(f"{AVATAR}/{name}"))
        ops = {op.GetOpName(): op for op in transform.GetOrderedXformOps()}
        ops["xformOp:translate"].Set(position)
        if orientation is not None:
            ops["xformOp:orient"].Set(orientation)
        if length is not None:
            ops["xformOp:scale"].Set(Gf.Vec3f(1, 1, length))

    set_transform("Head", *decoded["head"])
    for key, sign in [("left", 1), ("right", -1)]:
        label = key.title()
        shoulder = Gf.Vec3d(sign * .218, 0, 1.36)
        hand_target, orientation = decoded[key]
        offset = hand_target - shoulder
        direction = offset.GetNormalized() if offset.GetLength() > 1e-8 else Gf.Vec3d(0, 0, -1)
        upper, lower = .25, .24
        distance = min(max(offset.GetLength(), abs(upper-lower) + .001), upper+lower - .001)
        along = (upper**2 - lower**2 + distance**2) / (2 * distance)
        pole = Gf.Vec3d(sign, .5, 0)
        perpendicular = Gf.Cross(direction, Gf.Cross(pole, direction))
        if perpendicular.GetLength() < 1e-8:
            perpendicular = Gf.Cross(direction, Gf.Vec3d(0, 0, 1))
        elbow = shoulder + direction * along + perpendicular.GetNormalized() * math.sqrt(upper**2 - along**2)
        hand = shoulder + direction * distance
        set_transform(f"{label}Hand", hand, orientation)
        set_transform(f"{label}Elbow", elbow)
        for name, start, end in [("UpperArm", shoulder, elbow), ("Forearm", elbow, hand)]:
            axis = end - start
            rotation = Gf.Rotation(Gf.Vec3d(0, 0, 1), axis.GetNormalized()).GetQuat()
            set_transform(f"{label}{name}", (start + end) * .5, rotation, axis.GetLength())
