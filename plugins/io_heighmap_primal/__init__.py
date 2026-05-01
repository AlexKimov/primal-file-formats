bl_info = {
    "name": "Import .land/.light (Primal Software)",
    "author": "",
    "version": (0, 1),
    "blender": (3, 0, 0),
    "location": "File > Import",
    "description": "Import terrain heightmaps (.land) with optional .light textures",
    "category": "Import-Export",
}

import bpy
import sys
import importlib

from . import (
    import_operator,
    export_operator,
    ui,
)

classes = (
    import_operator.ImportPrimal,
    ui.PrimalDayPanel,
    export_operator.ExportLand,
    export_operator.ExportLight,
)

def cleanse_modules():
    """search for your plugin modules in blender python sys.modules and remove them"""

    import sys

    all_modules = sys.modules 
    all_modules = dict(sorted(all_modules.items(),key= lambda x:x[0])) #sort them
   
    for k,v in all_modules.items():
        if k.startswith(__name__):
            del sys.modules[k]

    return None 

def register()
    from bpy.props import EnumProperty
    
    bpy.types.Object.primal_day_part = EnumProperty(
        name="Day Part",
        description="Switch terrain lighting variant",
        items=[
            ("0", "Dawn", "Dawn lighting"),
            ("1", "Day", "Daytime lighting"),
            ("2", "Dusk", "Dusk lighting"),
            ("3", "Night", "Night lighting"),
        ],
        default="1",
        update=ui.switch_day_part
    )

    for cls in classes:
        try:
            bpy.utils.register_class(cls)
        except ValueError:
            pass

    bpy.types.TOPBAR_MT_file_import.append(import_operator.menu_func)
    bpy.types.TOPBAR_MT_file_export.append(export_operator.menu_func_land)
    bpy.types.TOPBAR_MT_file_export.append(export_operator.menu_func_light)

def unregister():
    bpy.types.TOPBAR_MT_file_import.remove(import_operator.menu_func)
    bpy.types.TOPBAR_MT_file_export.remove(export_operator.menu_func_land)
    bpy.types.TOPBAR_MT_file_export.remove(export_operator.menu_func_light)

    for cls in reversed(classes):
        try:
            bpy.utils.unregister_class(cls)
        except RuntimeError:
            pass

    del bpy.types.Object.primal_day_part
    cleanse_modules()

if __name__ == "__main__":
    register()