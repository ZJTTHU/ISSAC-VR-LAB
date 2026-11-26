"""Import the Isaac Sim stage and render it with Blender Cycles on CPU."""
import argparse
from pathlib import Path
import sys

import bpy
from mathutils import Vector

ROOT = Path(__file__).resolve().parent


def aim(obj, target):
    obj.rotation_euler = (Vector(target) - obj.location).to_track_quat("-Z", "Y").to_euler()


def light(name, location, power, color, size, target):
    data = bpy.data.lights.new(name, "AREA")
    data.energy = power
    data.color = color
    data.shape = "DISK"
    data.size = size
    obj = bpy.data.objects.new(name, data)
    bpy.context.collection.objects.link(obj)
    obj.location = location
    aim(obj, target)


def render(source, output, samples, scale):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    if not source.is_file():
        raise FileNotFoundError(source)
    if "FINISHED" not in bpy.ops.wm.usd_import(filepath=str(source)):
        raise RuntimeError(f"Unable to import {source}")
    if not any(obj.type == "MESH" and obj.name.startswith("Helmet") for obj in bpy.context.scene.objects):
        raise RuntimeError("Imported USD stage is missing the avatar")
    bpy.ops.object.camera_add(location=(2.65, -4.60, 2.58))
    camera = bpy.context.object
    camera.data.lens = 42
    aim(camera, (0, .39, .98))
    scene = bpy.context.scene
    scene.camera = camera
    light("Key", (-2.5, -2, 4.6), 780, (.78, .91, 1), 3, (0, 0, 1))
    light("Fill", (2.9, -2.6, 2.4), 350, (1, .69, .48), 2.6, (0, 0, .9))
    light("Rim", (.4, 1.5, 3.45), 930, (.29, .82, 1), 2.1, (0, 0, 1))
    scene.world = bpy.data.worlds.new("Lab ambient")
    scene.world.use_nodes = True
    scene.world.node_tree.nodes["Background"].inputs["Color"].default_value = (.14, .19, .26, 1)
    scene.world.node_tree.nodes["Background"].inputs["Strength"].default_value = .25
    scene.render.engine = "CYCLES"
    scene.cycles.device = "CPU"
    scene.cycles.samples = samples
    scene.cycles.use_denoising = True
    scene.render.resolution_x = 1100
    scene.render.resolution_y = 820
    scene.render.resolution_percentage = scale
    scene.render.image_settings.file_format = "PNG"
    scene.render.filepath = str(output)
    output.parent.mkdir(parents=True, exist_ok=True)
    bpy.ops.render.render(write_still=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, default=ROOT / "lab.usda")
    parser.add_argument("--output", type=Path, default=ROOT / "renders" / "lab.png")
    parser.add_argument("--samples", type=int, default=24)
    parser.add_argument("--scale", type=int, default=100)
    args = parser.parse_args(sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else [])
    render(args.source.resolve(), args.output.resolve(), args.samples, args.scale)
