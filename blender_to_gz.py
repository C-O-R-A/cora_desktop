import bpy
import os.path
from bpy_extras.io_utils import ImportHelper
from bpy.props import StringProperty, BoolProperty
from bpy.types import Operator

import xml.etree.ElementTree as ET
from xml.dom import minidom

# Target blender version: 3.x+

########################################################################################################################
### Exports model.dae of the scene with textures, its corresponding model.sdf file, and a default model.config file ####
########################################################################################################################
def export_sdf(prefix_path):
    USE_DAE_MATERIALS = True

    dae_filename = 'chess_world.dae'
    sdf_filename = 'chess_world.sdf'
    model_config_filename = 'chess_world.config'
    lightmap_filename = 'LightmapBaked.png'
    model_name = 'chess_world'
    meshes_folder_prefix = 'meshes/'
    
    # use all objects in the current scene (newer Blender API)
    objects = bpy.context.scene.objects
    mesh_objects = [o for o in objects if o.type == 'MESH']
    light_objects = [o for o in objects if o.type == 'LIGHT']
    
    # Ensure meshes folder exists
    meshes_dir = os.path.join(prefix_path, meshes_folder_prefix)
    if not os.path.exists(meshes_dir):
        os.makedirs(meshes_dir)
    
    # Select all mesh objects for export
    bpy.ops.object.select_all(action='DESELECT')
    for o in mesh_objects:
        o.select_set(True)
    
    # Exports the dae file and its associated textures (selected objects only)
    if mesh_objects:
        bpy.context.view_layer.objects.active = mesh_objects[0]
        bpy.ops.wm.collada_export(filepath=os.path.join(prefix_path, meshes_folder_prefix, dae_filename), check_existing=False)

    #############################################
    #### export sdf xml based off the scene #####
    #############################################
    
    # Helper function to resolve Blender duplicate image names (e.g., "marker_0.png.001" -> "marker_0.png")
    def resolve_image_name(img_name, meshes_dir):
        """Find the actual image file, handling Blender's .001, .002 suffixes"""
        # Try the name as-is first
        full_path = os.path.join(meshes_dir, img_name)
        if os.path.isfile(full_path):
            return img_name
        
        # Try stripping Blender duplicate suffixes (.001, .002, etc.)
        import re
        # Match patterns like .001, .002 before the extension
        match = re.match(r'^(.+?)(\.\d{3})?(\.[^.]+)$', img_name)
        if match:
            base, dup_suffix, ext = match.groups()
            if dup_suffix:  # If there's a duplicate suffix
                resolved_name = base + ext
                full_path = os.path.join(meshes_dir, resolved_name)
                if os.path.isfile(full_path):
                    return resolved_name
        
        # Return original if nothing found (Gazebo will report the error)
        return img_name
    
    # Helper to find texture files in meshes directory by partial name matching
    def find_texture_for_material(mat_name, meshes_dir):
        """Find a texture file in meshes folder that might match this material"""
        if not os.path.isdir(meshes_dir):
            return ""
        
        # List all image files
        image_files = [f for f in os.listdir(meshes_dir) if f.lower().endswith(('.png', '.jpg', '.jpeg'))]
        
        if not image_files:
            return ""
        
        # Try exact match first (after resolving .001 suffixes)
        for img_file in image_files:
            if img_file == mat_name or resolve_image_name(mat_name, meshes_dir) == img_file:
                return img_file
        
        # Try base name matching (e.g., "marker_0.png" for material "marker_0.png.001")
        mat_base = mat_name.split('.')[0] if '.' in mat_name else mat_name
        for img_file in image_files:
            img_base = img_file.rsplit('.', 1)[0]  # Remove extension
            if mat_base and img_base == mat_base:
                return img_file
        
        # If we have exactly one texture file and multiple materials, return it
        if len(image_files) == 1:
            return image_files[0]
        
        return ""
    
    sdf = ET.Element('sdf', attrib={'version':'1.9'})

    # 1 model and 1 link
    model = ET.SubElement(sdf, "model", attrib={"name":"test"})
    static = ET.SubElement(model, "static")
    static.text = "true"
    link = ET.SubElement(model, "link", attrib={"name":"testlink"})
    # for each geometry in geometry library add a <visual> tag
    for o in mesh_objects:
        # If object has multiple materials, create a visual per material slot
        materials = o.data.materials if hasattr(o.data, 'materials') else []
        if not materials or len(materials) == 0:
            materials = [None]
        
        for mat_idx, mat in enumerate(materials):
            visual_name = f"{o.name}_{mat_idx}" if len(materials) > 1 else o.name
            visual = ET.SubElement(link, "visual", attrib={"name": visual_name})

            geometry = ET.SubElement(visual, "geometry")
            mesh = ET.SubElement(geometry, "mesh")
            uri = ET.SubElement(mesh, "uri")
            uri.text = meshes_folder_prefix + dae_filename
            submesh = ET.SubElement(mesh, "submesh")
            submesh_name = ET.SubElement(submesh, "name")
            submesh_name.text = o.name
            
            # Extract material properties from Principled BSDF
            diffuse_map = ""
            base_color_rgb = [1.0, 1.0, 1.0, 1.0]  # default white
            metallic = 0.0
            roughness = 0.5
            
            if mat is not None and getattr(mat, 'use_nodes', False):
                nodes = mat.node_tree.nodes
                principled = None
                for n in nodes:
                    if n.type == 'BSDF_PRINCIPLED' or n.bl_idname == 'ShaderNodeBsdfPrincipled':
                        principled = n
                        break
                if principled is not None:
                    # Extract Base Color (RGB value or texture)
                    base_color = principled.inputs.get('Base Color')
                    if base_color is not None:
                        # If connected to texture, get the image name
                        if len(base_color.links) > 0:
                            link_node = base_color.links[0].from_node
                            if hasattr(link_node, 'image') and link_node.image is not None:
                                img_name = link_node.image.name
                                # Try to find the actual texture file
                                resolved_img = find_texture_for_material(img_name, meshes_dir)
                                if resolved_img:
                                    diffuse_map = resolved_img
                        else:
                            # No texture, use the color value directly
                            color_val = base_color.default_value
                            if hasattr(color_val, '__len__'):
                                base_color_rgb = [float(color_val[0]), float(color_val[1]), float(color_val[2]), 1.0]
                    
                    # Extract Metallic value
                    metallic_input = principled.inputs.get('Metallic')
                    if metallic_input is not None and len(metallic_input.links) == 0:
                        metallic = float(metallic_input.default_value)
                    
                    # Extract Roughness value
                    roughness_input = principled.inputs.get('Roughness')
                    if roughness_input is not None and len(roughness_input.links) == 0:
                        roughness = float(roughness_input.default_value)
            elif mat is None or not getattr(mat, 'use_nodes', False):
                # For materials without nodes, try to find a matching texture file
                if mat is not None:
                    resolved_img = find_texture_for_material(mat.name, meshes_dir)
                    if resolved_img:
                        diffuse_map = resolved_img
            
            # setup diffuse/specular color
            if not USE_DAE_MATERIALS:
                material_elem = ET.SubElement(visual, "material")
                diffuse = ET.SubElement(material_elem, "diffuse")
                diffuse.text = f"{base_color_rgb[0]} {base_color_rgb[1]} {base_color_rgb[2]} {base_color_rgb[3]}"
                specular = ET.SubElement(material_elem, "specular")
                specular.text = "0.0 0.0 0.0 1.0"
                pbr = ET.SubElement(material_elem, "pbr")
                metal = ET.SubElement(pbr, "metal")
                if diffuse_map != "":
                    albedo_map = ET.SubElement(metal, "albedo_map")
                    albedo_map.text = meshes_folder_prefix + diffuse_map
            
            # for lightmapping, add the UV and turn off casting of shadows
            lightmap_path = os.path.join(prefix_path, meshes_folder_prefix, lightmap_filename)
            if os.path.isfile(lightmap_path):
                light_map = ET.SubElement(metal, "light_map", attrib={"uv_set":"1"})
                light_map.text = meshes_folder_prefix + lightmap_filename

                cast_shadows = ET.SubElement(visual, "cast_shadows")
                cast_shadows.text = "0"
        
    from mathutils import Vector

    def add_attenuation_tags(light_elem, blender_light):
        attenuation = ET.SubElement(light_elem, "attenuation")
        # distance / range
        rng = getattr(blender_light, 'cutoff_distance', None)
        if rng is None:
            rng = getattr(blender_light, 'distance', None)
        if rng is None:
            rng = 25.0
        r = ET.SubElement(attenuation, "range")
        r.text = str(rng)

        # Blender does not expose linear/quadratic coefficients directly in recent APIs.
        # Provide a reasonable default attenuation: constant=1, linear=0, quadratic=1/(range^2)
        try:
            quad_val = 1.0 / (float(rng) * float(rng)) if float(rng) != 0.0 else 0.0
        except Exception:
            quad_val = 0.0

        linear_attenuation = ET.SubElement(attenuation, "linear")
        linear_attenuation.text = "0.0"
        quad_attenuation = ET.SubElement(attenuation, "quadratic")
        quad_attenuation.text = str(quad_val)
        const_attenuation = ET.SubElement(attenuation, "constant")
        const_attenuation.text = "1.0"

        cast_shadows = ET.SubElement(light, "cast_shadows")
        cast_shadows.text = "true"

        intensity = ET.SubElement(light, "intensity")
        intensity.text = str(getattr(blender_light, 'energy', 1.0))
    
    ## sdf collision tags
    collision = ET.SubElement(link, "collision", attrib={"name":"collision"})

    geometry = ET.SubElement(collision, "geometry")
    mesh = ET.SubElement(geometry, "mesh")
    uri = ET.SubElement(mesh, "uri")
    uri.text = meshes_folder_prefix + dae_filename

    surface = ET.SubElement(collision, "surface")
    contact = ET.SubElement(surface, "contact")

    ## sdf write to file
    xml_string = ET.tostring(sdf, encoding='unicode')
    reparsed = minidom.parseString(xml_string)

    sdf_file = open(prefix_path+sdf_filename, "w")
    sdf_file.write(reparsed.toprettyxml(indent="  "))
    sdf_file.close()

    ##############################
    ### generate model.config ####
    ##############################
    model = ET.Element('model')
    name = ET.SubElement(model, 'name')
    name.text = model_name
    version = ET.SubElement(model, 'version')
    version.text = "1.0"
    sdf_tag = ET.SubElement(model, "sdf", attrib={"sdf":"1.8"})
    sdf_tag.text = sdf_filename

    author = ET.SubElement(model, 'author')
    name = ET.SubElement(author, 'name')
    name.text = "Generated by blender SDF tools"

    xml_string = ET.tostring(model, encoding='unicode')
    reparsed = minidom.parseString(xml_string)

    config_file = open(prefix_path+model_config_filename, "w")
    config_file.write(reparsed.toprettyxml(indent="  "))
    config_file.close()


#### UI Handling ####
class OT_TestOpenFilebrowser(Operator, ImportHelper):
  bl_idname = "test.open_filebrowser"
  bl_label = "Save"
  
  directory : bpy.props.StringProperty(name="Outdir Path")
  
  def execute(self, context):
    """Do the export with the selected file."""

    if not os.path.isdir(self.directory):
        print(self.directory + " is not a directory!")
    else:
        print("exporting to directory: " + self.directory)
        export_sdf(self.directory)
    return {'FINISHED'}

def register(): 
    bpy.utils.register_class(OT_TestOpenFilebrowser) 
def unregister(): 
    bpy.utils.unregister_class(OT_TestOpenFilebrowser)
    
if __name__ == "__main__":
    register() 
    bpy.ops.test.open_filebrowser('INVOKE_DEFAULT')

# alternatively comment the main code block and do a function call without going through all the ui
# prefix_path = '/home/ddeng/blender_lightmap/final_office/office/'
# export_sdf(prefix_path)