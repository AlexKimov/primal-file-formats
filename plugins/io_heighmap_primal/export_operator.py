# export_operator.py
"""Blender operators to export .land and .light files."""

import bpy
import os
import io

try:
    from PIL import Image
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False

from .heightmap_exporter import (read_land_template,
                                 build_height_array,
                                 write_land_file)
from .light_exporter import tile_atlas_to_streams, calculate_clipmap_count
from .binary_reader import BinaryReader
from .binary_writer import BinaryWriter


# ----------------------------------------------------------------------
# Shared helpers
# ----------------------------------------------------------------------
def _get_texture_from_material_slot(obj, slot_index):
    """Return the Image node connected to Base Color, or None."""
    if slot_index >= len(obj.material_slots):
        return None
    mat = obj.material_slots[slot_index].material
    if not mat or not mat.use_nodes:
        return None
    for node in mat.node_tree.nodes:
        if node.type == 'TEX_IMAGE' and node.image:
            for link in mat.node_tree.links:
                if (link.from_node == node and
                    link.to_socket.name == 'Base Color'):
                    return node.image
    return None


# ----------------------------------------------------------------------
# .land export operator
# ----------------------------------------------------------------------
class ExportLand(bpy.types.Operator):
    """Export active terrain mesh as a .land heightmap file."""
    bl_idname = "export_land.primal"
    bl_label = "Export .land"
    filename_ext = ".land"
    filter_glob: bpy.props.StringProperty(default="*.land", options={"HIDDEN"})

    template_path: bpy.props.StringProperty(
        name="Template .land",
        description="Original .land file to copy header structure from",
        subtype='FILE_PATH'
    )
    height_scale: bpy.props.FloatProperty(
        name="Height Scale",
        description="Vertical scale factor used during import (vertex Z / scale = original int16)",
        default=0.02, min=0.001, max=10.0
    )

    def draw(self, context):
        layout = self.layout
        layout.prop(self, "template_path")
        layout.prop(self, "height_scale")

    def execute(self, context):
        obj = context.active_object
        if not obj or obj.type != 'MESH':
            self.report({"ERROR"}, "Select a mesh object")
            return {"CANCELLED"}

        if not self.template_path or not os.path.exists(self.template_path):
            self.report({"ERROR"}, "Template .land file not found")
            return {"CANCELLED"}

        try:
            prefix, width, height, suffix = read_land_template(self.template_path)
        except Exception as e:
            self.report({"ERROR"}, f"Failed to read template: {e}")
            return {"CANCELLED"}

        mesh = obj.data
        if len(mesh.vertices) != width * height:
            self.report({"ERROR"},
                        f"Mesh has {len(mesh.vertices)} vertices, expected {width}x{height}")
            return {"CANCELLED"}

        try:
            heights = build_height_array(mesh.vertices, width, height, self.height_scale)
            write_land_file(self.filepath, prefix, heights, suffix)
        except Exception as e:
            self.report({"ERROR"}, f"Failed to write .land: {e}")
            return {"CANCELLED"}

        self.report({"INFO"}, f"Exported .land to {self.filepath}")
        return {"FINISHED"}


# ----------------------------------------------------------------------
# .light export operator
# ----------------------------------------------------------------------
class ExportLight(bpy.types.Operator):
    """Export texture atlas as a .light archive."""
    bl_idname = "export_light.primal"
    bl_label = "Export .light"
    filename_ext = ".light"
    filter_glob: bpy.props.StringProperty(default="*.light", options={"HIDDEN"})

    template_path: bpy.props.StringProperty(
        name="Template .light",
        description="Original .light file to copy header structure from",
        subtype='FILE_PATH'
    )
    day0_material: bpy.props.IntProperty(name="Dawn mat slot", default=0, min=0, max=3)
    day1_material: bpy.props.IntProperty(name="Day mat slot",  default=1, min=0, max=3)
    day2_material: bpy.props.IntProperty(name="Dusk mat slot", default=2, min=0, max=3)
    day3_material: bpy.props.IntProperty(name="Night mat slot",default=3, min=0, max=3)

    def draw(self, context):
        layout = self.layout
        layout.prop(self, "template_path")
        layout.label(text="Day part material slots:")
        layout.prop(self, "day0_material")
        layout.prop(self, "day1_material")
        layout.prop(self, "day2_material")
        layout.prop(self, "day3_material")

    def execute(self, context):
        obj = context.active_object
        if not obj or obj.type != 'MESH':
            self.report({"ERROR"}, "Select a mesh with terrain materials")
            return {"CANCELLED"}

        if not self.template_path or not os.path.exists(self.template_path):
            self.report({"ERROR"}, "Template .light file not found")
            return {"CANCELLED"}

        if not PIL_AVAILABLE:
            self.report({"ERROR"}, "Pillow is required for texture encoding")
            return {"CANCELLED"}

        # 1. Parse template header
        try:
            r = BinaryReader(self.template_path)
            r.read_bytes(11)                     # magic
            r.read_u32()                         # unk
            tile_number = r.read_u32()
            tiles_in_row = r.read_u32()
            r.read_u32()                         # format_enum
            day_parts = r.read_u32()
            for _ in range(day_parts):
                r.read_f32(); r.read_f32(); r.read_f32(); r.read_f32()
            main_sub = r.read_u32()
            main_qual = r.read_u32()
            map_sub = r.read_u32()
            map_qual = r.read_u32()
            clipmap_sub = r.read_u32()
            clipmap_qual = r.read_u32()
            clipmap_stride1 = r.read_u32()
            clipmap_stride2 = r.read_u32()
            prefix_len = r.tell()
            r.close()
        except Exception as e:
            self.report({"ERROR"}, f"Failed to parse template: {e}")
            return {"CANCELLED"}

        with open(self.template_path, 'rb') as f:
            prefix = f.read(prefix_len)

        # 2. Gather atlas images
        grid = tiles_in_row
        tile_size = tile_number
        atlas_size = tile_size * grid

        day_slots = [self.day0_material, self.day1_material,
                     self.day2_material, self.day3_material]
        day_image = {}
        for day, slot in enumerate(day_slots):
            img = _get_texture_from_material_slot(obj, slot)
            if img:
                day_image[day] = img

        if not day_image:
            self.report({"ERROR"}, "No day part textures found")
            return {"CANCELLED"}

        fallback = min(day_image.keys())
        for day in range(day_parts):
            if day not in day_image:
                day_image[day] = day_image[fallback]

        # 3. Tile and compress
        all_tiles = []
        quality = main_qual

        for day in range(day_parts):
            atlas_blender = day_image[day]
            if atlas_blender.size[0] != atlas_size or atlas_blender.size[1] != atlas_size:
                self.report({"ERROR"},
                            f"Day {day} atlas must be {atlas_size}x{atlas_size}")
                return {"CANCELLED"}

            tmp_path = bpy.path.abspath("//") + "temp_atlas.png"
            atlas_blender.filepath_raw = tmp_path
            atlas_blender.file_format = 'PNG'
            atlas_blender.save()
            atlas_pil = Image.open(tmp_path).convert('RGB')
            os.unlink(tmp_path)

            tiles = tile_atlas_to_streams(atlas_pil, grid, tile_size, quality)
            all_tiles.extend(tiles)

        # 4. Assemble sizes
        num1 = day_parts * grid * grid
        main_sizes = [len(t) for t in all_tiles]
        clip_count = (calculate_clipmap_count(grid, tile_number,
                                              clipmap_stride1, clipmap_stride2)
                      * day_parts)

        # 5. Write
        writer = BinaryWriter()
        writer.write_bytes(prefix)
        writer.write_array('I', main_sizes)
        writer.write_u32(0)                       # map_size
        writer.write_array('I', [0] * clip_count) # clipmap sizes
        for tile in all_tiles:
            writer.write_bytes(tile)

        with open(self.filepath, 'wb') as f:
            f.write(writer.to_bytes())

        self.report({"INFO"}, f"Exported .light with {num1} tiles to {self.filepath}")
        return {"FINISHED"}


# ----------------------------------------------------------------------
# Menu functions
# ----------------------------------------------------------------------
def menu_func_land(self, context):
    self.layout.operator(ExportLand.bl_idname, text="Primal .land")

def menu_func_light(self, context):
    self.layout.operator(ExportLight.bl_idname, text="Primal .light")