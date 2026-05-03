bl_info = {
    "name": "Codex Blender Bridge",
    "author": "Aditya",
    "version": (0, 94, 0),
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


def get_project_root():
    source_path = Path(get_reload_source_path())
    if source_path.name == "codex_blender_addon.py" and source_path.parent.name == "blender_addon":
        return source_path.parent.parent
    return source_path.parent


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
    roughness_image=None,
    normal_image=None,
    metallic_image=None,
    alpha_image=None,
):
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    mat.blend_method = "BLEND" if opacity < 1.0 else "OPAQUE"
    nodes = mat.node_tree.nodes
    bsdf = nodes.get("Principled BSDF")
    coords = nodes.new(type="ShaderNodeTexCoord")
    mapping = nodes.new(type="ShaderNodeMapping")
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

    def add_texture_node(texture_image, color_space="sRGB"):
        texture = nodes.new(type="ShaderNodeTexImage")
        texture.image = texture_image
        texture.image.colorspace_settings.name = color_space
        mat.node_tree.links.new(mapping.outputs["Vector"], texture.inputs["Vector"])
        return texture

    texture = add_texture_node(image)
    if bsdf:
        mat.node_tree.links.new(texture.outputs["Color"], bsdf.inputs["Base Color"])
        if alpha_image is not None and "Alpha" in bsdf.inputs:
            alpha_texture = add_texture_node(alpha_image, color_space="Non-Color")
            mat.node_tree.links.new(alpha_texture.outputs["Color"], bsdf.inputs["Alpha"])
        elif "Alpha" in bsdf.inputs:
            bsdf.inputs["Alpha"].default_value = opacity
            mat.node_tree.links.new(texture.outputs["Alpha"], bsdf.inputs["Alpha"])
        if "Roughness" in bsdf.inputs:
            bsdf.inputs["Roughness"].default_value = roughness
            if roughness_image is not None:
                roughness_texture = add_texture_node(roughness_image, color_space="Non-Color")
                mat.node_tree.links.new(roughness_texture.outputs["Color"], bsdf.inputs["Roughness"])
        if "Metallic" in bsdf.inputs:
            bsdf.inputs["Metallic"].default_value = metallic
            if metallic_image is not None:
                metallic_texture = add_texture_node(metallic_image, color_space="Non-Color")
                mat.node_tree.links.new(metallic_texture.outputs["Color"], bsdf.inputs["Metallic"])
        if normal_image is not None and "Normal" in bsdf.inputs:
            normal_texture = add_texture_node(normal_image, color_space="Non-Color")
            normal_map = nodes.new(type="ShaderNodeNormalMap")
            mat.node_tree.links.new(normal_texture.outputs["Color"], normal_map.inputs["Color"])
            mat.node_tree.links.new(normal_map.outputs["Normal"], bsdf.inputs["Normal"])
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


def action_create_chair_model(params):
    clear_scene()

    width = get_number(params, "width", 1.35, minimum=0.4, maximum=5)
    depth = get_number(params, "depth", 1.25, minimum=0.4, maximum=5)
    height = get_number(params, "height", 2.25, minimum=0.8, maximum=6)
    seat_height = get_number(params, "seat_height", 0.95, minimum=0.25, maximum=3)
    cushion_thickness = get_number(params, "cushion_thickness", 0.18, minimum=0.05, maximum=0.6)
    style = params.get("style", "modern_wood")
    if not isinstance(style, str):
        raise ValueError("params.style must be a string")

    wood_color = params.get("wood_color", [0.72, 0.45, 0.25, 1])
    if not isinstance(wood_color, list) or len(wood_color) not in {3, 4}:
        raise ValueError("params.wood_color must be [r, g, b] or [r, g, b, a]")
    if len(wood_color) == 3:
        wood_color = wood_color + [1]

    fabric_color = params.get("fabric_color", [0.34, 0.48, 0.56, 1])
    if not isinstance(fabric_color, list) or len(fabric_color) not in {3, 4}:
        raise ValueError("params.fabric_color must be [r, g, b] or [r, g, b, a]")
    if len(fabric_color) == 3:
        fabric_color = fabric_color + [1]

    wood_mat = create_material("chair warm wood", tuple(wood_color), roughness=0.48)
    dark_wood_mat = create_material("chair dark wood", (wood_color[0] * 0.55, wood_color[1] * 0.52, wood_color[2] * 0.48, 1), roughness=0.58)
    fabric_mat = create_material("chair soft fabric", tuple(fabric_color), roughness=0.88)
    floor_mat = create_material("chair studio floor", (0.78, 0.76, 0.71, 1), roughness=0.65)

    create_rounded_cube("chair studio floor", (0, 0, -0.035), (width + 3.0, depth + 3.0, 0.07), floor_mat, 0.02, 2)
    create_rounded_cube("chair seat cushion", (0, 0, seat_height), (width, depth, cushion_thickness), fabric_mat, 0.09, 7)
    create_rounded_cube("chair front apron", (0, -depth * 0.48, seat_height - 0.18), (width * 0.92, 0.10, 0.22), dark_wood_mat, 0.03, 3)
    create_rounded_cube("chair back apron", (0, depth * 0.48, seat_height - 0.18), (width * 0.92, 0.10, 0.22), dark_wood_mat, 0.03, 3)
    create_rounded_cube("chair back cushion", (0, depth * 0.48, height * 0.72), (width, 0.18, height * 0.46), fabric_mat, 0.08, 7)
    create_rounded_cube("chair top rail", (0, depth * 0.56, height), (width * 1.05, 0.16, 0.16), wood_mat, 0.06, 5)

    leg_height = seat_height - cushion_thickness * 0.35
    leg_x = width * 0.38
    leg_y = depth * 0.36
    radius = min(width, depth) * 0.055
    for leg_name, x, y in [
        ("chair front left leg", -leg_x, -leg_y),
        ("chair front right leg", leg_x, -leg_y),
        ("chair back left leg", -leg_x, leg_y),
        ("chair back right leg", leg_x, leg_y),
    ]:
        create_table_leg(leg_name, x, y, leg_height, radius * 0.72, radius, wood_mat, angle=3.5)

    for support_name, x in [("chair left back post", -leg_x, ), ("chair right back post", leg_x)]:
        create_rounded_cube(support_name, (x, depth * 0.56, height * 0.64), (0.12, 0.12, height * 0.72), wood_mat, 0.035, 4)

    add_area_light("chair large softbox", (-2.4, -2.8, 3.8), (math.radians(58), 0, math.radians(-28)), 520, 3.8)
    add_area_light("chair cool rim", (2.2, 1.8, 2.6), (math.radians(70), 0, math.radians(132)), 100, 1.8)

    bpy.ops.object.camera_add(location=(3.25, -4.85, 2.35))
    camera = bpy.context.object
    camera.name = "chair product camera"
    look_at(camera, (0, 0.04, seat_height * 1.08))
    camera.data.lens = 32
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
        message="Created modern chair model.",
        style=style,
        width=width,
        depth=depth,
        height=height,
        seat_height=seat_height,
    )


def action_create_sofa_model(params):
    clear_scene()

    width = get_number(params, "width", 3.2, minimum=1.0, maximum=8)
    depth = get_number(params, "depth", 1.35, minimum=0.6, maximum=4)
    height = get_number(params, "height", 1.55, minimum=0.7, maximum=4)
    seat_height = get_number(params, "seat_height", 0.62, minimum=0.25, maximum=2)
    cushion_count = get_int(params, "cushion_count", 3, minimum=1, maximum=6)
    cushion_gap = get_number(params, "cushion_gap", 0.035, minimum=0, maximum=0.2)
    style = params.get("style", "modern_couch")
    if not isinstance(style, str):
        raise ValueError("params.style must be a string")

    fabric_color = params.get("fabric_color", [0.42, 0.54, 0.62, 1])
    if not isinstance(fabric_color, list) or len(fabric_color) not in {3, 4}:
        raise ValueError("params.fabric_color must be [r, g, b] or [r, g, b, a]")
    if len(fabric_color) == 3:
        fabric_color = fabric_color + [1]

    leg_color = params.get("leg_color", [0.42, 0.25, 0.14, 1])
    if not isinstance(leg_color, list) or len(leg_color) not in {3, 4}:
        raise ValueError("params.leg_color must be [r, g, b] or [r, g, b, a]")
    if len(leg_color) == 3:
        leg_color = leg_color + [1]

    fabric_mat = create_material("sofa soft fabric", tuple(fabric_color), roughness=0.9)
    seam_mat = create_material(
        "sofa darker fabric seams",
        (fabric_color[0] * 0.62, fabric_color[1] * 0.62, fabric_color[2] * 0.62, 1),
        roughness=0.94,
    )
    leg_mat = create_material("sofa tapered wood legs", tuple(leg_color), roughness=0.55)
    floor_mat = create_material("sofa studio floor", (0.78, 0.76, 0.71, 1), roughness=0.65)
    shadow_mat = create_material("sofa soft shadow pad", (0.36, 0.34, 0.31, 1), roughness=0.84)

    create_rounded_cube("sofa studio floor", (0, 0, -0.035), (width + 3.2, depth + 3.2, 0.07), floor_mat, 0.02, 2)
    create_rounded_cube("sofa contact shadow pad", (0, 0, 0.012), (width + 0.55, depth + 0.5, 0.02), shadow_mat, 0.12, 8)

    base_height = 0.24
    create_rounded_cube("sofa base platform", (0, 0, seat_height - base_height * 0.55), (width, depth * 0.9, base_height), fabric_mat, 0.10, 8)

    usable_width = width - cushion_gap * (cushion_count - 1)
    cushion_width = usable_width / cushion_count
    seat_depth = depth * 0.72
    seat_z = seat_height + 0.08
    start_x = -width / 2 + cushion_width / 2
    for index in range(cushion_count):
        x = start_x + index * (cushion_width + cushion_gap)
        create_rounded_cube(
            f"sofa seat cushion {index + 1}",
            (x, -depth * 0.12, seat_z),
            (cushion_width, seat_depth, 0.24),
            fabric_mat,
            0.12,
            9,
        )
        if index > 0:
            seam_x = x - cushion_width / 2 - cushion_gap / 2
            create_rounded_cube(
                f"sofa seat cushion seam {index}",
                (seam_x, -depth * 0.12, seat_z + 0.13),
                (0.018, seat_depth * 0.88, 0.018),
                seam_mat,
                0.006,
                2,
            )

    back_height = height - seat_height + 0.08
    create_rounded_cube(
        "sofa back cushion",
        (0, depth * 0.38, seat_height + back_height * 0.48),
        (width, 0.22, back_height),
        fabric_mat,
        0.12,
        9,
    )
    create_rounded_cube(
        "sofa left arm",
        (-width * 0.53, -depth * 0.04, seat_height + 0.28),
        (0.28, depth * 0.96, 0.72),
        fabric_mat,
        0.10,
        8,
    )
    create_rounded_cube(
        "sofa right arm",
        (width * 0.53, -depth * 0.04, seat_height + 0.28),
        (0.28, depth * 0.96, 0.72),
        fabric_mat,
        0.10,
        8,
    )

    pillow_width = min(0.58, width / max(cushion_count, 2) * 0.62)
    for index, x in enumerate((-width * 0.28, width * 0.28), start=1):
        create_rounded_cube(
            f"sofa loose pillow {index}",
            (x, depth * 0.18, seat_height + 0.46),
            (pillow_width, 0.14, 0.46),
            fabric_mat,
            0.10,
            8,
        )

    leg_height = seat_height - base_height * 1.1
    leg_x = width * 0.40
    leg_y = depth * 0.33
    radius = min(width, depth) * 0.035
    for leg_name, x, y in [
        ("sofa front left leg", -leg_x, -leg_y),
        ("sofa front right leg", leg_x, -leg_y),
        ("sofa back left leg", -leg_x, leg_y),
        ("sofa back right leg", leg_x, leg_y),
    ]:
        create_table_leg(leg_name, x, y, leg_height, radius * 0.75, radius, leg_mat, angle=4)

    add_area_light("sofa large softbox", (-width * 0.55, -depth * 2.0, height * 2.35), (math.radians(58), 0, math.radians(-28)), 620, 4.4)
    add_area_light("sofa warm rim light", (width * 0.55, depth * 1.55, height * 1.65), (math.radians(70), 0, math.radians(132)), 130, 2.2)
    add_area_light("sofa overhead fill", (0, 0, height * 2.55), (0, 0, 0), 140, 5.8)

    bpy.ops.object.camera_add(location=(width * 0.95, -depth * 3.3, height * 1.65))
    camera = bpy.context.object
    camera.name = "sofa product camera"
    look_at(camera, (0, -depth * 0.04, seat_height * 0.95))
    camera.data.lens = 35
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
        message="Created modern sofa model.",
        style=style,
        width=width,
        depth=depth,
        height=height,
        cushion_count=cushion_count,
    )


def create_leaf(name, location, scale, rotation, material):
    bpy.ops.mesh.primitive_uv_sphere_add(segments=24, ring_count=12, location=location, rotation=rotation)
    obj = bpy.context.object
    obj.name = name
    obj.scale = scale
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    if material:
        obj.data.materials.append(material)
    obj.modifiers.new("leaf smooth normals", "WEIGHTED_NORMAL")
    return obj


def action_create_plant_model(params):
    clear_scene()

    height = get_number(params, "height", 2.1, minimum=0.5, maximum=6)
    pot_radius = get_number(params, "pot_radius", 0.42, minimum=0.12, maximum=2)
    pot_height = get_number(params, "pot_height", 0.58, minimum=0.18, maximum=2)
    leaf_count = get_int(params, "leaf_count", 18, minimum=4, maximum=80)
    stem_count = get_int(params, "stem_count", 5, minimum=1, maximum=16)
    style = params.get("style", "indoor_potted")
    if not isinstance(style, str):
        raise ValueError("params.style must be a string")

    leaf_color = params.get("leaf_color", [0.20, 0.55, 0.34, 1])
    if not isinstance(leaf_color, list) or len(leaf_color) not in {3, 4}:
        raise ValueError("params.leaf_color must be [r, g, b] or [r, g, b, a]")
    if len(leaf_color) == 3:
        leaf_color = leaf_color + [1]

    pot_color = params.get("pot_color", [0.70, 0.62, 0.52, 1])
    if not isinstance(pot_color, list) or len(pot_color) not in {3, 4}:
        raise ValueError("params.pot_color must be [r, g, b] or [r, g, b, a]")
    if len(pot_color) == 3:
        pot_color = pot_color + [1]

    stem_mat = create_material("plant stems", (0.22, 0.18, 0.10, 1), roughness=0.74)
    leaf_mat = create_material("plant waxy leaves", tuple(leaf_color), roughness=0.62)
    vein_mat = create_material("plant leaf veins", (leaf_color[0] * 0.62, leaf_color[1] * 0.72, leaf_color[2] * 0.62, 1), roughness=0.72)
    pot_mat = create_material("plant ceramic pot", tuple(pot_color), roughness=0.7)
    soil_mat = create_material("plant dark soil", (0.10, 0.075, 0.05, 1), roughness=0.95)
    floor_mat = create_material("plant studio floor", (0.78, 0.76, 0.71, 1), roughness=0.65)

    create_rounded_cube("plant studio floor", (0, 0, -0.035), (pot_radius * 6.4, pot_radius * 6.4, 0.07), floor_mat, 0.02, 2)
    create_cylinder("plant ceramic pot", (0, 0, pot_height / 2), pot_radius, pot_height, pot_mat, vertices=48)
    create_cylinder("plant pot rim", (0, 0, pot_height + 0.035), pot_radius * 1.08, 0.07, pot_mat, vertices=48)
    create_cylinder("plant dark soil", (0, 0, pot_height + 0.075), pot_radius * 0.88, 0.035, soil_mat, vertices=48)

    stem_height = max(0.25, height - pot_height * 0.45)
    for index in range(stem_count):
        angle = (math.tau / stem_count) * index
        lean = 0.11 + 0.03 * (index % 3)
        x = math.cos(angle) * lean
        y = math.sin(angle) * lean
        stem = create_cylinder(
            f"plant stem {index + 1}",
            (x * 0.5, y * 0.5, pot_height + stem_height * 0.45),
            pot_radius * 0.035,
            stem_height * (0.78 + 0.05 * (index % 2)),
            stem_mat,
            vertices=12,
        )
        stem.rotation_euler[0] = math.sin(angle) * math.radians(7)
        stem.rotation_euler[1] = -math.cos(angle) * math.radians(7)

    leaf_base_z = pot_height + stem_height * 0.48
    leaf_span = pot_radius * 1.55
    for index in range(leaf_count):
        angle = (math.tau / leaf_count) * index
        layer = index % 4
        radius = leaf_span * (0.42 + 0.11 * layer)
        z = leaf_base_z + stem_height * (0.08 * layer + 0.05 * math.sin(index * 1.7))
        x = math.cos(angle) * radius
        y = math.sin(angle) * radius
        length = pot_radius * (0.42 + 0.055 * (index % 3))
        width = length * 0.34
        rotation = (math.radians(18 + layer * 7), 0, angle)
        create_leaf(
            f"plant broad leaf {index + 1}",
            (x, y, z),
            (length, width, 0.035),
            rotation,
            leaf_mat,
        )
        create_rounded_cube(
            f"plant leaf vein {index + 1}",
            (x, y, z + 0.018),
            (length * 1.35, 0.012, 0.008),
            vein_mat,
            0.004,
            1,
        ).rotation_euler[2] = angle

    add_area_light("plant large softbox", (-2.0, -2.6, height * 1.85), (math.radians(58), 0, math.radians(-28)), 480, 3.5)
    add_area_light("plant green rim", (1.8, 1.6, height * 1.3), (math.radians(70), 0, math.radians(132)), 90, 1.8)

    bpy.ops.object.camera_add(location=(2.3, -3.4, height * 0.95))
    camera = bpy.context.object
    camera.name = "plant product camera"
    look_at(camera, (0, 0, height * 0.52))
    camera.data.lens = 38
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
        message="Created indoor plant model.",
        style=style,
        height=height,
        pot_radius=pot_radius,
        leaf_count=leaf_count,
        stem_count=stem_count,
    )


def action_create_lamp_model(params):
    clear_scene()

    lamp_type = params.get("lamp_type", "floor")
    if not isinstance(lamp_type, str):
        raise ValueError("params.lamp_type must be a string")
    lamp_type = lamp_type.lower()
    if lamp_type not in {"floor", "table", "ceiling_panel"}:
        raise ValueError("params.lamp_type must be floor, table, or ceiling_panel")

    height = get_number(params, "height", 2.4 if lamp_type == "floor" else 1.0, minimum=0.25, maximum=6)
    shade_radius = get_number(params, "shade_radius", 0.38 if lamp_type != "ceiling_panel" else 1.05, minimum=0.08, maximum=3)
    power = get_number(params, "power", 520, minimum=0, maximum=5000)
    style = params.get("style", "warm_modern")
    if not isinstance(style, str):
        raise ValueError("params.style must be a string")

    metal_color = params.get("metal_color", [0.23, 0.23, 0.22, 1])
    if not isinstance(metal_color, list) or len(metal_color) not in {3, 4}:
        raise ValueError("params.metal_color must be [r, g, b] or [r, g, b, a]")
    if len(metal_color) == 3:
        metal_color = metal_color + [1]

    shade_color = params.get("shade_color", [0.95, 0.86, 0.68, 1])
    if not isinstance(shade_color, list) or len(shade_color) not in {3, 4}:
        raise ValueError("params.shade_color must be [r, g, b] or [r, g, b, a]")
    if len(shade_color) == 3:
        shade_color = shade_color + [1]

    metal_mat = create_material("lamp dark metal", tuple(metal_color), roughness=0.34, metallic=0.7)
    shade_mat = create_material("lamp warm shade", tuple(shade_color), roughness=0.72, emission=(1.0, 0.78, 0.42, 1), strength=0.25)
    glow_mat = create_material("lamp visible warm glow", (1.0, 0.72, 0.32, 1), roughness=0.2, emission=(1.0, 0.66, 0.26, 1), strength=2.4)
    floor_mat = create_material("lamp studio floor", (0.78, 0.76, 0.71, 1), roughness=0.65)

    create_rounded_cube("lamp studio floor", (0, 0, -0.035), (4.5, 4.5, 0.07), floor_mat, 0.02, 2)

    if lamp_type == "ceiling_panel":
        create_rounded_cube("ceiling panel body", (0, 0, height), (shade_radius * 2.2, shade_radius * 0.9, 0.10), shade_mat, 0.05, 6)
        create_rounded_cube("ceiling panel diffuser glow", (0, 0, height - 0.06), (shade_radius * 2.0, shade_radius * 0.72, 0.035), glow_mat, 0.04, 5)
        add_area_light("ceiling panel light", (0, 0, height - 0.12), (0, 0, 0), power, shade_radius * 2.0)
        camera_location = (2.5, -3.6, height * 0.72)
        target = (0, 0, height * 0.55)
    else:
        base_radius = shade_radius * (0.55 if lamp_type == "floor" else 0.45)
        pole_height = height * (0.72 if lamp_type == "floor" else 0.62)
        shade_z = pole_height + shade_radius * 0.55
        create_cylinder(f"{lamp_type} lamp round base", (0, 0, 0.045), base_radius, 0.09, metal_mat, vertices=36)
        create_cylinder(f"{lamp_type} lamp slim pole", (0, 0, pole_height / 2), shade_radius * 0.055, pole_height, metal_mat, vertices=18)
        create_cone(f"{lamp_type} lamp shade", (0, 0, shade_z), shade_radius * 0.82, shade_radius * 1.12, shade_radius * 0.72, shade_mat, vertices=40)
        create_cylinder(f"{lamp_type} lamp bulb glow", (0, 0, shade_z - shade_radius * 0.08), shade_radius * 0.22, shade_radius * 0.30, glow_mat, vertices=24)
        bpy.ops.object.light_add(type="POINT", location=(0, 0, shade_z - shade_radius * 0.06))
        light = bpy.context.object
        light.name = f"{lamp_type} lamp warm point light"
        light.data.energy = power
        light.data.shadow_soft_size = shade_radius * 2.2
        add_area_light(f"{lamp_type} lamp soft spill", (-1.2, -1.8, height * 1.25), (math.radians(58), 0, math.radians(-28)), power * 0.35, 2.5)
        camera_location = (2.1, -3.2, height * 0.75)
        target = (0, 0, height * 0.45)

    bpy.ops.object.camera_add(location=camera_location)
    camera = bpy.context.object
    camera.name = "lamp product camera"
    look_at(camera, target)
    camera.data.lens = 42 if lamp_type == "table" else 36
    bpy.context.scene.camera = camera
    bpy.context.scene.render.engine = "CYCLES"
    bpy.context.scene.cycles.samples = 96
    bpy.context.scene.render.resolution_x = 1280
    bpy.context.scene.render.resolution_y = 720
    bpy.context.scene.world.color = (0.12, 0.12, 0.12)
    bpy.context.scene.view_settings.view_transform = "Filmic"
    bpy.context.scene.view_settings.look = "Medium High Contrast"
    bpy.context.scene.frame_set(1)

    return make_result(
        True,
        message="Created lamp model.",
        style=style,
        lamp_type=lamp_type,
        height=height,
        power=power,
    )


def action_create_furniture_set(params):
    clear_scene()

    table_length = get_number(params, "table_length", 3.2, minimum=1.0, maximum=10)
    table_width = get_number(params, "table_width", 1.55, minimum=0.7, maximum=5)
    chair_count = get_int(params, "chair_count", 4, minimum=1, maximum=8)
    include_plant = params.get("include_plant", True)
    include_lamp = params.get("include_lamp", True)
    style = params.get("style", "compact_dining")
    if not isinstance(include_plant, bool):
        raise ValueError("params.include_plant must be a boolean")
    if not isinstance(include_lamp, bool):
        raise ValueError("params.include_lamp must be a boolean")
    if not isinstance(style, str):
        raise ValueError("params.style must be a string")

    wood_mat = create_material("set warm wood", (0.70, 0.43, 0.23, 1), roughness=0.48)
    dark_wood_mat = create_material("set dark wood", (0.30, 0.17, 0.09, 1), roughness=0.58)
    fabric_mat = create_material("set muted fabric", (0.35, 0.49, 0.57, 1), roughness=0.88)
    rug_mat = create_material("set woven rug", (0.62, 0.56, 0.48, 1), roughness=0.92)
    floor_mat = create_material("set studio floor", (0.78, 0.76, 0.71, 1), roughness=0.65)
    plant_mat = create_material("set plant leaves", (0.17, 0.50, 0.29, 1), roughness=0.68)
    pot_mat = create_material("set ceramic planter", (0.70, 0.62, 0.52, 1), roughness=0.72)
    glow_mat = create_material("set lamp warm glow", (1.0, 0.72, 0.32, 1), roughness=0.2, emission=(1.0, 0.66, 0.26, 1), strength=1.8)

    create_rounded_cube("furniture set floor", (0, 0, -0.035), (6.4, 5.4, 0.07), floor_mat, 0.02, 2)
    create_rounded_cube("furniture set rug", (0, 0, 0.012), (table_length + 2.2, table_width + 2.0, 0.025), rug_mat, 0.10, 8)

    table_height = 1.05
    create_rounded_cube("set dining tabletop", (0, 0, table_height), (table_length, table_width, 0.18), wood_mat, 0.09, 8)
    leg_x = table_length * 0.40
    leg_y = table_width * 0.35
    for name, x, y in [
        ("set table front left leg", -leg_x, -leg_y),
        ("set table front right leg", leg_x, -leg_y),
        ("set table back left leg", -leg_x, leg_y),
        ("set table back right leg", leg_x, leg_y),
    ]:
        create_table_leg(name, x, y, table_height - 0.09, 0.045, 0.065, dark_wood_mat, angle=3)

    chair_positions = [
        ("front", 0, -table_width * 1.15),
        ("back", 0, table_width * 1.15),
        ("left", -table_length * 0.62, 0),
        ("right", table_length * 0.62, 0),
        ("front left", -table_length * 0.32, -table_width * 1.15),
        ("front right", table_length * 0.32, -table_width * 1.15),
        ("back left", -table_length * 0.32, table_width * 1.15),
        ("back right", table_length * 0.32, table_width * 1.15),
    ][:chair_count]
    for index, (label, x, y) in enumerate(chair_positions, start=1):
        prefix = f"set chair {index} {label}"
        create_rounded_cube(f"{prefix} seat cushion", (x, y, 0.58), (0.72, 0.62, 0.14), fabric_mat, 0.06, 6)
        back_y = y + (0.34 if y <= 0 else -0.34)
        create_rounded_cube(f"{prefix} back cushion", (x, back_y, 1.02), (0.74, 0.12, 0.62), fabric_mat, 0.06, 6)
        create_rounded_cube(f"{prefix} front apron", (x, y - 0.30, 0.45), (0.68, 0.07, 0.14), dark_wood_mat, 0.025, 3)
        for leg_label, lx, ly in [
            ("front left leg", -0.26, -0.22),
            ("front right leg", 0.26, -0.22),
            ("back left leg", -0.26, 0.22),
            ("back right leg", 0.26, 0.22),
        ]:
            create_table_leg(f"{prefix} {leg_label}", x + lx, y + ly, 0.52, 0.026, 0.038, wood_mat, angle=3)

    if include_plant:
        plant_x = table_length * 0.72
        plant_y = table_width * 1.35
        create_cylinder("set plant pot", (plant_x, plant_y, 0.22), 0.26, 0.44, pot_mat, vertices=36)
        create_cylinder("set plant soil", (plant_x, plant_y, 0.46), 0.22, 0.035, dark_wood_mat, vertices=36)
        for index in range(9):
            angle = math.tau * index / 9
            x = plant_x + math.cos(angle) * 0.28
            y = plant_y + math.sin(angle) * 0.28
            z = 0.82 + 0.12 * (index % 3)
            create_leaf(f"set plant leaf {index + 1}", (x, y, z), (0.22, 0.08, 0.025), (math.radians(18), 0, angle), plant_mat)

    if include_lamp:
        lamp_x = -table_length * 0.82
        lamp_y = table_width * 1.42
        create_cylinder("set floor lamp base", (lamp_x, lamp_y, 0.04), 0.24, 0.08, dark_wood_mat, vertices=36)
        create_cylinder("set floor lamp pole", (lamp_x, lamp_y, 0.98), 0.035, 1.9, dark_wood_mat, vertices=18)
        create_cone("set floor lamp shade", (lamp_x, lamp_y, 1.96), 0.36, 0.50, 0.42, glow_mat, vertices=36)
        bpy.ops.object.light_add(type="POINT", location=(lamp_x, lamp_y, 1.9))
        lamp = bpy.context.object
        lamp.name = "set floor lamp point light"
        lamp.data.energy = 360
        lamp.data.shadow_soft_size = 1.6

    add_area_light("set large window softbox", (-2.4, -3.2, 3.2), (math.radians(58), 0, math.radians(-28)), 540, 4.2)
    add_area_light("set overhead fill", (0, 0, 3.5), (0, 0, 0), 130, 5.5)

    bpy.ops.object.camera_add(location=(4.1, -4.7, 2.65))
    camera = bpy.context.object
    camera.name = "furniture set camera"
    look_at(camera, (0, 0, 0.82))
    camera.data.lens = 31
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
        message="Created furniture set scene.",
        style=style,
        chair_count=chair_count,
        include_plant=include_plant,
        include_lamp=include_lamp,
    )


def action_create_room_layout(params):
    clear_scene()

    preset = params.get("preset", "living_room")
    if not isinstance(preset, str):
        raise ValueError("params.preset must be a string")
    preset = preset.lower()
    if preset not in {"studio", "living_room", "office", "gallery"}:
        raise ValueError("params.preset must be studio, living_room, office, or gallery")
    style = params.get("style", "clean_modern")
    if not isinstance(style, str):
        raise ValueError("params.style must be a string")

    floor_mat = create_material("layout warm floor", (0.72, 0.68, 0.60, 1), roughness=0.7)
    wall_mat = create_material("layout soft white walls", (0.80, 0.82, 0.80, 1), roughness=0.82)
    accent_mat = create_material("layout accent surface", (0.36, 0.48, 0.56, 1), roughness=0.78)
    wood_mat = create_material("layout warm wood", (0.68, 0.42, 0.22, 1), roughness=0.52)
    fabric_mat = create_material("layout soft fabric", (0.42, 0.54, 0.62, 1), roughness=0.88)
    dark_mat = create_material("layout dark metal", (0.16, 0.16, 0.15, 1), roughness=0.35, metallic=0.5)
    glow_mat = create_material("layout warm glow", (1.0, 0.74, 0.34, 1), roughness=0.2, emission=(1.0, 0.66, 0.26, 1), strength=1.5)

    room_width = 5.8 if preset != "gallery" else 7.2
    room_depth = 4.7 if preset != "gallery" else 4.2
    wall_height = 2.9
    create_rounded_cube("layout floor", (0, 0, -0.035), (room_width, room_depth, 0.07), floor_mat, 0.01, 1)
    create_cube("layout back wall", (0, room_depth / 2, wall_height / 2), (room_width, 0.10, wall_height), wall_mat)
    create_cube("layout left wall", (-room_width / 2, 0, wall_height / 2), (0.10, room_depth, wall_height), wall_mat)
    create_cube("layout right wall", (room_width / 2, 0, wall_height / 2), (0.10, room_depth, wall_height), wall_mat)

    if preset == "studio":
        create_rounded_cube("studio murphy bed", (-1.4, 1.45, 0.46), (1.75, 1.15, 0.22), fabric_mat, 0.06, 5)
        create_rounded_cube("studio work table", (1.15, 1.3, 0.78), (1.55, 0.72, 0.12), wood_mat, 0.04, 4)
        create_rounded_cube("studio storage unit", (2.0, -0.35, 0.78), (0.58, 1.15, 1.45), accent_mat, 0.04, 4)
        create_rounded_cube("studio rug", (-0.25, -0.55, 0.015), (3.4, 1.65, 0.025), fabric_mat, 0.08, 6)
        camera_location = (3.6, -3.4, 2.0)
        target = (0.0, 0.55, 0.75)
    elif preset == "office":
        create_rounded_cube("office desk", (0, 1.25, 0.82), (2.3, 0.78, 0.12), wood_mat, 0.04, 4)
        create_rounded_cube("office monitor", (0, 1.58, 1.22), (0.88, 0.06, 0.52), dark_mat, 0.025, 3)
        create_rounded_cube("office chair seat", (0, 0.35, 0.58), (0.74, 0.66, 0.13), fabric_mat, 0.06, 6)
        create_rounded_cube("office chair back", (0, 0.64, 1.02), (0.72, 0.10, 0.62), fabric_mat, 0.06, 6)
        create_rounded_cube("office shelf", (-2.25, 1.25, 1.1), (0.58, 1.05, 1.9), accent_mat, 0.035, 3)
        camera_location = (3.4, -3.2, 2.05)
        target = (0.0, 0.9, 0.95)
    elif preset == "gallery":
        for index, x in enumerate([-2.2, 0.0, 2.2], start=1):
            create_rounded_cube(f"gallery framed artwork {index}", (x, room_depth / 2 - 0.065, 1.55), (1.0, 0.035, 0.78), accent_mat, 0.025, 3)
            create_rounded_cube(f"gallery pedestal {index}", (x, 0.35, 0.48), (0.58, 0.58, 0.9), wall_mat, 0.035, 3)
        create_rounded_cube("gallery bench", (0, -1.35, 0.36), (2.2, 0.42, 0.20), wood_mat, 0.06, 5)
        for x in [-2.2, 0.0, 2.2]:
            add_area_light(f"gallery wall wash {x:.1f}", (x, 1.45, 2.45), (math.radians(78), 0, 0), 50, 0.8)
        camera_location = (3.8, -3.1, 1.8)
        target = (0.0, 0.55, 1.15)
    else:
        create_rounded_cube("living room sofa", (-0.95, 1.25, 0.58), (2.25, 0.82, 0.42), fabric_mat, 0.08, 6)
        create_rounded_cube("living room sofa back", (-0.95, 1.63, 1.0), (2.25, 0.16, 0.72), fabric_mat, 0.08, 6)
        create_rounded_cube("living room coffee table", (0.15, 0.05, 0.42), (1.45, 0.72, 0.10), wood_mat, 0.04, 4)
        create_rounded_cube("living room media unit", (1.85, 1.78, 0.52), (1.2, 0.28, 0.42), dark_mat, 0.035, 3)
        create_rounded_cube("living room rug", (-0.25, 0.2, 0.015), (3.3, 1.85, 0.025), fabric_mat, 0.08, 6)
        create_cylinder("living room floor lamp base", (1.95, -0.95, 0.04), 0.22, 0.08, dark_mat, vertices=32)
        create_cylinder("living room floor lamp pole", (1.95, -0.95, 0.95), 0.032, 1.8, dark_mat, vertices=16)
        create_cone("living room floor lamp shade", (1.95, -0.95, 1.9), 0.34, 0.48, 0.38, glow_mat, vertices=32)
        bpy.ops.object.light_add(type="POINT", location=(1.95, -0.95, 1.85))
        lamp = bpy.context.object
        lamp.name = "living room lamp light"
        lamp.data.energy = 280
        lamp.data.shadow_soft_size = 1.4
        camera_location = (3.6, -3.4, 2.0)
        target = (-0.25, 0.65, 0.85)

    add_area_light("layout large window light", (-room_width * 0.35, -room_depth * 0.65, 2.7), (math.radians(58), 0, math.radians(-28)), 340, 4.0)
    add_area_light("layout ceiling fill", (0, 0, 2.8), (0, 0, 0), 70, 5.2)

    bpy.ops.object.camera_add(location=camera_location)
    camera = bpy.context.object
    camera.name = f"{preset} layout camera"
    look_at(camera, target)
    camera.data.lens = 30
    bpy.context.scene.camera = camera
    bpy.context.scene.render.engine = "CYCLES"
    bpy.context.scene.cycles.samples = 96
    bpy.context.scene.render.resolution_x = 1280
    bpy.context.scene.render.resolution_y = 720
    bpy.context.scene.world.color = (0.78, 0.80, 0.82)
    bpy.context.scene.view_settings.view_transform = "Filmic"
    bpy.context.scene.view_settings.look = "Medium High Contrast"
    bpy.context.scene.frame_set(1)

    return make_result(True, message="Created room layout.", preset=preset, style=style)


def action_list_assets(params):
    asset_type = params.get("type")
    if asset_type is not None and not isinstance(asset_type, str):
        raise ValueError("params.type must be a string")
    extension = params.get("extension")
    if extension is not None and not isinstance(extension, str):
        raise ValueError("params.extension must be a string")

    selected_type = asset_type.lower() if asset_type else None
    selected_extension = extension.lower().lstrip(".") if extension else None
    asset_dirs = {
        "model": get_project_root() / "assets" / "models",
        "texture": get_project_root() / "assets" / "textures",
        "reference": get_project_root() / "assets" / "references",
    }
    assets = []
    for kind, folder in asset_dirs.items():
        if selected_type and selected_type not in {kind, kind + "s"}:
            continue
        if not folder.exists():
            continue
        for path in sorted(folder.iterdir()):
            if not path.is_file():
                continue
            suffix = path.suffix.lower().lstrip(".")
            if selected_extension and suffix != selected_extension:
                continue
            assets.append(
                {
                    "name": path.name,
                    "type": kind,
                    "extension": suffix,
                    "size": path.stat().st_size,
                    "path": path.relative_to(get_project_root()).as_posix(),
                }
            )

    return make_result(True, message="Listed assets.", assets=assets, count=len(assets))


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
            path = get_project_root() / path

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


def set_render_engine(preferred_engines):
    scene = bpy.context.scene
    for engine in preferred_engines:
        try:
            scene.render.engine = engine
            return scene.render.engine
        except TypeError:
            continue
    scene.render.engine = "CYCLES"
    return scene.render.engine


def action_set_render_preset(params):
    preset = params.get("preset", "preview")
    if not isinstance(preset, str):
        raise ValueError("params.preset must be a string")
    preset = preset.lower()
    presets = {
        "draft": {
            "engines": ["BLENDER_EEVEE_NEXT", "BLENDER_EEVEE", "CYCLES"],
            "resolution": [960, 540],
            "samples": 24,
            "look": "Medium High Contrast",
        },
        "preview": {
            "engines": ["CYCLES"],
            "resolution": [1280, 720],
            "samples": 64,
            "look": "Medium High Contrast",
        },
        "final": {
            "engines": ["CYCLES"],
            "resolution": [1920, 1080],
            "samples": 192,
            "look": "High Contrast",
        },
    }
    if preset not in presets:
        raise ValueError("params.preset must be draft, preview, or final")

    config = presets[preset]
    engine = set_render_engine(config["engines"])
    resolution = set_resolution({"resolution": config["resolution"]})
    samples = config["samples"]
    if engine == "CYCLES":
        bpy.context.scene.cycles.samples = samples
    elif hasattr(bpy.context.scene, "eevee"):
        bpy.context.scene.eevee.taa_render_samples = samples
    bpy.context.scene.view_settings.view_transform = "Filmic"
    bpy.context.scene.view_settings.look = config["look"]
    bpy.context.scene.render.film_transparent = False

    return make_result(
        True,
        message="Applied render preset.",
        preset=preset,
        engine=engine,
        resolution=resolution,
        samples=samples,
        view_transform=bpy.context.scene.view_settings.view_transform,
        look=bpy.context.scene.view_settings.look,
    )


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


def action_export_glb(params):
    output_path = resolve_output_path(params.get("output") or "exports/scene.glb")
    if output_path.suffix.lower() != ".glb":
        output_path = output_path.with_suffix(".glb")

    selected_only = params.get("selected_only", False)
    if not isinstance(selected_only, bool):
        raise ValueError("params.selected_only must be a boolean")
    include_materials = params.get("include_materials", True)
    if not isinstance(include_materials, bool):
        raise ValueError("params.include_materials must be a boolean")

    bpy.ops.export_scene.gltf(
        filepath=os.fspath(output_path),
        export_format="GLB",
        use_selection=selected_only,
        export_materials="EXPORT" if include_materials else "NONE",
    )
    return make_result(
        True,
        message="Exported GLB.",
        output=os.fspath(output_path),
        selected_only=selected_only,
        include_materials=include_materials,
    )


def action_export_obj(params):
    output_path = resolve_output_path(params.get("output") or "exports/scene.obj")
    if output_path.suffix.lower() != ".obj":
        output_path = output_path.with_suffix(".obj")

    selected_only = params.get("selected_only", False)
    if not isinstance(selected_only, bool):
        raise ValueError("params.selected_only must be a boolean")

    if hasattr(bpy.ops.wm, "obj_export"):
        bpy.ops.wm.obj_export(filepath=os.fspath(output_path), export_selected_objects=selected_only)
    else:
        bpy.ops.export_scene.obj(filepath=os.fspath(output_path), use_selection=selected_only)

    return make_result(
        True,
        message="Exported OBJ.",
        output=os.fspath(output_path),
        selected_only=selected_only,
    )


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


def action_fit_object_to_bounds(params):
    name = params.get("object")
    if not isinstance(name, str) or not name.strip():
        raise ValueError("params.object must be a non-empty string")
    obj = bpy.data.objects.get(name)
    if obj is None:
        raise ValueError(f"Object not found: {name}")

    target_location = get_vector(params, "target_location", [0, 0, 0])
    target_size_value = params.get("target_size", [1, 1, 1])
    if isinstance(target_size_value, (int, float)):
        if target_size_value <= 0:
            raise ValueError("params.target_size must be positive")
        target_size = (target_size_value, target_size_value, target_size_value)
    else:
        target_size = get_vector(params, "target_size", [1, 1, 1])
        if any(value <= 0 for value in target_size):
            raise ValueError("params.target_size values must be positive")

    align_to_floor = params.get("align_to_floor", True)
    if not isinstance(align_to_floor, bool):
        raise ValueError("params.align_to_floor must be a boolean")

    bpy.context.view_layer.update()
    dimensions = obj.dimensions
    ratios = [
        target / current
        for target, current in zip(target_size, dimensions)
        if current > 0
    ]
    if not ratios:
        raise ValueError(f"Object has no measurable bounds: {name}")
    scale_factor = min(ratios)
    obj.scale = tuple(component * scale_factor for component in obj.scale)
    obj.location = target_location
    bpy.context.view_layer.update()

    if align_to_floor:
        min_z = min((obj.matrix_world @ Vector(corner)).z for corner in obj.bound_box)
        obj.location.z += target_location[2] - min_z
        bpy.context.view_layer.update()

    return make_result(
        True,
        message="Fit object to bounds.",
        object=obj.name,
        target_size=target_size,
        target_location=target_location,
        align_to_floor=align_to_floor,
        dimensions=tuple(round(value, 5) for value in obj.dimensions),
        location=tuple(round(value, 5) for value in obj.location),
    )


def action_inspect_scene(params):
    include_hidden = params.get("include_hidden", False)
    if not isinstance(include_hidden, bool):
        raise ValueError("params.include_hidden must be a boolean")
    object_type = params.get("type")
    if object_type is not None and not isinstance(object_type, str):
        raise ValueError("params.type must be a string")
    selected_type = object_type.upper() if object_type else None

    objects = []
    for obj in bpy.context.scene.objects:
        if not include_hidden and obj.hide_get():
            continue
        if selected_type and obj.type != selected_type:
            continue
        materials = []
        if hasattr(obj.data, "materials"):
            materials = [mat.name for mat in obj.data.materials if mat]
        objects.append(
            {
                "name": obj.name,
                "type": obj.type,
                "location": [round(value, 5) for value in obj.location],
                "rotation": [round(value, 5) for value in obj.rotation_euler],
                "scale": [round(value, 5) for value in obj.scale],
                "dimensions": [round(value, 5) for value in obj.dimensions],
                "materials": materials,
            }
        )

    return make_result(True, message="Inspected scene.", objects=objects, count=len(objects))


def action_transform_object(params):
    name = params.get("object")
    if not isinstance(name, str) or not name.strip():
        raise ValueError("params.object must be a non-empty string")
    obj = bpy.data.objects.get(name)
    if obj is None:
        raise ValueError(f"Object not found: {name}")

    if "location" in params:
        obj.location = get_vector(params, "location", [obj.location.x, obj.location.y, obj.location.z])
    if "rotation" in params:
        obj.rotation_euler = get_vector(params, "rotation", [obj.rotation_euler.x, obj.rotation_euler.y, obj.rotation_euler.z])
    if "scale" in params:
        scale_value = params.get("scale")
        if isinstance(scale_value, (int, float)):
            obj.scale = (scale_value, scale_value, scale_value)
        else:
            obj.scale = get_vector(params, "scale", [obj.scale.x, obj.scale.y, obj.scale.z])
    bpy.context.view_layer.update()
    if "dimensions" in params:
        dimensions = get_vector(params, "dimensions", [obj.dimensions.x, obj.dimensions.y, obj.dimensions.z])
        if any(value <= 0 for value in dimensions):
            raise ValueError("params.dimensions values must be positive")
        obj.dimensions = dimensions
        bpy.context.view_layer.update()

    return make_result(
        True,
        message="Transformed object.",
        object=obj.name,
        location=tuple(round(value, 5) for value in obj.location),
        rotation=tuple(round(value, 5) for value in obj.rotation_euler),
        scale=tuple(round(value, 5) for value in obj.scale),
        dimensions=tuple(round(value, 5) for value in obj.dimensions),
    )


def action_duplicate_object(params):
    name = params.get("object")
    if not isinstance(name, str) or not name.strip():
        raise ValueError("params.object must be a non-empty string")
    source = bpy.data.objects.get(name)
    if source is None:
        raise ValueError(f"Object not found: {name}")
    count = get_int(params, "count", 3, minimum=1, maximum=100)
    offset = get_vector(params, "offset", [1, 0, 0])
    name_prefix = params.get("name_prefix", f"{source.name} copy")
    if not isinstance(name_prefix, str) or not name_prefix.strip():
        raise ValueError("params.name_prefix must be a non-empty string")

    collection = source.users_collection[0] if source.users_collection else bpy.context.collection
    created = []
    for index in range(1, count + 1):
        duplicate = source.copy()
        if source.data:
            duplicate.data = source.data.copy()
        duplicate.name = f"{name_prefix} {index}"
        duplicate.location = (
            source.location.x + offset[0] * index,
            source.location.y + offset[1] * index,
            source.location.z + offset[2] * index,
        )
        collection.objects.link(duplicate)
        created.append(duplicate.name)

    return make_result(
        True,
        message="Duplicated object.",
        source=source.name,
        objects=created,
        count=len(created),
        offset=offset,
    )


def action_animate_object(params):
    name = params.get("object")
    if not isinstance(name, str) or not name.strip():
        raise ValueError("params.object must be a non-empty string")
    obj = bpy.data.objects.get(name)
    if obj is None:
        raise ValueError(f"Object not found: {name}")
    frame_start = get_int(params, "frame_start", 1, minimum=0, maximum=100000)
    frame_end = get_int(params, "frame_end", 80, minimum=0, maximum=100000)
    if frame_end <= frame_start:
        raise ValueError("params.frame_end must be greater than frame_start")

    channels = []
    if "location_start" in params or "location_end" in params:
        start = get_vector(params, "location_start", [obj.location.x, obj.location.y, obj.location.z])
        end = get_vector(params, "location_end", [obj.location.x, obj.location.y, obj.location.z])
        obj.location = start
        obj.keyframe_insert(data_path="location", frame=frame_start)
        obj.location = end
        obj.keyframe_insert(data_path="location", frame=frame_end)
        channels.append("location")
    if "rotation_start" in params or "rotation_end" in params:
        start = get_vector(params, "rotation_start", [obj.rotation_euler.x, obj.rotation_euler.y, obj.rotation_euler.z])
        end = get_vector(params, "rotation_end", [obj.rotation_euler.x, obj.rotation_euler.y, obj.rotation_euler.z])
        obj.rotation_euler = start
        obj.keyframe_insert(data_path="rotation_euler", frame=frame_start)
        obj.rotation_euler = end
        obj.keyframe_insert(data_path="rotation_euler", frame=frame_end)
        channels.append("rotation")
    if "scale_start" in params or "scale_end" in params:
        start = get_vector(params, "scale_start", [obj.scale.x, obj.scale.y, obj.scale.z])
        end = get_vector(params, "scale_end", [obj.scale.x, obj.scale.y, obj.scale.z])
        obj.scale = start
        obj.keyframe_insert(data_path="scale", frame=frame_start)
        obj.scale = end
        obj.keyframe_insert(data_path="scale", frame=frame_end)
        channels.append("scale")
    if not channels:
        raise ValueError("Provide at least one location, rotation, or scale start/end pair")

    bpy.context.scene.frame_start = frame_start
    bpy.context.scene.frame_end = frame_end
    bpy.context.scene.frame_set(frame_start)

    return make_result(
        True,
        message="Animated object.",
        object=obj.name,
        channels=channels,
        frame_start=frame_start,
        frame_end=frame_end,
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
    base_color_value = params.get("base_color_path") or params.get("path")
    path = resolve_input_path(base_color_value, param_name="base_color_path")
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

    optional_images = {}
    for key in ("roughness_path", "normal_path", "metallic_path", "alpha_path"):
        value = params.get(key)
        if value is not None:
            optional_path = resolve_input_path(value, param_name=key)
            optional_images[key] = bpy.data.images.load(os.fspath(optional_path), check_existing=True)

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
        roughness_image=optional_images.get("roughness_path"),
        normal_image=optional_images.get("normal_path"),
        metallic_image=optional_images.get("metallic_path"),
        alpha_image=optional_images.get("alpha_path"),
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
        maps=sorted(["base_color_path"] + list(optional_images)),
    )


MATERIAL_PRESETS = {
    "wood_oak": {
        "color": (0.72, 0.45, 0.22, 1.0),
        "roughness": 0.46,
        "metallic": 0.0,
    },
    "fabric_soft": {
        "color": (0.33, 0.46, 0.56, 1.0),
        "roughness": 0.88,
        "metallic": 0.0,
    },
    "brushed_metal": {
        "color": (0.62, 0.60, 0.56, 1.0),
        "roughness": 0.28,
        "metallic": 0.85,
    },
    "glass_clear": {
        "color": (0.72, 0.92, 1.0, 0.34),
        "roughness": 0.05,
        "metallic": 0.0,
        "alpha": 0.34,
    },
    "matte_plastic": {
        "color": (0.18, 0.18, 0.20, 1.0),
        "roughness": 0.62,
        "metallic": 0.0,
    },
}


def create_material_preset(name, preset):
    color = preset["color"]
    mat = create_material(name, color, roughness=preset["roughness"], metallic=preset["metallic"])
    alpha = preset.get("alpha")
    if alpha is not None:
        mat.blend_method = "BLEND"
        mat.use_screen_refraction = True
        bsdf = mat.node_tree.nodes.get("Principled BSDF")
        if bsdf and "Alpha" in bsdf.inputs:
            bsdf.inputs["Alpha"].default_value = alpha
    return mat


def action_apply_material_preset(params):
    object_name = params.get("object")
    if not isinstance(object_name, str) or not object_name.strip():
        raise ValueError("params.object must be a non-empty string")

    obj = bpy.data.objects.get(object_name)
    if obj is None:
        raise ValueError(f"Object not found: {object_name}")
    if not hasattr(obj.data, "materials"):
        raise ValueError(f"Object does not support materials: {object_name}")

    preset_name = params.get("preset")
    if preset_name not in MATERIAL_PRESETS:
        names = ", ".join(sorted(MATERIAL_PRESETS))
        raise ValueError(f"params.preset must be one of: {names}")

    material_name = params.get("material_name") or f"{object_name} {preset_name}"
    if not isinstance(material_name, str) or not material_name.strip():
        raise ValueError("params.material_name must be a non-empty string")

    mode = params.get("mode", "replace")
    if mode not in {"replace", "append"}:
        raise ValueError("params.mode must be 'replace' or 'append'")

    material = create_material_preset(material_name, MATERIAL_PRESETS[preset_name])
    if mode == "replace":
        obj.data.materials.clear()
    obj.data.materials.append(material)

    return make_result(
        True,
        message="Applied material preset.",
        object=obj.name,
        material=material.name,
        preset=preset_name,
        mode=mode,
    )


def action_setup_reference_camera(params):
    reference_object = params.get("reference_object")
    if reference_object is not None:
        if not isinstance(reference_object, str) or not reference_object.strip():
            raise ValueError("params.reference_object must be a non-empty string")
        if bpy.data.objects.get(reference_object) is None:
            raise ValueError(f"Reference object not found: {reference_object}")

    camera_location = get_vector(params, "camera_location", [4.2, -5.4, 2.45])
    target = get_vector(params, "target", [0.0, 0.0, 1.1])
    lens = get_number(params, "lens", 35, minimum=1, maximum=300)
    create_target = params.get("create_target", True)
    if not isinstance(create_target, bool):
        raise ValueError("params.create_target must be a boolean")

    if create_target:
        bpy.ops.object.empty_add(type="PLAIN_AXES", location=target)
        target_obj = bpy.context.object
        target_obj.name = "reference camera target"

    if bpy.context.scene.camera is None:
        bpy.ops.object.camera_add(location=camera_location)
        camera = bpy.context.object
        camera.name = "reference camera"
        bpy.context.scene.camera = camera
    else:
        camera = bpy.context.scene.camera
        camera.location = camera_location
    look_at(camera, target)
    camera.data.lens = lens

    resolution = params.get("resolution")
    if resolution is not None:
        set_resolution({"resolution": resolution})

    return make_result(
        True,
        message="Set up reference camera.",
        camera=camera.name,
        reference_object=reference_object,
        camera_location=camera_location,
        target=target,
        lens=lens,
    )


def action_setup_compare_view(params):
    reference_object = params.get("reference_object")
    if not isinstance(reference_object, str) or not reference_object.strip():
        raise ValueError("params.reference_object must be a non-empty string")
    reference = bpy.data.objects.get(reference_object)
    if reference is None:
        raise ValueError(f"Reference object not found: {reference_object}")

    mode = params.get("mode", "side_by_side")
    if mode not in {"side_by_side", "background"}:
        raise ValueError("params.mode must be 'side_by_side' or 'background'")

    if mode == "side_by_side":
        reference_location = get_vector(params, "reference_location", [2.25, 2.15, 1.55])
        reference_width = get_number(params, "reference_width", 2.5, minimum=0.1, maximum=100)
        camera_location = get_vector(params, "camera_location", [4.8, -5.8, 2.65])
        target = get_vector(params, "target", [0.55, 0.55, 1.25])
        lens = get_number(params, "lens", 30, minimum=1, maximum=300)
    else:
        reference_location = get_vector(params, "reference_location", [0, 2.65, 1.65])
        reference_width = get_number(params, "reference_width", 3.6, minimum=0.1, maximum=100)
        camera_location = get_vector(params, "camera_location", [4.2, -5.4, 2.45])
        target = get_vector(params, "target", [0.0, 0.2, 1.15])
        lens = get_number(params, "lens", 32, minimum=1, maximum=300)

    reference.location = reference_location
    reference.rotation_euler = get_vector(params, "reference_rotation", [math.radians(90), 0, 0])
    height = reference.dimensions.y if reference.dimensions.y else reference_width
    aspect = height / reference.dimensions.x if reference.dimensions.x else 1.0
    reference.dimensions = (reference_width, reference_width * aspect, 1)
    bpy.context.view_layer.objects.active = reference
    reference.select_set(True)
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    reference.select_set(False)

    if bpy.context.scene.camera is None:
        bpy.ops.object.camera_add(location=camera_location)
        camera = bpy.context.object
        camera.name = "compare camera"
        bpy.context.scene.camera = camera
    else:
        camera = bpy.context.scene.camera
        camera.location = camera_location
    look_at(camera, target)
    camera.data.lens = lens

    resolution = params.get("resolution")
    if resolution is not None:
        set_resolution({"resolution": resolution})

    return make_result(
        True,
        message="Set up compare view.",
        mode=mode,
        reference_object=reference.name,
        camera=camera.name,
        reference_location=reference_location,
        reference_width=reference_width,
        camera_location=camera_location,
        target=target,
        lens=lens,
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
    if action == "create_chair_model":
        return action_create_chair_model(params)
    if action == "create_sofa_model":
        return action_create_sofa_model(params)
    if action == "create_plant_model":
        return action_create_plant_model(params)
    if action == "create_lamp_model":
        return action_create_lamp_model(params)
    if action == "create_furniture_set":
        return action_create_furniture_set(params)
    if action == "create_room_layout":
        return action_create_room_layout(params)
    if action == "list_assets":
        return action_list_assets(params)
    if action == "inspect_rig":
        return action_inspect_rig(params)
    if action == "render_scene":
        return action_render_scene(params)
    if action == "set_render_preset":
        return action_set_render_preset(params)
    if action == "save_blend":
        return action_save_blend(params)
    if action == "export_glb":
        return action_export_glb(params)
    if action == "export_obj":
        return action_export_obj(params)
    if action == "import_asset":
        return action_import_asset(params)
    if action == "fit_object_to_bounds":
        return action_fit_object_to_bounds(params)
    if action == "inspect_scene":
        return action_inspect_scene(params)
    if action == "transform_object":
        return action_transform_object(params)
    if action == "duplicate_object":
        return action_duplicate_object(params)
    if action == "animate_object":
        return action_animate_object(params)
    if action == "add_reference_image":
        return action_add_reference_image(params)
    if action == "apply_texture_material":
        return action_apply_texture_material(params)
    if action == "apply_material_preset":
        return action_apply_material_preset(params)
    if action == "setup_reference_camera":
        return action_setup_reference_camera(params)
    if action == "setup_compare_view":
        return action_setup_compare_view(params)
    if action == "create_scene_from_reference":
        return action_create_scene_from_reference(params)
    if action == "run_python":
        return action_run_python(params)
    return make_result(
        False,
        error=f"Unsupported action: {action}",
        errorType="UnsupportedAction",
        hint="Reload the bridge code or install the latest add-on if this action was added recently.",
    )


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
