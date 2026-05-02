bl_info = {
    "name": "Codex Blender Bridge",
    "author": "Aditya",
    "version": (0, 7, 0),
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


def add_area_light(name, location, rotation, power, size):
    bpy.ops.object.light_add(type="AREA", location=location, rotation=rotation)
    light = bpy.context.object
    light.name = name
    light.data.energy = power
    light.data.size = size
    return light


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
    if action == "inspect_rig":
        return action_inspect_rig(params)
    if action == "render_scene":
        return action_render_scene(params)
    if action == "save_blend":
        return action_save_blend(params)
    if action == "import_asset":
        return action_import_asset(params)
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
