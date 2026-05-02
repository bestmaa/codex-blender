bl_info = {
    "name": "Codex Blender Bridge",
    "author": "Aditya",
    "version": (0, 1, 0),
    "blender": (3, 6, 0),
    "location": "View3D > Sidebar > Codex",
    "description": "Local HTTP bridge for sending Codex commands to Blender.",
    "category": "3D View",
}

import contextlib
import io
import json
import queue
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import bpy
from mathutils import Vector


HOST = "127.0.0.1"
PORT = 8765

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
    if action == "inspect_rig":
        return action_inspect_rig(params)
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
        if not job.event.wait(timeout=30):
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


CLASSES = (
    CODEXBLENDER_OT_start_bridge,
    CODEXBLENDER_OT_stop_bridge,
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

