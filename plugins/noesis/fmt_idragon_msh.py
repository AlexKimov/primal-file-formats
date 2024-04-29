from inc_noesis import *
import os
import noewin
import noewinext


ANIM_EVAL_FRAMERATE = 20.0
IDRAGON_MODEL_TYPE = 0
BESIEGER_MODEL_TYPE = 1
IDRAGON_ANIMATION_TYPE = 3
BESIEGER_ANIMATION_TYPE = 4
BESIEGER_MAGIC_NUMBER = 537068291
BESIEGER_ANIMATION_MAGIC_NUMBER = 537068832


def registerNoesisTypes():
    handle = noesis.register( \
        "I of the Dragon (2002)/BESIEGER (2004) model with animations", ".msh")
        
    noesis.addOption(handle, "-nogui", "disables UI", 0) 
    
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
        

class PRBone: 
    def __init__(self, type):
        self.type = type
        self.parentIndex = 0
        self.matrix = Matrix4x4()
        self.matrix2 = Matrix4x4()
        self.name = ""
        self.transMatrix = None
        
    def read(self, reader): 
        if self.type == IDRAGON_MODEL_TYPE:    
            self.parentIndex = struct.unpack('i', reader.read(4))[0]  
            self.matrix.read(reader)
            self.matrix2.read(reader)
            self.name = CString().read(reader)
        else:
            self.name = CString().read(reader)         
            self.parentIndex = struct.unpack('i', reader.read(4))[0]  
            self.matrix.read(reader)
            self.matrix2.read(reader)                   

    def getTransMat(self):
        mat = NoeMat44()
        mat[0] = NoeVec4(self.matrix2.getStorage()[0])
        mat[1] = NoeVec4(self.matrix2.getStorage()[1])
        mat[2] = NoeVec4(self.matrix2.getStorage()[2])
        mat[3] = self.matrix2.getStorage()[3]

        return mat.toMat43()
    
    
class PRMesh: 
    def __init__(self, type):
        self.modelType = type
        self.textureName = ""
        self.vertexStartIndex = 0 
        self.vertexNum = 0
        self.faceStartIndex = 0 
        self.faceVertexNum = 0
        self.faceNum = 0
        self.boneIndexNum = 0
        self.boneIndexes = []
        
    def read(self, reader):   
        reader.seek(4, NOESEEK_REL)
        if self.modelType == IDRAGON_MODEL_TYPE:
            self.type, self.vertexStartIndex, self.vertexNum, self.faceStartIndex, self.faceVertexNum, self.faceNum = \
                struct.unpack('=6I', reader.read(24)) 
            self.boneIndexes = struct.unpack('=4i', reader.read(16)) 
        else:
            self.vertexNum = reader.readUInt()
            self.faceNum = int(reader.readUInt())
        
        self.textureName = CString().read(reader)

        if self.modelType != IDRAGON_MODEL_TYPE:        
            self.boneIndexNum = reader.readUInt()        
            self.boneIndexes = struct.unpack('H'*self.boneIndexNum, reader.read(self.boneIndexNum*2)) 
            

class PRSVertex: 
    def __init__(self, type):
        self.type = type
        self.coordinates = Vector3F()
        self.weights = Vector3F() if self.type == IDRAGON_MODEL_TYPE else [0]*4
        self.normal = Vector3F()        
        self.boneIndexes = [0]*4       
        self.uv = Vector2F()
        
    def read(self, reader):
        self.coordinates.read(reader)       
        if self.type == IDRAGON_MODEL_TYPE: 
            self.weights.read(reader)        
            self.normal.read(reader)
            self.uv.read(reader)
        else:
            weight = reader.readFloat();
            self.weights = [weight]*4;
            if weight != 1:
                self.weights[1] = 1 - weight;
            self.boneIndexes = struct.unpack('4B', reader.readBytes(4))
            self.normal.read(reader)     
            self.uv.read(reader)
   
   
class PRSModelBoneAnimationFrames:  
    def __init__(self, reader, type):
        self.type = type     
        self.reader = reader
        self.time = 0
        self.matrix = Matrix4x4()
        self.rotation = Vector4F()
        self.position = Vector3F()
        
    def read(self):
        if self.type == BESIEGER_ANIMATION_TYPE:
            self.rotation.read(self.reader)
            self.position.read(self.reader)
        else:
            self.time = self.reader.readFloat()  
            self.matrix.read(self.reader)
            self.reader.seek(44, NOESEEK_REL)


class PRSModelBoneAnimation:  
    def __init__(self, reader, type):
        self.type = type    
        self.reader = reader
        self.parentIndex = -1
        self.num = 0
        self.frames = []
        self.boneName = ""
        self.parentName = ""
      
    def readHeader(self):   
        if self.type == BESIEGER_ANIMATION_TYPE:
            self.boneName = CString().read(self.reader) 
            self.parentIndex = self.reader.readInt() 
            self.reader.seek(4, NOESEEK_REL)
            self.num = self.reader.readUInt() 
        else:
            self.reader.seek(8, NOESEEK_REL)  
            self.num = self.reader.readUInt()      
            self.boneName = CString().read(self.reader)  
            self.parentName = CString().read(self.reader)      
      
    def readFrames(self):   
        for i in range(self.num):
            boneFrames = PRSModelBoneAnimationFrames(self.reader, self.type)
            boneFrames.read()
            self.frames.append(boneFrames)           
        
    def read(self):
        self.readHeader()
        self.readFrames()
        
     
class PRSModelAnimations:
    def __init__(self):
        self.reader = None
        self.boneAnimations = []
        self.num = 0
        self.time = 0
        self.filename = ""
        self.type = -1
        
    def readHeader(self):
        self.type = BESIEGER_ANIMATION_TYPE if self.reader.readUInt() == BESIEGER_ANIMATION_MAGIC_NUMBER \
            else IDRAGON_ANIMATION_TYPE
            
        if self.type == BESIEGER_ANIMATION_TYPE:
            self.time = self.reader.readUInt()        
            self.num = self.reader.readUInt()        
        else:         
            self.reader.seek(20, NOESEEK_ABS)
            self.num = self.reader.readUInt()
            self.time = self.reader.readUInt()
            self.reader.seek(52, NOESEEK_ABS)
            
    def readBonesAnimationFrames(self):
        for i in range(self.num):
            boneAnims = PRSModelBoneAnimation(self.reader, self.type)
            boneAnims.read()
            self.boneAnimations.append(boneAnims)            

    def load(self, filename): 
        with open(filename, "rb") as filereader:
            self.reader = NoeBitStream(filereader.read())           
            self.filename = filename 
          
            self.readHeader()  
            self.readBonesAnimationFrames()            
            

class PSModel: 
    def __init__(self, reader):
        self.type = 0
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
        if self.reader.readUInt() == BESIEGER_MAGIC_NUMBER:
            self.type = BESIEGER_MODEL_TYPE
            reader.seek(56, NOESEEK_ABS)
        else:
            self.type = IDRAGON_MODEL_TYPE
            reader.seek(24, NOESEEK_REL)
               
    def readGeometryData(self, reader):
        if self.type == BESIEGER_MODEL_TYPE:      
            self.vertexCount = reader.readUInt()
           
            for i in range(self.vertexCount):
                vertex = PRSVertex(self.type) 
                vertex.read(reader)
                self.vertexAttributes.append(vertex)  
    
            self.faceCount = int(reader.readUInt() / 3)
           
            for i in range(self.faceCount):
                face = Vector3UI16() 
                face.read(reader)
                self.faces.append(face)                 
        else:        
            self.faceCount = struct.unpack('I', reader.read(4))[0]
        
            reader.seek(48, os.SEEK_CUR)     
        
            self.vertexCount, self.faceIndexCount, self.matCount, self.boneCount = \
                struct.unpack('=IIII', reader.read(16))  
        
            reader.seek(12, os.SEEK_CUR)
        
            for i in range(self.vertexCount):
                vertex = PRSVertex(self.type) 
                vertex.read(reader)
                self.vertexAttributes.append(vertex)                     
        
            for i in range(self.faceCount):
                face = Vector3UI16() 
                face.read(reader)
                self.faces.append(face)     
            
    def readMeshes(self, reader): 
        if self.type == BESIEGER_MODEL_TYPE:

            self.matCount = self.reader.readUInt() 
        
        index1 = 0
        index2 = 0
      
        for i in range(self.matCount):        
            mesh = PRMesh(self.type) 
            mesh.read(reader)
            mesh.faceStartIndex = index1
            mesh.vertexStartIndex = index2
            self.meshes.append(mesh)        
            index1 += mesh.faceNum
            index2 += mesh.vertexNum

    def readSkeleton(self, reader): 
        if self.type == BESIEGER_MODEL_TYPE:
            self.boneCount = self.reader.readUInt() 
            
        for i in range(self.boneCount):
            bone = PRBone(self.type) 
            bone.read(reader)
            self.bones.append(bone)             
        
    def readModelData(self, reader):
        self.readGeometryData(reader)        
        self.readMeshes(reader)         
        self.readSkeleton(reader)        
        
    def read(self):
        self.readHeader(self.reader)         
        self.readModelData(self.reader)           


class PRSViewSettingsDialogWindow:
    def __init__(self):
        self.options = {"AnimationFile": "", "TextureFolder": ""}
        self.isCanceled = True
        self.animationListBox = None
        self.anmPathEditBox = None
        self.texturePathEditBox = None
        self.actorFileNameEditBox = None
        self.anmDir = ""
        
    def buttonGetAnimationListOnClick(self, noeWnd, controlId, wParam, lParam):  
        dir = self.anmPathEditBox.getText().strip()
        if dir != "":
            if os.path.isdir(dir):
                self.anmDir = dir
        else:
            dialog = noewinext.NoeUserOpenFolderDialog("Choose folder with animation files")
            self.anmDir = dialog.getOpenFolderName() 
            if self.anmDir:
                self.anmPathEditBox.setText(self.anmDir)
  
        for file in os.listdir(self.anmDir):
            if file.lower().endswith(".anm"):
                self.animationListBox.addString(file)
                     
        return True     
        
    def buttonGetTexturePathOnClick(self, noeWnd, controlId, wParam, lParam):
        dialog = noewinext.NoeUserOpenFolderDialog("Choose folder with texture files")
        self.texturePathEditBox.setText(dialog.getOpenFolderName())
        
        return True
        
    def buttonLoadOnClick(self, noeWnd, controlId, wParam, lParam):    
        filename = self.animationListBox.getStringForIndex(self.animationListBox.getSelectionIndex())
    
        if filename != None:
            self.options["AnimationFile"] = os.path.join(self.anmDir, filename) 
        
        dir = self.texturePathEditBox.getText()
        if os.path.isdir(dir):
            self.options["TextureFolder"] = self.texturePathEditBox.getText()
        
        self.isCanceled = False
        self.noeWnd.closeWindow()   

        return True

    def buttonCancelOnClick(self, noeWnd, controlId, wParam, lParam):
        self.isCanceled = True
        self.noeWnd.closeWindow()

        return True

    def create(self):
        self.noeWnd = noewin.NoeUserWindow("Load model", "openModelWindowClass", 610, 360)
        noeWindowRect = noewin.getNoesisWindowRect()

        if noeWindowRect:
            windowMargin = 100
            self.noeWnd.x = noeWindowRect[0] + windowMargin
            self.noeWnd.y = noeWindowRect[1] + windowMargin

        if self.noeWnd.createWindow():
            self.noeWnd.setFont("Arial", 14)

            self.noeWnd.createStatic("Path to texture folder", 5, 5, 300, 20)
            # 
            index = self.noeWnd.createEditBox(5, 24, 490, 20, "", None, True)
            self.texturePathEditBox = self.noeWnd.getControlByIndex(index)
            
            self.noeWnd.createButton("Open", 505, 22, 90, 22, self.buttonGetTexturePathOnClick)

            self.noeWnd.createStatic("Path to .anm files", 5, 50, 300, 20)
            # 
            index = self.noeWnd.createEditBox(5, 70, 490, 20, "", None, True)
            self.anmPathEditBox = self.noeWnd.getControlByIndex(index)
            
            self.noeWnd.createButton("Open/Load", 505, 68, 90, 22, self.buttonGetAnimationListOnClick)
            
            self.noeWnd.createStatic("Animations:", 5, 100, 80, 20)
            index = self.noeWnd.createListBox(5, 120, 490, 220)
            self.animationListBox = self.noeWnd.getControlByIndex(index)
            
            self.noeWnd.createButton("Load", 505, 265, 90, 30, self.buttonLoadOnClick)
            self.noeWnd.createButton("Cancel", 505, 300, 90, 30, self.buttonCancelOnClick)

            self.noeWnd.doModal()
              
  
def idModelCheckType(data):

    return 1     
    

def idModelLoadModel(data, mdlList):
    #noesis.logPopup()
    path = ""
    anmPath = ""
    
    if not noesis.optWasInvoked("-nogui"):
        dialogWindow = PRSViewSettingsDialogWindow()
        dialogWindow.create()
    
        if not dialogWindow.isCanceled:
            path = dialogWindow.options["TextureFolder"]
            anmPath = dialogWindow.options["AnimationFile"]
        
    model = PSModel(NoeBitStream(data))
    model.read()

    ctx = rapi.rpgCreateContext()

    #transMatrix = NoeMat43( ((1, 0, 0), (0, 0, 1), (0, 1, 0), (0, 0, 0)) ) 
    #rapi.rpgSetTransform(transMatrix)

    # load textures
    mats = []
    textures = [] 
 
    if path == "":
        path = os.path.dirname(noesis.getSelectedFile())       

    for index, mesh in enumerate(model.meshes): 
 
        matName = "{} {}".format("mat", index) 

        name, _ = os.path.splitext(os.path.join(path, mesh.textureName))

        filename = name + ".dds"
        if not os.path.isfile(filename):
            filename = name + ".tga"
                     
        mat = NoeMaterial(matName, filename)
        rapi.rpgSetMaterial(matName) 

        texture = rapi.loadExternalTex(filename)

        if texture is None:
            texture = NoeTexture(filename, 0, 0, bytearray())
        mats.append(mat) 
        textures.append(texture) 
             
        if model.type == BESIEGER_MODEL_TYPE: 
            mesh.faceNum = int(mesh.faceNum / 3)
            faceStartIndex = int(mesh.faceStartIndex / 3)
        else:
            faceStartIndex = mesh.faceStartIndex
   
        rapi.immBegin(noesis.RPGEO_TRIANGLE)
        bi = [bind for bind in mesh.boneIndexes if bind > -1]
      
        for face in model.faces[faceStartIndex: (faceStartIndex + mesh.faceNum)]:                             
            for i in range(3):
                vIndex = face.getStorage()[i]
                if model.type == BESIEGER_MODEL_TYPE:            
                    vIndex += mesh.vertexStartIndex                   
                rapi.immUV2(model.vertexAttributes[vIndex].uv.getStorage())  
                rapi.immNormal3(model.vertexAttributes[vIndex].normal.getStorage())  
                if model.type == BESIEGER_MODEL_TYPE:                    
                    bi = [mesh.boneIndexes[index] for index in model.vertexAttributes[vIndex].boneIndexes]                                 
                rapi.immBoneIndex(bi)
                if model.type == BESIEGER_MODEL_TYPE:
                    rapi.immBoneWeight(model.vertexAttributes[vIndex].weights)
                else:               
                    rapi.immBoneWeight(model.vertexAttributes[vIndex].weights.getStorage())               
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
    
    if anmPath:
        animation = PRSModelAnimations()
        animation.load(anmPath)
    
        if animation.filename:
            boneNames = [bone.name for bone in model.bones]
    
            for bone in animation.boneAnimations:      
                keyFramedBone = NoeKeyFramedBone(boneNames.index(bone.boneName))
                rkeys = []
                pkeys = []
                               
                for index, frame in enumerate(bone.frames): 
                    if animation.type == BESIEGER_ANIMATION_TYPE:
                        rkeys.append(NoeKeyFramedValue(index * 1.0 / ANIM_EVAL_FRAMERATE, NoeQuat(frame.rotation.getStorage()).toMat43(1).toQuat()))           
                        pkeys.append(NoeKeyFramedValue(index * 1.0 / ANIM_EVAL_FRAMERATE, NoeVec3(frame.position.getStorage())))                
                    else:          
                        rkeys.append(NoeKeyFramedValue(frame.time, frame.matrix.getRotationQuat()))           
                        pkeys.append(NoeKeyFramedValue(frame.time, NoeVec4(frame.matrix.getPosition()).toVec3()))

                keyFramedBone.setRotation(rkeys)          
                keyFramedBone.setTranslation(pkeys)

                kfBones.append(keyFramedBone) 

            anims.append(NoeKeyFramedAnim(animation.filename, bones, kfBones) ) 
            mdl.setAnims(anims)   
    
    mdl.setBones(bones)
   
    if mats:    
        mdl.setModelMaterials(NoeModelMaterials(textures, mats))  
        
    mdlList.append(mdl)
    
    rapi.setPreviewOption("setAngOfs", "0 180 0")
    #rapi.setPreviewOption("setAnimSpeed", "20.0")
	
    return 1        