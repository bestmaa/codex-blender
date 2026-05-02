bl_info = {
    "name": "Codex Blender Bridge",
    "author": "Aditya",
    "version": (0, 13, 0),
    "blender": (3, 6, 0),
    "location": "View3D > Sidebar > Codex",
    "description": "Local HTTP bridge for sending Codex commands to Blender.",
    "category": "3D View",
}

import contextlib
import io
import json
import math
import os
import queue
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import bpy
from mathutils import Vector


HOST = "127.0.0.1"
PORT = 8765
DEFAULT_COMMAND_TIMEOUT = 300
DEFAULT_SOURCE_PATH = r"\\wsl.localhost\Ubuntu\home\aditya\projects\codex-blender\blender_addon\codex_blender_addon.py"

_server = None
_server_thread = None
_command_queue = queue.Queue()


class CommandJob:
    def __init__(self, payload):
        self.payload = payload
        self.event = threading.Event()
        self.result = None


def make_result(ok, **values):
    data = {"ok": ok}
    data.update(values)
    return data


def get_addon_preferences():
    addon = bpy.context.preferences.addons.get(__name__)
    return addon.preferences if addon else None


def get_reload_source_path():
    preferences = get_addon_preferences()
    if preferences and preferences.source_path:
        return preferences.source_path
    if DEFAULT_SOURCE_PATH and Path(DEFAULT_SOURCE_PATH).exists():
        return DEFAULT_SOURCE_PATH
    return __file__


def reload_bridge_code(source_path):
    path = Path(source_path)
    if not path.exists():
        raise FileNotFoundError(f"Reload source not found: {source_path}")

    was_running = is_bridge_running()
    stop_bridge()
    source = path.read_text(encoding="utf-8")
    exec(compile(source, os.fspath(path), "exec"), globals(), globals())
    if was_running:
        start_bridge()
    return path


def clear_scene():
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete()


def create_cube(name, location, scale, material):
    bpy.ops.mesh.primitive_cube_add(size=1, location=location)
    obj = bpy.context.object
    obj.name = name
    obj.dimensions = scale
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    if material:
        obj.data.materials.append(material)
    return obj


def create_rounded_cube(name, location, scale, material, bevel_width=0.04, bevel_segments=4):
    obj = create_cube(name, location, scale, material)
    if bevel_width > 0:
        bevel = obj.modifiers.new("soft rounded edges", "BEVEL")
        bevel.width = bevel_width
        bevel.segments = bevel_segments
        obj.modifiers.new("weighted normals", "WEIGHTED_NORMAL")
    return obj


def create_material(name, color, roughness=0.55, metallic=0.0, emission=None, strength=0.0):
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes.get("Principled BSDF")
    if bsdf:
        bsdf.inputs["Base Color"].default_value = color
        bsdf.inputs["Roughness"].default_value = roughness
        bsdf.inputs["Metallic"].default_value = metallic
        if emission and "Emission Color" in bsdf.inputs:
            bsdf.inputs["Emission Color"].default_value = emission
            bsdf.inputs["Emission Strength"].default_value = strength
    return mat


def create_image_material(name, image, opacity=1.0, unlit=True):
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    mat.blend_method = "BLEND" if opacity < 1.0 else "OPAQUE"
    mat.show_transparent_back = True
    nodes = mat.node_tree.nodes
    bsdf = nodes.get("Principled BSDF")
    texture = nodes.new(type="ShaderNodeTexImage")
    texture.image = image
    if bsdf:
        mat.node_tree.links.new(texture.outputs["Color"], bsdf.inputs["Base Color"])
        if "Alpha" in bsdf.inputs:
            bsdf.inputs["Alpha"].default_value = opacity
            mat.node_tree.links.new(texture.outputs["Alpha"], bsdf.inputs["Alpha"])
        if "Roughness" in bsdf.inputs:
            bsdf.inputs["Roughness"].default_value = 0.8
        if unlit and "Emission Color" in bsdf.inputs:
            mat.node_tree.links.new(texture.outputs["Color"], bsdf.inputs["Emission Color"])
        if unlit and "Emission Strength" in bsdf.inputs:
            bsdf.inputs["Emission Strength"].default_value = 0.6
    return mat


def create_texture_material(
    name,
    image,
    roughness=0.55,
    metallic=0.0,
    opacity=1.0,
    texture_scale=(1.0, 1.0),
    texture_offset=(0.0, 0.0),
    texture_rotation=0.0,
    projection="uv",
):
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    mat.blend_method = "BLEND" if opacity < 1.0 else "OPAQUE"
    nodes = mat.node_tree.nodes
    bsdf = nodes.get("Principled BSDF")
    coords = nodes.new(type="ShaderNodeTexCoord")
    mapping = nodes.new(type="ShaderNodeMapping")
    texture = nodes.new(type="ShaderNodeTexImage")
    texture.image = image
    coordinate_output = {
        "uv": "UV",
        "generated": "Generated",
        "object": "Object",
    }[projection]
    mat.node_tree.links.new(coords.outputs[coordinate_output], mapping.inputs["Vector"])
    mapping.inputs["Scale"].default_value[0] = texture_scale[0]
    mapping.inputs["Scale"].default_value[1] = texture_scale[1]
    mapping.inputs["Location"].default_value[0] = texture_offset[0]
    mapping.inputs["Location"].default_value[1] = texture_offset[1]
    mapping.inputs["Rotation"].default_value[2] = texture_rotation
    mat.node_tree.links.new(mapping.outputs["Vector"], texture.inputs["Vector"])
    if bsdf:
        mat.node_tree.links.new(texture.outputs["Color"], bsdf.inputs["Base Color"])
        if "Alpha" in bsdf.inputs:
            bsdf.inputs["Alpha"].default_value = opacity
            mat.node_tree.links.new(texture.outputs["Alpha"], bsdf.inputs["Alpha"])
        if "Roughness" in bsdf.inputs:
            bsdf.inputs["Roughness"].default_value = roughness
        if "Metallic" in bsdf.inputs:
            bsdf.inputs["Metallic"].default_value = metallic
    return mat


def add_area_light(name, location, rotation, power, size):
    bpy.ops.object.light_add(type="AREA", location=location, rotation=rotation)
    light = bpy.context.object
    light.name = name
    light.data.energy = power
    light.data.size = size
    return light


def look_at(obj, target):
    direction = Vector(target) - obj.location
    obj.rotation_euler = direction.to_track_quat("-Z", "Y").to_euler()


def get_number(params, name, default, minimum=None, maximum=None):
    value = params.get(name, default)
    if not isinstance(value, (int, float)):
        raise ValueError(f"params.{name} must be a number")
    if minimum is not None and value < minimum:
        raise ValueError(f"params.{name} must be >= {minimum}")
    if maximum is not None and value > maximum:
        raise ValueError(f"params.{name} must be <= {maximum}")
    return value


def get_int(params, name, default, minimum=None, maximum=None):
    value = get_number(params, name, default, minimum, maximum)
    if int(value) != value:
        raise ValueError(f"params.{name} must be an integer")
    return int(value)


def action_create_room(params):
    clear_scene()

    wall_mat = create_material("warm white wall", (0.78, 0.76, 0.70, 1.0), roughness=0.8)
    floor_mat = create_material("dark wood floor", (0.18, 0.12, 0.08, 1.0), roughness=0.62)
    sofa_mat = create_material("deep teal fabric", (0.02, 0.26, 0.30, 1.0), roughness=0.9)
    table_mat = create_material("matte black metal", (0.02, 0.02, 0.025, 1.0), roughness=0.48, metallic=0.5)
    neon_mat = create_material(
        "cyan neon",
        (0.0, 0.8, 1.0, 1.0),
        emission=(0.0, 0.8, 1.0, 1.0),
        strength=3.0,
    )

    create_cube("floor", (0, 0, -0.05), (7.5, 6.0, 0.1), floor_mat)
    create_cube("back wall", (0, 3.0, 1.5), (7.5, 0.12, 3.1), wall_mat)
    create_cube("left wall", (-3.75, 0, 1.5), (0.12, 6.0, 3.1), wall_mat)
    create_cube("right wall", (3.75, 0, 1.5), (0.12, 6.0, 3.1), wall_mat)

    create_cube("low sofa base", (-1.35, 1.6, 0.35), (2.8, 0.85, 0.45), sofa_mat)
    create_cube("sofa back", (-1.35, 2.0, 0.85), (2.9, 0.25, 1.0), sofa_mat)
    create_cube("coffee table top", (1.25, 1.1, 0.45), (1.7, 0.75, 0.12), table_mat)
    create_cube("coffee table leg 1", (0.55, 0.82, 0.22), (0.08, 0.08, 0.42), table_mat)
    create_cube("coffee table leg 2", (1.95, 0.82, 0.22), (0.08, 0.08, 0.42), table_mat)
    create_cube("coffee table leg 3", (0.55, 1.38, 0.22), (0.08, 0.08, 0.42), table_mat)
    create_cube("coffee table leg 4", (1.95, 1.38, 0.22), (0.08, 0.08, 0.42), table_mat)
    create_cube("neon wall strip", (0, 2.93, 2.2), (4.4, 0.04, 0.08), neon_mat)

    add_area_light("large softbox", (0, -1.2, 3.6), (1.1, 0.0, 0.0), 450, 4.0)
    add_area_light("cyan accent", (2.8, 2.4, 1.8), (1.2, 0.0, -0.7), 180, 1.4)

    bpy.ops.object.camera_add(location=(4.6, -4.5, 2.2), rotation=(1.18, 0.0, 0.78))
    bpy.context.scene.camera = bpy.context.object
    bpy.context.scene.render.engine = "CYCLES"
    bpy.context.scene.cycles.samples = 64
    bpy.context.scene.frame_set(1)

    return make_result(True, message="Created starter room scene.", style=params.get("style", "modern_neon"))


def create_cylinder(name, location, radius, depth, material, vertices=24):
    bpy.ops.mesh.primitive_cylinder_add(vertices=vertices, radius=radius, depth=depth, location=location)
    obj = bpy.context.object
    obj.name = name
    if material:
        obj.data.materials.append(material)
    return obj


def create_cone(name, location, radius1, radius2, depth, material, vertices=24):
    bpy.ops.mesh.primitive_cone_add(
        vertices=vertices,
        radius1=radius1,
        radius2=radius2,
        depth=depth,
        location=location,
    )
    obj = bpy.context.object
    obj.name = name
    if material:
        obj.data.materials.append(material)
    return obj


def create_table_leg(name, x, y, height, top_radius, bottom_radius, material, angle=5.0):
    bpy.ops.mesh.primitive_cone_add(
        vertices=4,
        radius1=bottom_radius,
        radius2=top_radius,
        depth=height,
        location=(x, y, height / 2),
        rotation=(0, 0, math.radians(45)),
    )
    obj = bpy.context.object
    obj.name = name
    obj.rotation_euler[0] = math.radians(angle if x > 0 else -angle)
    obj.rotation_euler[1] = math.radians(-angle if y > 0 else angle)
    if material:
        obj.data.materials.append(material)
    bevel = obj.modifiers.new("slightly softened leg edges", "BEVEL")
    bevel.width = 0.018
    bevel.segments = 2
    obj.modifiers.new("weighted normals", "WEIGHTED_NORMAL")
    return obj


def action_create_table_model(params):
    clear_scene()

    length = get_number(params, "length", 3.6, minimum=0.8, maximum=12)
    width = get_number(params, "width", 2.0, minimum=0.5, maximum=8)
    height = get_number(params, "height", 1.55, minimum=0.5, maximum=4)
    top_thickness = get_number(params, "top_thickness", 0.24, minimum=0.06, maximum=0.8)
    corner_roundness = get_number(params, "corner_roundness", 0.14, minimum=0, maximum=0.5)
    include_grain = params.get("include_grain", True)
    if not isinstance(include_grain, bool):
        raise ValueError("params.include_grain must be a boolean")
    style = params.get("style", "modern_wood")
    if not isinstance(style, str):
        raise ValueError("params.style must be a string")

    wood_color = params.get("wood_color", [0.78, 0.47, 0.25, 1])
    if not isinstance(wood_color, list) or len(wood_color) not in {3, 4}:
        raise ValueError("params.wood_color must be [r, g, b] or [r, g, b, a]")
    if len(wood_color) == 3:
        wood_color = wood_color + [1]
    if not all(isinstance(value, (int, float)) for value in wood_color):
        raise ValueError("params.wood_color must contain only numbers")

    wood_mat = create_material("warm natural wood", tuple(wood_color), roughness=0.42)
    dark_wood_mat = create_material(
        "dark end grain",
        (wood_color[0] * 0.52, wood_color[1] * 0.48, wood_color[2] * 0.45, 1),
        roughness=0.58,
    )
    grain_mat = create_material("subtle wood grain lines", (0.30, 0.16, 0.08, 1), roughness=0.78)
    floor_mat = create_material("matte studio floor", (0.78, 0.76, 0.71, 1), roughness=0.65)
    shadow_mat = create_material("soft contact shadow base", (0.38, 0.34, 0.30, 1), roughness=0.8)

    create_rounded_cube("studio floor", (0, 0, -0.035), (length + 2.8, width + 2.7, 0.07), floor_mat, 0.02, 2)
    create_rounded_cube("soft shadow pad", (0, 0, 0.01), (length + 0.4, width + 0.45, 0.018), shadow_mat, 0.10, 8)

    top_z = height
    create_rounded_cube(
        "rounded rectangular tabletop",
        (0, 0, top_z),
        (length, width, top_thickness),
        wood_mat,
        corner_roundness,
        10,
    )
    underside_z = top_z - top_thickness * 0.72
    create_rounded_cube(
        "darker tabletop underside",
        (0, 0, underside_z),
        (length * 0.92, width * 0.86, top_thickness * 0.55),
        dark_wood_mat,
        min(corner_roundness * 0.45, 0.08),
        5,
    )

    leg_height = max(0.2, height - top_thickness * 0.58)
    leg_x = length * 0.38
    leg_y = width * 0.34
    top_radius = min(length, width) * 0.055
    bottom_radius = top_radius * 1.45
    for leg_name, x, y in [
        ("front left tapered leg", -leg_x, -leg_y),
        ("front right tapered leg", leg_x, -leg_y),
        ("back left tapered leg", -leg_x, leg_y),
        ("back right tapered leg", leg_x, leg_y),
    ]:
        create_table_leg(leg_name, x, y, leg_height, top_radius, bottom_radius, dark_wood_mat)

    apron_z = leg_height + top_thickness * 0.15
    apron_depth = min(0.25, top_thickness * 1.05)
    create_rounded_cube("front apron", (0, -width * 0.46, apron_z), (length * 0.84, 0.11, apron_depth), dark_wood_mat, 0.035, 4)
    create_rounded_cube("back apron", (0, width * 0.46, apron_z), (length * 0.84, 0.11, apron_depth), dark_wood_mat, 0.035, 4)
    create_rounded_cube("left side apron", (-length * 0.45, 0, apron_z), (0.11, width * 0.74, apron_depth), dark_wood_mat, 0.035, 4)
    create_rounded_cube("right side apron", (length * 0.45, 0, apron_z), (0.11, width * 0.74, apron_depth), dark_wood_mat, 0.035, 4)

    if include_grain:
        grain_count = max(4, min(14, int(width * 5)))
        for index in range(grain_count):
            y = -width * 0.38 + (width * 0.76 / max(1, grain_count - 1)) * index
            create_rounded_cube(
                f"long subtle wood grain {index + 1}",
                (0, y, top_z + top_thickness / 2 + 0.006),
                (length * 0.86, 0.018, 0.012),
                grain_mat,
                0.006,
                2,
            )

    add_area_light("large softbox key", (-length * 0.75, -width * 1.6, height * 2.7), (math.radians(58), 0, math.radians(-28)), 650, 4.0)
    add_area_light("small cool rim light", (length * 0.8, width * 1.1, height * 1.9), (math.radians(70), 0, math.radians(132)), 120, 2.0)
    add_area_light("overhead soft fill", (0, 0, height * 2.8), (0, 0, 0), 180, 5.5)

    bpy.ops.object.camera_add(location=(length * 0.98, -width * 1.58, height * 1.55))
    camera = bpy.context.object
    camera.name = "table product camera"
    look_at(camera, (0, 0, height * 0.70))
    camera.data.lens = 45
    camera.data.dof.use_dof = True
    camera.data.dof.focus_distance = (Vector((0, 0, height * 0.70)) - camera.location).length
    camera.data.dof.aperture_fstop = 8
    bpy.context.scene.camera = camera

    bpy.context.scene.render.engine = "CYCLES"
    bpy.context.scene.cycles.samples = 96
    bpy.context.scene.render.resolution_x = 1280
    bpy.context.scene.render.resolution_y = 720
    bpy.context.scene.world.color = (0.78, 0.80, 0.82)
    bpy.context.scene.view_settings.view_transform = "Filmic"
    bpy.context.scene.view_settings.look = "Medium High Contrast"
    bpy.context.scene.frame_set(1)

    return make_result(
        True,
        message="Created modern table model.",
        style=style,
        length=length,
        width=width,
        height=height,
        include_grain=include_grain,
    )


def add_tree(index, x, y, trunk_mat, leaf_mat, height_offset=0.0):
    trunk_height = 1.0 + height_offset
    create_cylinder(f"tree {index} trunk", (x, y, trunk_height / 2), 0.13, trunk_height, trunk_mat, vertices=14)
    create_cone(f"tree {index} lower canopy", (x, y, trunk_height + 0.55), 0.78, 0.18, 1.15, leaf_mat, vertices=20)
    create_cone(f"tree {index} upper canopy", (x, y, trunk_height + 1.15), 0.55, 0.08, 0.95, leaf_mat, vertices=20)


def add_street_light(index, x, y, pole_mat, lamp_mat):
    pole_height = 3.1
    create_cylinder(f"street light {index} pole", (x, y, pole_height / 2), 0.055, pole_height, pole_mat, vertices=16)
    arm_y = y - 0.28 if y > 0 else y + 0.28
    lamp_y = y - 0.56 if y > 0 else y + 0.56
    create_cube(f"street light {index} arm", (x, arm_y, pole_height), (0.08, 0.62, 0.08), pole_mat)
    create_cube(f"street light {index} lamp", (x, lamp_y, pole_height - 0.05), (0.32, 0.18, 0.12), lamp_mat)
    bpy.ops.object.light_add(type="POINT", location=(x, lamp_y, pole_height - 0.16))
    light = bpy.context.object
    light.name = f"street light {index} glow"
    light.data.energy = 120
    light.data.shadow_soft_size = 1.5
    return light


def action_create_outdoor_scene(params):
    clear_scene()

    road_length = get_number(params, "road_length", 32, minimum=6, maximum=200)
    road_width = get_number(params, "road_width", 5, minimum=2, maximum=30)
    tree_count = get_int(params, "tree_count", 12, minimum=0, maximum=80)
    street_light_count = get_int(params, "street_light_count", 6, minimum=0, maximum=40)
    style = params.get("style", "clean_suburban")
    if not isinstance(style, str):
        raise ValueError("params.style must be a string")

    grass_mat = create_material("soft green grass", (0.12, 0.42, 0.15, 1.0), roughness=0.9)
    asphalt_mat = create_material("dark asphalt", (0.025, 0.027, 0.028, 1.0), roughness=0.78)
    marking_mat = create_material("warm white road marking", (0.95, 0.86, 0.56, 1.0), roughness=0.45)
    curb_mat = create_material("concrete curb", (0.44, 0.42, 0.38, 1.0), roughness=0.8)
    trunk_mat = create_material("tree bark", (0.23, 0.12, 0.055, 1.0), roughness=0.82)
    leaf_mat = create_material("deep green leaves", (0.04, 0.28, 0.08, 1.0), roughness=0.88)
    pole_mat = create_material("painted black metal", (0.015, 0.015, 0.018, 1.0), roughness=0.42, metallic=0.5)
    lamp_mat = create_material(
        "warm lamp glass",
        (1.0, 0.78, 0.34, 1.0),
        emission=(1.0, 0.62, 0.2, 1.0),
        strength=1.8,
    )

    ground_width = max(road_width + 10, 14)
    create_cube("grass ground", (0, 0, -0.06), (road_length + 8, ground_width, 0.12), grass_mat)
    create_cube("main road", (0, 0, 0.01), (road_length, road_width, 0.08), asphalt_mat)
    create_cube("left curb", (0, road_width / 2 + 0.18, 0.09), (road_length, 0.18, 0.16), curb_mat)
    create_cube("right curb", (0, -road_width / 2 - 0.18, 0.09), (road_length, 0.18, 0.16), curb_mat)

    dash_count = max(3, int(road_length // 4))
    dash_spacing = road_length / dash_count
    for index in range(dash_count):
        x = -road_length / 2 + dash_spacing * (index + 0.5)
        create_cube(f"center road dash {index + 1}", (x, 0, 0.075), (dash_spacing * 0.45, 0.08, 0.012), marking_mat)

    if tree_count:
        usable_length = road_length * 0.9
        row_count = max(1, math.ceil(tree_count / 2))
        for index in range(tree_count):
            side = 1 if index % 2 == 0 else -1
            row_index = index // 2
            x = -usable_length / 2 + (usable_length / max(1, row_count - 1)) * row_index
            y = side * (road_width / 2 + 1.8 + (0.35 if row_index % 2 else 0.0))
            add_tree(index + 1, x, y, trunk_mat, leaf_mat, height_offset=(index % 3) * 0.08)

    if street_light_count:
        usable_length = road_length * 0.82
        row_count = max(1, math.ceil(street_light_count / 2))
        for index in range(street_light_count):
            side = 1 if index % 2 == 0 else -1
            row_index = index // 2
            x = -usable_length / 2 + (usable_length / max(1, row_count - 1)) * row_index
            y = side * (road_width / 2 + 0.78)
            add_street_light(index + 1, x, y, pole_mat, lamp_mat)

    bpy.ops.object.light_add(type="SUN", location=(0, -4, 8), rotation=(math.radians(48), 0, math.radians(28)))
    sun = bpy.context.object
    sun.name = "late afternoon sun"
    sun.data.energy = 2.2

    bpy.ops.object.camera_add(
        location=(road_length * 0.32, -road_width * 2.2, 4.2),
        rotation=(math.radians(62), 0.0, math.radians(38)),
    )
    bpy.context.scene.camera = bpy.context.object
    bpy.context.scene.world.color = (0.58, 0.72, 0.88)
    bpy.context.scene.render.engine = "CYCLES"
    bpy.context.scene.cycles.samples = 64
    bpy.context.scene.frame_set(1)

    return make_result(
        True,
        message="Created outdoor road scene.",
        style=style,
        road_length=road_length,
        road_width=road_width,
        tree_count=tree_count,
        street_light_count=street_light_count,
    )


def action_inspect_rig(_params):
    armatures = []
    for obj in bpy.context.scene.objects:
        if obj.type == "ARMATURE":
            armatures.append(
                {
                    "name": obj.name,
                    "bones": [bone.name for bone in obj.data.bones],
                }
            )
    return make_result(True, armatures=armatures)


def resolve_output_path(value):
    output = value or "renders/render.png"
    if not isinstance(output, str):
        raise ValueError("params.output must be a string")

    if output.startswith("//"):
        path = Path(bpy.path.abspath(output))
    else:
        path = Path(output)
        if not path.is_absolute():
            path = Path(__file__).resolve().parents[1] / path

    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def resolve_input_path(value, param_name="path"):
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"params.{param_name} must be a non-empty string")

    if value.startswith("//"):
        path = Path(bpy.path.abspath(value))
    else:
        path = Path(value)
        if not path.is_absolute():
            path = Path(__file__).resolve().parents[1] / path

    if not path.exists():
        raise FileNotFoundError(f"Asset not found: {path}")
    return path


def get_vector(params, name, default, length=3):
    value = params.get(name, default)
    if not isinstance(value, list) or len(value) != length:
        raise ValueError(f"params.{name} must be a list with {length} numbers")
    if not all(isinstance(item, (int, float)) for item in value):
        raise ValueError(f"params.{name} must contain only numbers")
    return tuple(value)


def get_vector2(params, name, default):
    value = params.get(name, default)
    if not isinstance(value, list) or len(value) != 2:
        raise ValueError(f"params.{name} must be a list with 2 numbers")
    if not all(isinstance(item, (int, float)) for item in value):
        raise ValueError(f"params.{name} must contain only numbers")
    return tuple(value)


def set_resolution(params):
    resolution = params.get("resolution", [1280, 720])
    if (
        not isinstance(resolution, list)
        or len(resolution) != 2
        or not all(isinstance(value, int) and value > 0 for value in resolution)
    ):
        raise ValueError("params.resolution must be [width, height] with positive integers")

    bpy.context.scene.render.resolution_x = resolution[0]
    bpy.context.scene.render.resolution_y = resolution[1]
    bpy.context.scene.render.resolution_percentage = 100
    return resolution


def action_render_scene(params):
    if bpy.context.scene.camera is None:
        return make_result(False, error="Scene has no active camera")

    output_path = resolve_output_path(params.get("output"))
    resolution = set_resolution(params)
    samples = params.get("samples")
    if samples is not None:
        if not isinstance(samples, int) or samples <= 0:
            return make_result(False, error="params.samples must be a positive integer")
        if bpy.context.scene.render.engine == "CYCLES":
            bpy.context.scene.cycles.samples = samples

    bpy.context.scene.render.filepath = os.fspath(output_path)
    bpy.context.scene.render.image_settings.file_format = "PNG"
    bpy.ops.render.render(write_still=True)

    return make_result(
        True,
        message="Rendered scene.",
        output=os.fspath(output_path),
        resolution=resolution,
    )


def action_save_blend(params):
    output_path = resolve_output_path(params.get("output") or "scenes/scene.blend")
    if output_path.suffix.lower() != ".blend":
        output_path = output_path.with_suffix(".blend")

    bpy.ops.wm.save_as_mainfile(filepath=os.fspath(output_path))
    return make_result(True, message="Saved Blender scene.", output=os.fspath(output_path))


def set_import_transform(objects, location, rotation, scale):
    for obj in objects:
        obj.location = location
        obj.rotation_euler = rotation
        obj.scale = scale


def import_obj(path):
    if hasattr(bpy.ops.wm, "obj_import"):
        bpy.ops.wm.obj_import(filepath=os.fspath(path))
    else:
        bpy.ops.import_scene.obj(filepath=os.fspath(path))


def action_import_asset(params):
    path = resolve_input_path(params.get("path"))
    location = get_vector(params, "location", [0, 0, 0])
    rotation = get_vector(params, "rotation", [0, 0, 0])
    scale_value = params.get("scale", 1.0)
    if isinstance(scale_value, (int, float)):
        scale = (scale_value, scale_value, scale_value)
    else:
        scale = get_vector(params, "scale", [1, 1, 1])

    before = set(bpy.data.objects)
    suffix = path.suffix.lower()
    if suffix in {".glb", ".gltf"}:
        bpy.ops.import_scene.gltf(filepath=os.fspath(path))
    elif suffix == ".fbx":
        bpy.ops.import_scene.fbx(filepath=os.fspath(path))
    elif suffix == ".obj":
        import_obj(path)
    else:
        return make_result(False, error=f"Unsupported asset type: {suffix}")

    imported = [obj for obj in bpy.data.objects if obj not in before]
    set_import_transform(imported, location, rotation, scale)
    for obj in imported:
        obj.select_set(True)
    if imported:
        bpy.context.view_layer.objects.active = imported[0]

    return make_result(
        True,
        message="Imported asset.",
        path=os.fspath(path),
        objects=[obj.name for obj in imported],
    )


def action_add_reference_image(params):
    path = resolve_input_path(params.get("path"))
    name = params.get("name", path.stem)
    if not isinstance(name, str) or not name.strip():
        raise ValueError("params.name must be a non-empty string")

    location = get_vector(params, "location", [0, 2.2, 1.4])
    rotation = get_vector(params, "rotation", [math.radians(90), 0, 0])
    width = get_number(params, "width", 3.0, minimum=0.1, maximum=100)
    opacity = get_number(params, "opacity", 1.0, minimum=0.05, maximum=1.0)
    unlit = params.get("unlit", True)
    if not isinstance(unlit, bool):
        raise ValueError("params.unlit must be a boolean")

    image = bpy.data.images.load(os.fspath(path), check_existing=True)
    image_width, image_height = image.size
    aspect = image_height / image_width if image_width else 1.0
    height = params.get("height")
    if height is None:
        height = width * aspect
    elif not isinstance(height, (int, float)) or height <= 0:
        raise ValueError("params.height must be a positive number")

    bpy.ops.mesh.primitive_plane_add(size=1, location=location, rotation=rotation)
    plane = bpy.context.object
    plane.name = name
    plane.dimensions = (width, height, 1)
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    plane.data.materials.append(create_image_material(f"{name} material", image, opacity=opacity, unlit=unlit))

    return make_result(
        True,
        message="Added reference image plane.",
        path=os.fspath(path),
        object=plane.name,
        width=width,
        height=height,
        opacity=opacity,
    )


def action_apply_texture_material(params):
    path = resolve_input_path(params.get("path"))
    object_name = params.get("object")
    if not isinstance(object_name, str) or not object_name.strip():
        raise ValueError("params.object must be a non-empty string")

    obj = bpy.data.objects.get(object_name)
    if obj is None:
        raise ValueError(f"Object not found: {object_name}")
    if not hasattr(obj.data, "materials"):
        raise ValueError(f"Object does not support materials: {object_name}")

    material_name = params.get("material_name") or f"{object_name} texture material"
    if not isinstance(material_name, str) or not material_name.strip():
        raise ValueError("params.material_name must be a non-empty string")

    roughness = get_number(params, "roughness", 0.55, minimum=0, maximum=1)
    metallic = get_number(params, "metallic", 0.0, minimum=0, maximum=1)
    opacity = get_number(params, "opacity", 1.0, minimum=0.05, maximum=1)
    texture_scale = get_vector2(params, "texture_scale", [1.0, 1.0])
    texture_offset = get_vector2(params, "texture_offset", [0.0, 0.0])
    texture_rotation = get_number(params, "texture_rotation", 0.0)
    projection = params.get("projection", "uv")
    if projection not in {"uv", "generated", "object"}:
        raise ValueError("params.projection must be 'uv', 'generated', or 'object'")
    mode = params.get("mode", "replace")
    if mode not in {"replace", "append"}:
        raise ValueError("params.mode must be 'replace' or 'append'")

    image = bpy.data.images.load(os.fspath(path), check_existing=True)
    material = create_texture_material(
        material_name,
        image,
        roughness=roughness,
        metallic=metallic,
        opacity=opacity,
        texture_scale=texture_scale,
        texture_offset=texture_offset,
        texture_rotation=texture_rotation,
        projection=projection,
    )
    if mode == "replace":
        obj.data.materials.clear()
    obj.data.materials.append(material)

    return make_result(
        True,
        message="Applied texture material.",
        object=obj.name,
        material=material.name,
        path=os.fspath(path),
        mode=mode,
        texture_scale=texture_scale,
        texture_offset=texture_offset,
        texture_rotation=texture_rotation,
        projection=projection,
    )


def material_from_plan(cache, name, color):
    key = name or json.dumps(color)
    if key not in cache:
        if not isinstance(color, list) or len(color) not in {3, 4}:
            color = [0.7, 0.7, 0.7, 1.0]
        if len(color) == 3:
            color = color + [1.0]
        cache[key] = create_material(name or "reference material", tuple(color), roughness=0.72)
    return cache[key]


def create_reference_primitive(item, material):
    shape = item.get("shape", "cube")
    name = item.get("name", shape)
    location = get_vector(item, "location", [0, 0, 0])
    rotation = get_vector(item, "rotation", [0, 0, 0])
    scale = get_vector(item, "scale", [1, 1, 1])

    if shape == "cube":
        obj = create_cube(name, location, scale, material)
    elif shape == "cylinder":
        radius = get_number(item, "radius", 0.5, minimum=0.01)
        depth = get_number(item, "depth", 1.0, minimum=0.01)
        obj = create_cylinder(name, location, radius, depth, material, vertices=32)
    elif shape == "cone":
        radius1 = get_number(item, "radius1", 0.5, minimum=0.0)
        radius2 = get_number(item, "radius2", 0.0, minimum=0.0)
        depth = get_number(item, "depth", 1.0, minimum=0.01)
        obj = create_cone(name, location, radius1, radius2, depth, material, vertices=32)
    elif shape == "sphere":
        bpy.ops.mesh.primitive_uv_sphere_add(segments=32, ring_count=16, radius=1, location=location)
        obj = bpy.context.object
        obj.name = name
        obj.scale = scale
        obj.data.materials.append(material)
    else:
        raise ValueError(f"Unsupported reference shape: {shape}")

    obj.rotation_euler = rotation
    return obj


def action_create_scene_from_reference(params):
    clear_scene()

    title = params.get("title", "reference scene")
    if not isinstance(title, str):
        raise ValueError("params.title must be a string")

    materials = {}
    floor_mat = material_from_plan(materials, "reference floor", params.get("floor_color", [0.45, 0.43, 0.38, 1]))
    floor_size = get_vector(params, "floor_size", [8, 6, 0.08])
    create_cube("reference floor", (0, 0, -0.04), floor_size, floor_mat)

    objects = params.get("objects", [])
    if not isinstance(objects, list):
        raise ValueError("params.objects must be a list")

    created = []
    for index, item in enumerate(objects):
        if not isinstance(item, dict):
            raise ValueError("each object in params.objects must be an object")
        material = material_from_plan(
            materials,
            item.get("material", f"reference material {index + 1}"),
            item.get("color", [0.7, 0.7, 0.7, 1]),
        )
        created.append(create_reference_primitive(item, material).name)

    bpy.ops.object.light_add(type="AREA", location=(0, -3.2, 4.0), rotation=(math.radians(62), 0, 0))
    key = bpy.context.object
    key.name = "reference soft key light"
    key.data.energy = get_number(params, "key_light_energy", 420, minimum=0)
    key.data.size = 4.5

    bpy.ops.object.light_add(type="SUN", location=(0, 0, 6), rotation=(math.radians(45), 0, math.radians(35)))
    sun = bpy.context.object
    sun.name = "reference sun light"
    sun.data.energy = get_number(params, "sun_energy", 1.4, minimum=0)

    camera_location = get_vector(params, "camera_location", [5.0, -5.0, 3.0])
    camera_rotation = get_vector(params, "camera_rotation", [math.radians(60), 0, math.radians(42)])
    bpy.ops.object.camera_add(location=camera_location, rotation=camera_rotation)
    bpy.context.scene.camera = bpy.context.object
    bpy.context.scene.world.color = tuple(params.get("world_color", [0.05, 0.055, 0.065]))
    bpy.context.scene.render.engine = "CYCLES"
    bpy.context.scene.cycles.samples = 64
    bpy.context.scene.frame_set(1)

    return make_result(True, message="Created scene from reference plan.", title=title, objects=created)


def action_run_python(params):
    code = params.get("code", "")
    if not isinstance(code, str) or not code.strip():
        return make_result(False, error="params.code must be a non-empty string")

    namespace = {"bpy": bpy, "Vector": Vector}
    output = io.StringIO()
    with contextlib.redirect_stdout(output):
        exec(code, namespace, namespace)
    return make_result(True, stdout=output.getvalue())


def execute_command(payload):
    action = payload.get("action")
    params = payload.get("params") or {}

    if action == "ping":
        return make_result(True, message="Blender bridge is running.")
    if action == "create_room":
        return action_create_room(params)
    if action == "create_outdoor_scene":
        return action_create_outdoor_scene(params)
    if action == "create_table_model":
        return action_create_table_model(params)
    if action == "inspect_rig":
        return action_inspect_rig(params)
    if action == "render_scene":
        return action_render_scene(params)
    if action == "save_blend":
        return action_save_blend(params)
    if action == "import_asset":
        return action_import_asset(params)
    if action == "add_reference_image":
        return action_add_reference_image(params)
    if action == "apply_texture_material":
        return action_apply_texture_material(params)
    if action == "create_scene_from_reference":
        return action_create_scene_from_reference(params)
    if action == "run_python":
        return action_run_python(params)
    return make_result(False, error=f"Unsupported action: {action}")


def process_queued_commands():
    while True:
        try:
            job = _command_queue.get_nowait()
        except queue.Empty:
            break

        try:
            job.result = execute_command(job.payload)
        except Exception as exc:
            job.result = make_result(False, error=str(exc), errorType=type(exc).__name__)
        finally:
            job.event.set()

    return 0.1 if is_bridge_running() else None


class CodexRequestHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path != "/health":
            self.send_json(404, make_result(False, error="Not found"))
            return
        self.send_json(200, make_result(True, message="Codex Blender Bridge is healthy."))

    def do_POST(self):
        if self.path != "/command":
            self.send_json(404, make_result(False, error="Not found"))
            return

        try:
            length = int(self.headers.get("Content-Length", "0"))
            payload = json.loads(self.rfile.read(length).decode("utf-8"))
        except Exception as exc:
            self.send_json(400, make_result(False, error=f"Invalid request: {exc}"))
            return

        job = CommandJob(payload)
        _command_queue.put(job)
        timeout = payload.get("params", {}).get("timeout_seconds", DEFAULT_COMMAND_TIMEOUT)
        if not isinstance(timeout, (int, float)) or timeout <= 0:
            timeout = DEFAULT_COMMAND_TIMEOUT
        if not job.event.wait(timeout=timeout):
            self.send_json(504, make_result(False, error="Timed out waiting for Blender."))
            return

        self.send_json(200, job.result)

    def send_json(self, status, payload):
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, _format, *_args):
        return


def is_bridge_running():
    return _server is not None


def start_bridge():
    global _server, _server_thread

    if is_bridge_running():
        return

    _server = ThreadingHTTPServer((HOST, PORT), CodexRequestHandler)
    _server_thread = threading.Thread(target=_server.serve_forever, daemon=True)
    _server_thread.start()
    bpy.app.timers.register(process_queued_commands, persistent=True)


def stop_bridge():
    global _server, _server_thread

    if _server is None:
        return

    _server.shutdown()
    _server.server_close()
    _server = None
    _server_thread = None


class CODEXBLENDER_OT_start_bridge(bpy.types.Operator):
    bl_idname = "codex_blender.start_bridge"
    bl_label = "Start Bridge"

    def execute(self, _context):
        start_bridge()
        self.report({"INFO"}, f"Codex bridge running on http://{HOST}:{PORT}")
        return {"FINISHED"}


class CODEXBLENDER_OT_stop_bridge(bpy.types.Operator):
    bl_idname = "codex_blender.stop_bridge"
    bl_label = "Stop Bridge"

    def execute(self, _context):
        stop_bridge()
        self.report({"INFO"}, "Codex bridge stopped")
        return {"FINISHED"}


class CODEXBLENDER_OT_reload_bridge_code(bpy.types.Operator):
    bl_idname = "codex_blender.reload_bridge_code"
    bl_label = "Reload Bridge Code"

    def execute(self, _context):
        try:
            path = reload_bridge_code(get_reload_source_path())
        except Exception as exc:
            self.report({"ERROR"}, str(exc))
            return {"CANCELLED"}

        self.report({"INFO"}, f"Reloaded bridge code from {path}")
        return {"FINISHED"}


class CODEXBLENDER_AddonPreferences(bpy.types.AddonPreferences):
    bl_idname = __name__

    developer_mode: bpy.props.BoolProperty(
        name="Developer Mode",
        description="Show add-on development controls such as bridge code reload",
        default=False,
    )

    source_path: bpy.props.StringProperty(
        name="Source File",
        description="Development source file to reload without reinstalling the add-on",
        default=DEFAULT_SOURCE_PATH,
        subtype="FILE_PATH",
    )

    def draw(self, _context):
        layout = self.layout
        layout.prop(self, "developer_mode")
        if self.developer_mode:
            layout.prop(self, "source_path")


class CODEXBLENDER_PT_panel(bpy.types.Panel):
    bl_label = "Codex Blender"
    bl_idname = "CODEXBLENDER_PT_panel"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Codex"

    def draw(self, _context):
        layout = self.layout
        status = "Running" if is_bridge_running() else "Stopped"
        layout.label(text=f"Bridge: {status}")
        layout.label(text=f"{HOST}:{PORT}")
        row = layout.row(align=True)
        row.operator("codex_blender.start_bridge")
        row.operator("codex_blender.stop_bridge")
        preferences = get_addon_preferences()
        if preferences and preferences.developer_mode:
            layout.separator()
            layout.prop(preferences, "source_path")
            layout.operator("codex_blender.reload_bridge_code")


CLASSES = (
    CODEXBLENDER_AddonPreferences,
    CODEXBLENDER_OT_start_bridge,
    CODEXBLENDER_OT_stop_bridge,
    CODEXBLENDER_OT_reload_bridge_code,
    CODEXBLENDER_PT_panel,
)


def register():
    for cls in CLASSES:
        bpy.utils.register_class(cls)


def unregister():
    stop_bridge()
    for cls in reversed(CLASSES):
        bpy.utils.unregister_class(cls)


if __name__ == "__main__":
    register()
