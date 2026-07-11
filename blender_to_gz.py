import bpy
import os
import time
import xml.etree.ElementTree as ET
from xml.dom import minidom
from bpy_extras.io_utils import ExportHelper
from bpy.types import Operator
from mathutils import Vector

# -----------------------------------------------------
# SETTINGS
# -----------------------------------------------------
VISUAL_DECIMATION_THRESHOLD = 3000
COLLISION_BOX_THRESHOLD = 500

# -----------------------------------------------------
# HELPERS
# -----------------------------------------------------
def get_bbox_size(obj):
    world_corners = [obj.matrix_world @ Vector(c) for c in obj.bound_box]
    xs = [v.x for v in world_corners]
    ys = [v.y for v in world_corners]
    zs = [v.z for v in world_corners]
    size_x = max(max(xs) - min(xs), 0.001)
    size_y = max(max(ys) - min(ys), 0.001)
    size_z = max(max(zs) - min(zs), 0.001)
    return size_x, size_y, size_z

def compute_box_inertia(mass, size_x, size_y, size_z):
    ixx = (1/12) * mass * (size_y**2 + size_z**2)
    iyy = (1/12) * mass * (size_x**2 + size_z**2)
    izz = (1/12) * mass * (size_x**2 + size_y**2)
    return ixx, iyy, izz

# -----------------------------------------------------
# MAIN EXPORT
# -----------------------------------------------------
def export_world(filepath):
    directory = os.path.dirname(filepath)
    world_name = os.path.splitext(os.path.basename(filepath))[0]

    meshes_folder = "meshes"
    meshes_dir = os.path.join(directory, meshes_folder)
    os.makedirs(meshes_dir, exist_ok=True)

    print("Exporting world:", world_name)

    # -----------------------------------------------------
    # COLLECT OBJECTS
    # -----------------------------------------------------
    objects = bpy.context.scene.objects
    mesh_objects = [o for o in objects if o.type == "MESH" and not o.name.startswith("_ignore_")]

    if not mesh_objects:
        print("No mesh objects found.")
        return

    # -----------------------------------------------------
    # APPLY SCALE
    # -----------------------------------------------------
    bpy.ops.object.select_all(action='DESELECT')
    for obj in mesh_objects:
        obj.select_set(True)
    bpy.context.view_layer.objects.active = mesh_objects[0]
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)

    # -----------------------------------------------------
    # DECIMATION
    # -----------------------------------------------------
    for obj in mesh_objects:
        num_verts = len(obj.data.vertices)
        while num_verts > VISUAL_DECIMATION_THRESHOLD:
            print(f"Decimating {obj.name}: {num_verts} verts")
            bpy.context.view_layer.objects.active = obj
            mod = obj.modifiers.new(name="Decimate", type='DECIMATE')
            mod.ratio = 0.5
            bpy.ops.object.modifier_apply(modifier=mod.name)
            time.sleep(0.05)
            num_verts = len(obj.data.vertices)

# -----------------------------------------------------
# EXPORT COLLADA
# -----------------------------------------------------
    for obj in mesh_objects:
        dae_filename = f"{obj.name}.dae"
        dae_path = os.path.join(meshes_dir, dae_filename)

        # Deselect everything first
        bpy.ops.object.select_all(action='DESELECT')

        # Select ONLY this object
        obj.select_set(True)
        bpy.context.view_layer.objects.active = obj

        # Export only selected
        bpy.ops.wm.collada_export(
            filepath=dae_path,
            check_existing=False,
            selected=True
        )

        print(f"Collada exported to {dae_path}")

    # -----------------------------------------------------
    # BUILD WORLD (SDF)
    # -----------------------------------------------------
    sdf = ET.Element("sdf", attrib={"version": "1.9"})
    world = ET.SubElement(sdf, "world", attrib={"name": "main_world"})

    # Full physics / GUI / plugins / lights / ground plane
    gui_plugin_block = """<physics name="default_physics" type="ode">
  <max_step_size>0.01</max_step_size>
  <real_time_factor>1.0</real_time_factor>
  <enable_physics>true</enable_physics>
</physics>

<plugin filename="ignition-gazebo-user-commands-system" name="ignition::gazebo::systems::UserCommands"/>
<plugin filename="gz-sim-physics-system" name="gz::sim::systems::Physics"/>
<plugin filename="gz-sim-scene-broadcaster-system" name="gz::sim::systems::SceneBroadcaster"/>

<!-- GUI + Plugins -->
<gui fullscreen="0">
  <!-- Paste your full GUI/plugins block here exactly -->
</gui>

<!-- Light -->
<light type="directional" name="sun">
  <cast_shadows>true</cast_shadows>
  <pose>0 0 10 0 0 0</pose>
  <diffuse>0.8 0.8 0.8 1</diffuse>
  <specular>0.2 0.2 0.2 1</specular>
  <attenuation>
    <range>1000</range>
    <constant>0.9</constant>
    <linear>0.01</linear>
    <quadratic>0.001</quadratic>
  </attenuation>
  <direction>-0.5 0.1 -0.9</direction>
</light>

<!-- Ground plane -->
<model name="ground_plane">
  <static>true</static>
  <link name="ground">
    <collision name="collision">
      <geometry>
        <plane>
          <normal>0 0 1</normal>
          <size>100 100</size>
        </plane>
      </geometry>
    </collision>
    <visual name="visual">
      <geometry>
        <plane>
          <normal>0 0 1</normal>
          <size>100 100</size>
        </plane>
      </geometry>
      <material>
        <ambient>0.8 0.8 0.8 1</ambient>
        <diffuse>0.8 0.8 0.8 1</diffuse>
        <specular>0.8 0.8 0.8 1</specular>
      </material>
    </visual>
  </link>
</model>
"""
    import xml.etree.ElementTree as ET_temp
    block_tree = ET_temp.fromstring(f"<root>{gui_plugin_block}</root>")
    for child in block_tree:
        world.append(child)

    # -----------------------------------------------------
    # ADD MESH OBJECTS WITH COLLISION AND INERTIA (like old GZ script)
    # -----------------------------------------------------
    for obj in mesh_objects:
        model = ET.SubElement(world, "model", attrib={"name": obj.name})
        link = ET.SubElement(model, "link", attrib={"name": obj.name + "_link"})

        loc = obj.matrix_world.translation
        rot = obj.matrix_world.to_euler()
        ET.SubElement(model, "pose").text = f"0 0 0 0 0 0"
        size_x, size_y, size_z = get_bbox_size(obj)

        # Static or dynamic
        if obj.name.startswith("_static_"):
            ET.SubElement(model, "static").text = "true"
        else:
            ET.SubElement(model, "static").text = "false"

            # Inertial
            mass = 1.0
            inertial = ET.SubElement(link, "inertial")
            ET.SubElement(inertial, "mass").text = f"{mass:.5f}"
            inertia = ET.SubElement(inertial, "inertia")
            ixx, iyy, izz = compute_box_inertia(mass, size_x, size_y, size_z)
            ET.SubElement(inertia, "ixx").text = f"{ixx:.8f}"
            ET.SubElement(inertia, "iyy").text = f"{iyy:.8f}"
            ET.SubElement(inertia, "izz").text = f"{izz:.8f}"
            ET.SubElement(inertia, "ixy").text = "0"
            ET.SubElement(inertia, "ixz").text = "0"
            ET.SubElement(inertia, "iyz").text = "0"
            ET.SubElement(inertial, "pose").text = f"{loc.x:.5f} {loc.y:.5f} {loc.z:.5f} 0 0 0"

            ET.SubElement(link, "self_collide").text = "0"
            ET.SubElement(link, "enable_wind").text = "0"
            ET.SubElement(link, "kinematic").text = "0"

        # Visual
        visual = ET.SubElement(link, "visual", attrib={"name": obj.name})
        geometry = ET.SubElement(visual, "geometry")
        mesh = ET.SubElement(geometry, "mesh")
        ET.SubElement(mesh, "uri").text = f"meshes/{obj.name}.dae"
        submesh = ET.SubElement(mesh, "submesh")
        ET.SubElement(submesh, "name").text = obj.name

        # Collision
        collision = ET.SubElement(link, "collision", attrib={"name": obj.name + "_collision"})
        geometry_c = ET.SubElement(collision, "geometry")
        num_verts = len(obj.data.vertices)
        if num_verts > COLLISION_BOX_THRESHOLD:
            box = ET.SubElement(geometry_c, "box")
            ET.SubElement(box, "size").text = f"{size_x:.5f} {size_y:.5f} {size_z:.5f}"
            ET.SubElement(collision, "pose").text = f"{loc.x:.5f} {loc.y:.5f} {loc.z:.5f} 0 0 0"
        else:
            mesh_c = ET.SubElement(geometry_c, "mesh")
            ET.SubElement(mesh_c, "uri").text = f"meshes/{obj.name}.dae"
            submesh_c = ET.SubElement(mesh_c, "submesh")
            ET.SubElement(submesh_c, "name").text = obj.name

        ET.SubElement(collision, "max_contacts").text = "10"
        surface = ET.SubElement(collision, "surface")
        contact = ET.SubElement(surface, "contact")
        ET.SubElement(contact, "ode")
        friction = ET.SubElement(surface, "friction")
        ET.SubElement(friction, "ode")
        torsional = ET.SubElement(friction, "torsional")
        ET.SubElement(torsional, "ode")

    # -----------------------------------------------------
    # WRITE SDF FILE
    # -----------------------------------------------------
    xml_string = ET.tostring(sdf, encoding='unicode')
    pretty_xml = minidom.parseString(xml_string).toprettyxml(indent="  ")
    with open(filepath, "w") as f:
        f.write(pretty_xml)

    print("Export complete! SDF written to:", filepath)

# -----------------------------------------------------
# BLENDER OPERATOR
# -----------------------------------------------------
class OT_ExportWorld(Operator, ExportHelper):
    bl_idname = "export.ignition_world"
    bl_label = "Export Ignition World"
    filename_ext = ".sdf"

    def execute(self, context):
        export_world(self.filepath)
        return {"FINISHED"}

def register():
    bpy.utils.register_class(OT_ExportWorld)

def unregister():
    bpy.utils.unregister_class(OT_ExportWorld)

if __name__ == "__main__":
    register()
    bpy.ops.export.ignition_world("INVOKE_DEFAULT")