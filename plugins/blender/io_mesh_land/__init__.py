bl_info = {
    "name": "Import .land Heightmap",
    "author": "",
    "version": (0, 1),
    "blender": (3, 0, 0),
    "location": "File > Import >I of The Dragon .land heightmap",
    "description": "Imports heightmap from I of The Dragon .land file",
    "category": "Import-Export",
}

import bpy
import struct
import os
from bpy.props import StringProperty, FloatProperty

class ImportLandOperator(bpy.types.Operator):
    bl_idname = "import_mesh.land_heightmap"
    bl_label = "Import .land Heightmap"
    bl_options = {'PRESET', 'UNDO'}

    filter_glob: StringProperty(
        default="*.land",
        options={'HIDDEN'},
        maxlen=255, 
    ) 

    filepath: StringProperty(
        name="File Path",
        description="Filepath used for importing the file",
        maxlen=1024,
        subtype='FILE_PATH',
    )

    height_scale: FloatProperty(
        name="Height Scale",
        description="Scale factor for the height values (Raw values are -32k to 32k)",
        default=0.02,
        min=0.001,
        max=0.1,
    )

    def execute(self, context):
        filepath = self.filepath
        
        if not os.path.exists(filepath):
            self.report({'ERROR'}, f"File not found: {filepath}")
            return {'CANCELLED'}

        try:
            with open(filepath, 'rb') as f:
                f.seek(36)        
                points = struct.unpack('<H', f.read(2))[0]

                # Read heightmap data
                # Total bytes needed: points * points * 2 (16-bit signed short)
                total_vertices = points * points 
                total_bytes = total_vertices * 2
                
                height_data = f.read(total_bytes)

                # Unpack heights (signed short 'h', Little Endian '<')
                heights = struct.unpack(f'<{total_vertices}h', height_data)

                verts = []
                faces = []

                offset = (points - 1) / 2.0
                
                for i in range(total_vertices):
                    y = i // points
                    x = i % points

                    h_val = heights[i] * self.height_scale
                    
                    # Coordinate mapping: 
                    # X = Right, Y = Forward (Blender), Z = Up
                    # We map grid x/y to Blender x/y
                    vx = (x - offset)
                    vy = (y - offset)
                    vz = h_val
                    
                    verts.append((vx, vy, vz))

                # Generate Faces (Quads)
                for y in range(points - 1):
                    for x in range(points - 1):
                        # Indices of the 4 corners of the quad
                        v1 = y * points + x
                        v2 = v1 + 1
                        v3 = (y + 1) * points + x + 1
                        v4 = (y + 1) * points + x
                        
                        faces.append((v1, v2, v3, v4))

                mesh = bpy.data.meshes.new("Heightmap")
                obj = bpy.data.objects.new("Heightmap", mesh)
                
                context.collection.objects.link(obj)
                
                mesh.from_pydata(verts, [], faces)
                mesh.update()
                
                for poly in mesh.polygons:
                    poly.use_smooth = True   
                
                self.report({'INFO'}, f"Imported {points}x{points} heightmap")
                
        except Exception as e:
            self.report({'ERROR'}, f"Error importing file: {str(e)}")
            return {'CANCELLED'}

        return {'FINISHED'}

    def invoke(self, context, event):
        context.window_manager.fileselect_add(self)
        return {'RUNNING_MODAL'}


def menu_func_import(self, context):
    self.layout.operator(ImportLandOperator.bl_idname, text=".land Heightmap (.land)")

def register():
    bpy.utils.register_class(ImportLandOperator)
    bpy.types.TOPBAR_MT_file_import.append(menu_func_import)

def unregister():
    bpy.utils.unregister_class(ImportLandOperator)
    bpy.types.TOPBAR_MT_file_import.remove(menu_func_import)

if __name__ == "__main__":
    register()