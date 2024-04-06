from inc_noesis import *
import os

ANIM_EVAL_FRAMERATE = 20.0


def registerNoesisTypes():
    handle = noesis.register( \
        "Eye of the Dragon (2002) model with animations", ".msh")
        
    noesis.setHandlerTypeCheck(handle, idModelCheckType)
    noesis.setHandlerLoadModel(handle, idModelLoadModel)
        
    return 1 
    
    
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
        
    def getRotationQuat(self):
        mat = NoeMat44()
        mat[0] = NoeVec4(self.x.getStorage())
        mat[1] = NoeVec4(self.y.getStorage())
        mat[2] = NoeVec4(self.z.getStorage())

        return mat.toMat43().toQuat() 
        
    def getPosition(self): 
        return self.pos.getStorage()
        
    def getStorage(self):
        return (self.x.getStorage(), self.y.getStorage(), self.z.getStorage(), \
            self.pos.getStorage())          
 

class CString: 
    def read(self, reader):
        len = struct.unpack('I', reader.read(4))[0]
        if len == 0:
            return ""
        else:        
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
        self.transMatrix = None
        
    def read(self, reader):  
        self.parentIndex = struct.unpack('i', reader.read(4))[0]  
        self.matrix.read(reader)
        self.matrix2.read(reader)
        self.name = CString().read(reader)             

    def getTransMat(self):
        mat = NoeMat44()
        mat[0] = NoeVec4(self.matrix2.getStorage()[0])
        mat[1] = NoeVec4(self.matrix2.getStorage()[1])
        mat[2] = NoeVec4(self.matrix2.getStorage()[2])
        mat[3] = self.matrix2.getStorage()[3]

        return mat.toMat43()
    
    
class IDMesh: 
    def __init__(self):
        self.textureName = ""
        self.vertexStartIndex = 0 
        self.vertexNum = 0
        self.faceStartIndex = 0 
        self.faceVertexNum = 0
        self.faceNum = 0
        self.boneIndex = 0
        self.type = 0
        self.boneIndexes = []
        
    def read(self, reader): 
        reader.seek(4, os.SEEK_CUR)
        
        self.type, self.vertexStartIndex, self.vertexNum, self.faceStartIndex, self.faceVertexNum, self.faceNum = \
            struct.unpack('=6I', reader.read(24)) 
        self.boneIndexes = struct.unpack('=4i', reader.read(16)) 
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
   
   
class IDModelBoneAnimationFrames:  
    def __init__(self, reader):  
        self.reader = reader
        self.time = 0
        self.matrix = Matrix4x4()
        
    def read(self):
        self.time = self.reader.readFloat()  
        self.matrix.read(self.reader)
        self.reader.seek(44, NOESEEK_REL)


class IDModelBoneAnimation:  
    def __init__(self, reader): 
        self.reader = reader
        self.num = 0
        self.frames = []
        self.boneName = ""
        self.parentName = ""
      
    def readHeader(self):
        self.reader.seek(8, NOESEEK_REL)  
        self.num = self.reader.readUInt()      
        self.boneName = CString().read(self.reader)  
        self.parentName = CString().read(self.reader)      
      
    def readFrames(self):   
        for i in range(self.num):
            boneFrames = IDModelBoneAnimationFrames(self.reader)
            boneFrames.read()
            self.frames.append(boneFrames)           
        
    def read(self):
        self.readHeader()
        self.readFrames()
        
     
class IDModelAnimations:
    def __init__(self):
        self.reader = None
        self.boneAnimations = []
        self.num = 0
        self.animationLength = 0
        self.filename = ""
        
    def readHeader(self):
        self.reader.seek(20, NOESEEK_ABS)
        self.num = self.reader.readUInt()
        self.animationLength = self.reader.readUInt()
        
    def readBonesAnimationFrames(self):
        self.reader.seek(52, NOESEEK_ABS)
        for i in range(self.num):
            boneAnims = IDModelBoneAnimation(self.reader)
            boneAnims.read()
            self.boneAnimations.append(boneAnims)   

    def load(self, filename): 
        with open(filename, "rb") as filereader:
            self.reader = NoeBitStream(filereader.read())           
            self.filename = filename 
          
        self.readHeader()  
        self.readBonesAnimationFrames()  
            

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
        self.meshes = []        
        self.bones = [] 
        self.name = ""      
        
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
            
    def readMeshes(self, reader): 
        for i in range(self.matCount):
            mesh = IDMesh() 
            mesh.read(reader)
            self.meshes.append(mesh)        

    def readSkeleton(self, reader): 
        for i in range(self.boneCount):
            bone = IDBone() 
            bone.read(reader)
            self.bones.append(bone)             
        
    def readModelData(self, reader):
        self.readGeometryData(reader)    
        self.readMeshes(reader)      
        self.readSkeleton(reader)        
        
    def read(self):
        self.readHeader(self.reader)         
        self.readModelData(self.reader)           
  
  
def idModelCheckType(data):

    return 1     
    

def idModelLoadModel(data, mdlList):
    noesis.logPopup()
    model = IDCharacterModel(NoeBitStream(data))
    model.read()
    
    ctx = rapi.rpgCreateContext()

    #transMatrix = NoeMat43( ((1, 0, 0), (0, 0, 1), (0, 1, 0), (0, 0, 0)) ) 
    #rapi.rpgSetTransform(transMatrix)

    # load textures
    mats = []
    textures = [] 
 
    path = os.path.dirname(noesis.getSelectedFile()) + "/"        

    for index, mesh in enumerate(model.meshes): 
        
        matName = "{} {}".format("mat", index)
        name, _ = os.path.splitext(path + mesh.textureName)
        filename = name + ".dds"
        if not os.path.isfile(filename):
            filename = name + ".tga"
            
        mat = NoeMaterial(matName, filename)
        rapi.rpgSetMaterial(matName) 
        # mat.setDiffuseColor(NoeVec4(mat.diffuse.getStorage()))
        # mat.setAmbientColor(NoeVec4(mat.ambient.getStorage()))
        # mat.setSpecularColor(NoeVec4(mat.specular.getStorage()))
        
        texture = rapi.loadExternalTex(filename)

        if texture is None:
            texture = NoeTexture(filename, 0, 0, bytearray())
        mats.append(mat) 
        textures.append(texture) 
        
        meshName = "{} {}".format("mesh", index)         
        rapi.rpgSetName(meshName)
            
        faceStartIndex = int(mesh.faceStartIndex / 3)
        for face in model.faces[faceStartIndex: (faceStartIndex + mesh.faceNum)]:               
            rapi.immBegin(noesis.RPGEO_TRIANGLE)
            for i in range(3):              
                vIndex = face.getStorage()[i] 
                rapi.immUV2(model.vertexAttributes[vIndex].uv.getStorage())  
                rapi.immNormal3(model.vertexAttributes[vIndex].normal.getStorage())  
                #rapi.immColor3(model.vertexAttributes[vIndex].color.getStorage())
                
                bi = []               
                bi = [bind for bind in mesh.boneIndexes if bind > -1]
                wh = [1/len(bi)]*len(bi)   
                
                rapi.immBoneIndex(bi)                
                rapi.immBoneWeight(wh)                     
                rapi.immVertex3(model.vertexAttributes[vIndex].coordinates.getStorage())   
            rapi.immEnd() 
                        
    
    # show skeleton
    bones = []
    for index, bone in enumerate(model.bones):
        boneName = bone.name
        
        if bone.parentIndex >= 0:
            parentMat = model.bones[bone.parentIndex].transMatrix
            boneMat = bone.getTransMat() * parentMat
            bone.transMatrix = boneMat
            
            parentName = model.bones[bone.parentIndex].name
            bones.append(NoeBone(index, boneName, boneMat, parentName, bone.parentIndex))             
        else:         
            bone.transMatrix = bone.getTransMat()
            boneMat = bone.transMatrix

            bones.append(NoeBone(index, boneName, boneMat, "", -1))

    anims = []
    kfBones = []

    mdl = rapi.rpgConstructModelSlim() 
    
    animation = IDModelAnimations()
    #animation.load("F:\git\primal\Geometry.res\Dragon\Dragon_Cast3.ANM")
    
    if animation.filename:
        boneNames = [bone.name for bone in model.bones]
    
        frameToTime = animation.animationLength * 1.0 / ANIM_EVAL_FRAMERATE
    
        for index, bone in enumerate(animation.boneAnimations): 
            keyFramedBone = NoeKeyFramedBone(boneNames.index(bone.boneName))
            rkeys = []
            pkeys = []
        
            for frame in bone.frames:         
                rkeys.append(NoeKeyFramedValue(frame.time, frame.matrix.getRotationQuat()))           
                pkeys.append(NoeKeyFramedValue(frame.time, NoeVec4(frame.matrix.getPosition()).toVec3()))

            keyFramedBone.setRotation(rkeys)          
            keyFramedBone.setTranslation(pkeys)

            kfBones.append(keyFramedBone) 

        anims.append(NoeKeyFramedAnim(animation.filename, bones, kfBones) ) 
        mdl.setAnims(anims)   

    mdl.setBones(bones)
    
    # set meshes
    if mats:    
        mdl.setModelMaterials(NoeModelMaterials(textures, mats))  
        
    mdlList.append(mdl)
    
    rapi.setPreviewOption("setAngOfs", "0 180 0")
    #rapi.setPreviewOption("setAnimSpeed", "20.0")
	
    return 1        