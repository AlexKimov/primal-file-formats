# ui.py
"""UI layout helpers and day-part panel."""
import bpy


def draw_import_ui(layout, operator):
    terrain_box = layout.box()
    terrain_box.label(text="Terrain settings")
    terrain_box.prop(operator, "height_scale")
    terrain_box.prop(operator, "cell_size")

    tex_box = layout.box()
    tex_box.label(text="Texture settings")
    tex_box.prop(operator, "load_textures", text="Load textures")
    
    if operator.load_textures:
        tex_box.prop(operator, "load_mode", expand=True)
        if operator.load_mode == 'SINGLE':
            tex_box.prop(operator, "day_part", text="Day part")
        tex_box.prop(operator, "texture_type")
        tex_box.prop(operator, "export_textures")


def switch_day_part(obj, context):
    if hasattr(obj, "material_slots") and len(obj.material_slots) >= 4:
        obj.active_material_index = int(obj.primal_day_part)


class PrimalDayPanel(bpy.types.Panel):
    bl_label = "Primal Day Switcher"
    bl_idname = "VIEW3D_PT_primal_day_switch"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Primal"

    @classmethod
    def poll(cls, context):
        obj = context.active_object
        return obj and hasattr(obj, "primal_day_part")

    def draw(self, context):
        layout = self.layout
        obj = context.active_object
        layout.prop(obj, "primal_day_part", expand=True)