bl_info = {
    "name": "Import MSH (.msh)",
    "author": "",
    "version": (0, 1, 0),
    "blender": (2, 80, 0),
    "location": "File > Import > I of The Dragon MSH (.msh)",
    "description": "Import a file in the msh format",
    # "warning": "",
    # "wiki_url": "",
    # "tracker_url": "",
    "support": "COMMUNITY",
    "category": "Import-Export",
}

import bpy, bmesh
import mathutils
from bpy_extras.io_utils import ImportHelper

import os
import sys
import math
import struct
from pathlib import Path
from struct import calcsize, unpack


try:
    os.SEEK_SET
except AttributeError:
    os.SEEK_SET, os.SEEK_CUR, os.SEEK_END = range(3)


class StdOutOverride:
    buffer = []
    def write(self, text):
        sys.__stdout__.write(text)
        
        if text == '\n':
            self.print_to_console()

        else:
            for line in text.replace('\t', '    ').split('\n'):
                if len(self.buffer) > 0:
                    self.print_to_console()
                self.buffer.append(line)
    def print_to_console(self):
        buffer_str = ''.join(map(str, self.buffer))
        if hasattr(bpy.context, 'screen') and bpy.context.screen:
            for area in bpy.context.screen.areas:
                if area.type == 'CONSOLE':
                    with bpy.context.temp_override(area=area):
                        try:
                            bpy.ops.console.scrollback_append(text=buffer_str, type='OUTPUT')
                        except Exception as ex:
                            pass
        self.buffer = []


sys.stdout = StdOutOverride() 
 
 
def bytestoString(str):
   filtered = bytearray([x if x < 0x80 else 0x2D for x in str])
   return str(filtered, "ASCII").rstrip("\0")    
 
 
class Vector3UI16:
    def __init__(self, x = 0, y = 0, z = 0):    
        self.x = x
        self.y = y
        self.z = z
        
    def read(self, reader):
        self.x, self.y, self.z = struct.unpack('=HHH', reader.read(6)) 
        
    def getStorage(self):
        return (self.x, self.y, self.z)    
        
    
class Vector3F:
    def __init__(self, x = 0, y = 0, z = 0):    
        self.x = x
        self.y = y
        self.z = z
        
    def read(self, reader):
        self.x, self.y, self.z = struct.unpack('3f', reader.read(12))  
        
    def getStorage(self):
        return (self.x, self.y, self.z)     
   
   
class Vector4F:
    def __init__(self, x = 0, y = 0, z = 0, w = 0):    
        self.x = x
        self.y = y
        self.z = z
        self.z = w        
        
    def read(self, reader):
        self.x, self.y, self.z, self.w = struct.unpack('4f', reader.read(16))  
        
    def getStorage(self):
        return (self.x, self.y, self.z, self.w)    


class Matrix4x4:
    def __init__(self):    
        self.x = Vector4F()
        self.y = Vector4F()
        self.z = Vector4F()
        self.pos = Vector4F()       
        
    def read(self, reader):
        self.x.read(reader)
        self.y.read(reader)
        self.z.read(reader)
        self.pos.read(reader)
        
    def getStorage(self):
        return (self.x.getStorage(), self.y.getStorage(), self.z.getStorage(), \
            self.pos.getStorage())          
 

class CString: 
    def read(self, reader):
        len = struct.unpack('I', reader.read(4))[0]        
        nstr = reader.read(len)        
        filtered = bytearray([x if x < 0x80 else 0x2D for x in nstr])
        return str(filtered, "ASCII").rstrip("\0")    
    
    
class Vector4I:
    def __init__(self):    
        self.i1 = 0
        self.i2 = 0
        self.i3 = 0
        self.i4 = 0        
        
    def toFloat(self, value):
        return value/255 if value >= 0 else 1    
        
    def read(self, reader):
        data = struct.unpack('=4i', reader.read(16))
                         
        self.i1 = self.toFloat(data[0])
        self.i2 = self.toFloat(data[1])
        self.i3 = self.toFloat(data[2])
        self.i4 = self.toFloat(data[3])
        
    def getStorage(self):
        return (self.i1, self.i2, self.i3, self.i4)            
    
    
class Vector3UI:
    def __init__(self):    
        self.i1 = 0
        self.i2 = 0
        self.i3 = 0
        
    def read(self, reader):
        self.i1, self.i2, self.i3 = struct.unpack('=3I', reader.read(12))
        
    def getStorage(self):
        return (self.i1, self.i2, self.i3)     
   
   
class Vector2F:
    def __init__(self):    
        self.x = 0
        self.y = 0
        
    def read(self, reader):
        self.x, self.y = struct.unpack('2f', reader.read(8))  
        
    def getStorage(self):
        return (self.x, self.y)  
        

class IDBone: 
    def __init__(self):
        self.parentIndex = 0
        self.matrix = Matrix4x4()
        self.matrix2 = Matrix4x4()
        self.name = ""
        
    def read(self, reader):  
        self.parentIndex = struct.unpack('i', reader.read(4))[0]  
        self.matrix.read(reader)
        self.matrix2.read(reader)
        self.name = CString().read(reader)             
    
    
class IDMaterial: 
    def __init__(self):
        self.textureName = ""
        self.vertexIndex = 0 
        self.vertexCount = 0
        self.matVertexIndex = 0 
        self.matVertexCount = 0
        self.matFaceCount = 0
        self.color = Vector4I()
        
    def read(self, reader): 
        reader.seek(8, os.SEEK_CUR)
        self.vertexIndex, self.vertexCount, self.matVertexIndex, self.matVertexCount, self.matFaceCount = \
            struct.unpack('=5I', reader.read(20)) 
        self.color.read(reader)
        self.textureName = CString().read(reader)  
        

class IDVertex: 
    def __init__(self):
        self.coordinates = Vector3F()
        self.normal = Vector3F()
        self.color = Vector3F()        
        self.uv = Vector2F()
        
    def read(self, reader):
        self.coordinates.read(reader)
        self.normal.read(reader)
        self.color.read(reader)
        self.uv.read(reader)            
   

class IDCharacterModel: 
    def __init__(self, reader):
        self.reader = reader
        self.faceCount = 0
        self.vertexCount = 0
        self.faceIndexCount = 0
        self.boneCount = 0
        self.matCount = 0
        self.vertexAttributes = []
        self.faces = []        
        self.materials = []        
        self.bones = [] 
        self.name = "" 
        # self.textures= None        
        
    def readHeader(self, reader):
        reader.seek(28, os.SEEK_CUR)
               
    def readGeometryData(self, reader):
        self.faceCount = struct.unpack('I', reader.read(4))[0]
        
        reader.seek(48, os.SEEK_CUR)     
        
        self.vertexCount, self.faceIndexCount, self.matCount, self.boneCount = \
            struct.unpack('=IIII', reader.read(16))  
        
        reader.seek(12, os.SEEK_CUR)
        
        for i in range(self.vertexCount):
            vertex = IDVertex() 
            vertex.read(reader)
            self.vertexAttributes.append(vertex)   
        
        for i in range(self.faceCount):
            face = Vector3UI16() 
            face.read(reader)
            self.faces.append(face)     
            
    def readMaterials(self, reader): 
        for i in range(self.matCount):
            mat = IDMaterial() 
            mat.read(reader)
            self.materials.append(mat)

        # self.textures = tuple(set([mat.name for mat in self.materials]))           

    def readSkeleton(self, reader): 
        for i in range(self.boneCount):
            bone = IDBone() 
            bone.read(reader)
            self.bones.append(bone)             
        
    def readModelData(self, reader):
        self.readGeometryData(reader)    
        self.readMaterials(reader)      
        self.readSkeleton(reader)        
        
    def read(self):
        self.readHeader(self.reader)         
        self.readModelData(self.reader)          


def load_msh_file(msh_filename, context, dir, BATCH_LOAD=False):
    fhandle = open(msh_filename, "rb")
    
    model = IDCharacterModel(fhandle)
    model.read()   
    
    fhandle.close()
    
    collection = None
    bm = bmesh.new() 
  
    for vertex in model.vertexAttributes:
        bm.verts.new(vertex.coordinates.getStorage())
        bm.verts.ensure_lookup_table()
    
    faces = []    
    for faceIndexes in model.faces:                                  
        face = [bm.verts[i] for i in faceIndexes.getStorage()]
        bm.faces.new(face)
        bm.faces.ensure_lookup_table()
        faces.append(face)
 
    # create materials and add uvs
    uv_layer = bm.loops.layers.uv.verify()
     
    mats = []
    for idx, mat in enumerate(model.materials):
        # material
        nmat = bpy.data.materials.new("Material %d" % idx)
        nmat.diffuse_color = mat.color.getStorage()
        mats.append(nmat)
        nmat.use_nodes = True        
        bsdf = nmat.node_tree.nodes["Principled BSDF"]
        
        mapping_node = nmat.node_tree.nodes.new('ShaderNodeMapping')
        mapping_node.inputs["Rotation"].default_value = (-3.14159, 0, 0)

        tex_coord_node = nmat.node_tree.nodes.new('ShaderNodeTexCoord')
        nmat.node_tree.links.new(mapping_node.inputs['Vector'], \
            tex_coord_node.outputs['UV'])    
            
        # texture
        tex_node = nmat.node_tree.nodes.new('ShaderNodeTexImage')

        dir = os.path.dirname(os.path.abspath(msh_filename))
        
        fname = None
        
        filname = dir + mat.textureName
        path = Path(filname)
        if path.is_file():
           fname = dir + mat.textureName

        else:
            filname = dir + os.path.splitext(mat.textureName)[0] + ".dds"
            path = Path(filname)
            if path.is_file():
               fname = filname
           
        if fname:
            tex_node.image = bpy.data.images.load(fname) 
            
        nmat.node_tree.links.new(tex_node.inputs['Vector'], mapping_node.outputs['Vector'])    
        nmat.node_tree.links.new(bsdf.inputs['Base Color'], tex_node.outputs['Color'])                       
        faceIndex = int(mat.matVertexIndex / 3)
        faceIndexRange = range(faceIndex, faceIndex + mat.matFaceCount, 1) 
        
        for faceIndex in faceIndexRange:
            bm.faces[faceIndex].material_index = idx
            for i, loop in enumerate(bm.faces[faceIndex].loops):
                loop_uv = loop[uv_layer]

                index = model.faces[faceIndex].getStorage()[i]
                loop_uv.uv = model.vertexAttributes[index].uv.getStorage()         
     
    name = os.path.splitext(msh_filename)[0]    
    mesh = bpy.data.meshes.new(name)
    bm.to_mesh(mesh)
    ob = bpy.data.objects.new(name, mesh)
    
    for mat in mats:
       ob.data.materials.append(mat)
              
    try:
        collection = collection or bpy.context.scene.collection
        collection.objects.link(ob)       
    except AttributeError:
        bpy.context.scene.objects.link(ob)    
    try:
        bpy.context.scene.update()
    except AttributeError:
        pass
        
    # bones
    # skeleton = bpy.data.armatures.new("armature")
    # skeleton.display_type = 'STICK'    
    # obj = bpy.data.objects.new("skeleton", skeleton)        
    # bpy.context.scene.collection.objects.link(obj)    
    # bpy.context.view_layer.objects.active = obj
    
    # bpy.ops.object.mode_set(mode = 'EDIT', toggle = False)
    
    # for bone in model.bones:
        # nbone = skeleton.edit_bones.new(bone.name) 
        # nbone.tail = (0, 0, 1)        

        # if bone.parentIndex >= 0:     
            # matrx = mathutils.Matrix(bone.matrix.getStorage())
            # parent_matrx = mathutils.Matrix(skeleton.edit_bones[bone.parentIndex].matrix) 
            # nbone.matrix = matrx * parent_matrx 
            # nbone.parent = skeleton.edit_bones[bone.parentIndex]
        # else:
            # nbone.matrix = bone.matrix.getStorage()  

    # bpy.ops.object.mode_set(mode = 'OBJECT', toggle = False)         

    polygons = ob.data.polygons
    polygons.foreach_set('use_smooth', [True] * len(polygons))  
    
    return
        

class ImportMSH(bpy.types.Operator, ImportHelper):
    bl_idname = "import_scene.msh"  
    bl_label = "Import msh"
    bl_options = {"UNDO"}

    filter_glob : bpy.props.StringProperty(
        default = "*.msh",
        options = {"HIDDEN"},
    ) 
    
    textures_path : bpy.props.StringProperty(
        name = "Path: ",
        description = "Choose path to textures",
        default = "",
        maxlen = 1024,
        subtype = 'FILE_NAME'
    )
      
    def execute(self, context):
        if context.mode != "OBJECT":
            if not context.scene.objects.active:
                context.scene.objects.active = context.scene.objects[0]
            bpy.ops.object.mode_set(mode="OBJECT")
        bpy.ops.object.select_all(action="DESELECT")
        
        load_msh_file(self.filepath, context, self.textures_path)
        
        bpy.ops.object.select_all(action="DESELECT")
        return {"FINISHED"}


# Only needed if you want to add into a dynamic menu
def menu_func_import(self, context):
    self.layout.operator(ImportMSH.bl_idname, text="Import I of The Dragon MSH (.msh)")


def register():
    bpy.utils.register_class(ImportMSH)
    try:
        bpy.types.TOPBAR_MT_file_import.append(menu_func_import)
    except AttributeError:
        bpy.types.INFO_MT_file_import.append(menu_func_import)


def unregister():
    bpy.utils.unregister_class(ImportMSH)
    try:
        bpy.types.TOPBAR_MT_file_import.remove(menu_func_import)
    except AttributeError:
        bpy.types.INFO_MT_file_import.remove(menu_func_import)


if __name__ == "__main__":
    register()