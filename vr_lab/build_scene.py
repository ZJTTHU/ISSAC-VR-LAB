"""Generate the lab and avatar as a portable USD stage."""
import argparse
import math
from pathlib import Path

from pxr import Gf, Sdf, Usd, UsdGeom, UsdPhysics, UsdShade

ROOT = Path(__file__).resolve().parent


def make_material(stage, name, color, metallic=0.0):
    path = f"/World/Materials/{name}"
    material = UsdShade.Material.Define(stage, path)
    shader = UsdShade.Shader.Define(stage, f"{path}/Surface")
    shader.CreateIdAttr("UsdPreviewSurface")
    shader.CreateInput("diffuseColor", Sdf.ValueTypeNames.Color3f).Set(Gf.Vec3f(*color))
    shader.CreateInput("roughness", Sdf.ValueTypeNames.Float).Set(0.35)
    shader.CreateInput("metallic", Sdf.ValueTypeNames.Float).Set(metallic)
    surface = shader.CreateOutput("surface", Sdf.ValueTypeNames.Token)
    material.CreateSurfaceOutput().ConnectToSource(surface)
    return material


def box_geometry():
    points = [(x, y, z) for z in (-1, 1) for x, y in
              [(-1, -1), (1, -1), (1, 1), (-1, 1)]]
    return points, [(3, 2, 1, 0), (4, 5, 6, 7), (0, 1, 5, 4),
                    (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7)]


def sphere_geometry():
    sides, rings = 16, 8
    points = [(0, 0, 1)]
    for ring in range(1, rings):
        phi = math.pi * ring / rings
        for side in range(sides):
            theta = math.tau * side / sides
            points.append((math.sin(phi) * math.cos(theta),
                           math.sin(phi) * math.sin(theta), math.cos(phi)))
    points.append((0, 0, -1))
    faces = []
    for side in range(sides):
        following = (side + 1) % sides
        faces.append((0, 1 + side, 1 + following))
        for ring in range(rings - 2):
            start = 1 + ring * sides
            faces.append((start + side, start + sides + side,
                          start + sides + following, start + following))
        start = 1 + (rings - 2) * sides
        faces.append((len(points) - 1, start + following, start + side))
    return points, faces


def build(output):
    stage = Usd.Stage.CreateInMemory("lab.usda")
    world = UsdGeom.Xform.Define(stage, "/World")
    stage.SetDefaultPrim(world.GetPrim())
    UsdGeom.SetStageUpAxis(stage, UsdGeom.Tokens.z)
    UsdGeom.SetStageMetersPerUnit(stage, 1.0)
    physics = UsdPhysics.Scene.Define(stage, "/World/Physics")
    physics.CreateGravityDirectionAttr(Gf.Vec3f(0, 0, -1))
    physics.CreateGravityMagnitudeAttr(9.81)
    materials = {
        "navy": make_material(stage, "Navy", (.038, .083, .13), .25),
        "panel": make_material(stage, "Panel", (.12, .19, .25), .1),
        "ivory": make_material(stage, "Ivory", (.72, .79, .78), .22),
        "cyan": make_material(stage, "Cyan", (.02, .57, .63), .22),
        "amber": make_material(stage, "Amber", (.92, .34, .08), .1),
        "rubber": make_material(stage, "Rubber", (.025, .04, .055)),
    }
    geometries = {"box": box_geometry(), "round": sphere_geometry()}

    def frame(path, position=(0, 0, 0)):
        transform = UsdGeom.Xform.Define(stage, path)
        transform.AddTranslateOp().Set(Gf.Vec3d(*position))
        transform.AddOrientOp(UsdGeom.XformOp.PrecisionDouble).Set(Gf.Quatd(1))
        return path

    def part(parent, name, position, size, material, shape="box"):
        points, faces = geometries[shape]
        mesh = UsdGeom.Mesh.Define(stage, f"{parent}/{name}")
        mesh.CreatePointsAttr([Gf.Vec3f(*(v * s for v, s in zip(point, size)))
                               for point in points])
        mesh.CreateFaceVertexCountsAttr([len(face) for face in faces])
        mesh.CreateFaceVertexIndicesAttr([vertex for face in faces for vertex in face])
        mesh.CreateSubdivisionSchemeAttr(UsdGeom.Tokens.none)
        mesh.CreateExtentAttr([Gf.Vec3f(*(-v for v in size)), Gf.Vec3f(*size)])
        mesh.AddTranslateOp().Set(Gf.Vec3d(*position))
        UsdShade.MaterialBindingAPI.Apply(mesh.GetPrim()).Bind(materials[material])
        return mesh.GetPrim()

    lab = frame("/World/Lab")
    floor = part(lab, "Floor", (0, 0, -.07), (3.4, 2.9, .07), "navy")
    UsdPhysics.CollisionAPI.Apply(floor)
    for i in range(-4, 5):
        for j in range(-3, 4):
            part(lab, f"Tile_{i+4}_{j+3}", (.72*i, .72*j, .001),
                 (.351, .351, .008), "panel")
    part(lab, "BackWall", (0, 2.55, 1.27), (3.4, .07, 1.27), "navy")
    part(lab, "SideWall", (-3.32, .45, 1.27), (.07, 2.05, 1.27), "navy")
    for i in range(7):
        x = .87 * (i-3)
        part(lab, f"WallPanel_{i}", (x, 2.45, 1.34), (.41, .035, .94), "panel")
        part(lab, f"WallLight_{i}", (x, 2.40, 2.14), (.32, .025, .021), "cyan")
    for x, label in [(-1, "Left"), (1, "Right")]:
        part(lab, f"Guide{label}", (x, -.1, .013), (.025, 1.65, .009), "cyan")
        part(lab, f"Bench{label}", (x*1.9, 1.63, .48), (.53, .31, .47), "navy")
        part(lab, f"BenchTop{label}", (x*1.9, 1.63, .98), (.57, .35, .035), "ivory")
        part(lab, f"Monitor{label}", (x*1.9, 1.75, 1.24), (.35, .07, .19), "rubber")
        part(lab, f"Display{label}", (x*1.9, 1.67, 1.24), (.29, .01, .13), "cyan")

    avatar = frame("/World/Avatar")
    part(avatar, "Pelvis", (0, 0, .95), (.19, .11, .14), "navy", "round")
    part(avatar, "Torso", (0, 0, 1.23), (.245, .135, .275), "ivory", "round")
    part(avatar, "Chest", (0, -.13, 1.31), (.127, .025, .064), "cyan", "round")
    part(avatar, "Neck", (0, 0, 1.49), (.065, .061, .084), "rubber", "round")
    head = frame(f"{avatar}/Head", (0, 0, 1.66))
    part(head, "Helmet", (0, 0, 0), (.143, .133, .166), "ivory", "round")
    part(head, "Visor", (0, -.102, .023), (.128, .055, .073), "rubber", "round")
    for sign, label in [(1, "Left"), (-1, "Right")]:
        part(head, f"Eye{label}", (sign*.051, -.152, .027), (.031, .012, .018), "cyan", "round")
        part(avatar, f"Thigh{label}", (sign*.121, 0, .75), (.089, .088, .208), "ivory", "round")
        part(avatar, f"Knee{label}", (sign*.131, -.012, .55), (.076, .082, .075), "amber", "round")
        part(avatar, f"Shin{label}", (sign*.133, 0, .33), (.076, .081, .203), "ivory", "round")
        part(avatar, f"Foot{label}", (sign*.136, -.063, .11), (.092, .173, .077), "navy", "round")
        grip = frame(f"{avatar}/{label}Hand", (sign*.343, -.105, .949))
        part(grip, "Glove", (0, 0, 0), (.062, .066, .083), "navy", "round")
        part(grip, "Pad", (0, -.056, .018), (.038, .016, .042), "cyan", "round")
        part(avatar, f"Shoulder{label}", (sign*.218, 0, 1.36), (.096, .097, .092), "amber", "round")
        frame(f"{avatar}/{label}Elbow")
        part(f"{avatar}/{label}Elbow", "Joint", (0, 0, 0), (.055, .055, .055), "rubber", "round")
        for segment, material in [("UpperArm", "ivory"), ("Forearm", "ivory")]:
            path = frame(f"{avatar}/{label}{segment}")
            UsdGeom.Xformable(stage.GetPrimAtPath(path)).AddScaleOp().Set(Gf.Vec3f(1))
            part(path, "Shell", (0, 0, 0), (.067, .071, .5), material, "round")

    from pose import apply_pose, REST_POSE
    apply_pose(stage, REST_POSE)
    output.write_text(stage.GetRootLayer().ExportToString().rstrip() + "\n", encoding="utf-8")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("output", nargs="?", type=Path, default=ROOT / "lab.usda")
    output = parser.parse_args().output.resolve()
    if output.suffix != ".usda":
        parser.error("output must use the .usda extension")
    build(output)
