from inc_noesis import *
import os
import noewin
import noewinext
from pprint import pprint


IDRAGON_MODEL_TYPE = 0
IDRAGON_MODEL_TYPE_SHORT = 10
BESIEGER_MODEL_TYPE = 1
IDRAGON_ANIMATION_TYPE = 3
BESIEGER_ANIMATION_TYPE = 4
BESIEGER_MAGIC_NUMBER = 537068291
BESIEGER_ANIMATION_MAGIC_NUMBER = 537068832
IDRAGON_MAGIC_NUMBER2 = 536937233
SAMPLE_RATE = 30.0


def registerNoesisTypes():
    handle = noesis.register( \
        "I of the Dragon (2002)/BESIEGER (2004) model with animations", ".msh")
        
    noesis.addOption(handle, "-nogui", "disables UI", 0) 
    noesis.addOption(handle, "-noanimations", "no animations", 0) 
    noesis.addOption(handle, "-texturespath", "set path to textures folder", noesis.OPTFLAG_WANTARG) 
    noesis.addOption(handle, "-animationspath", "set path to animation files folder", noesis.OPTFLAG_WANTARG) 
    
    noesis.setHandlerTypeCheck(handle, idModelCheckType)
    noesis.setHandlerLoadModel(handle, idModelLoadModel)
    noesis.setHandlerWriteModel(handle, idModelWriteModel)
        
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


class Matrix4x3:
    def __init__(self):    
        self.x = Vector3F()
        self.y = Vector3F()
        self.z = Vector3F()
        self.pos = Vector3F()       
        
    def read(self, reader):
        self.x.read(reader)
        self.y.read(reader)
        self.z.read(reader)
        self.pos.read(reader)
        
    def getNoeMatrix(self):
        mat = NoeMat43()
        mat[0] = NoeVec3(self.x.getStorage())
        mat[1] = NoeVec3(self.y.getStorage())
        mat[2] = NoeVec3(self.z.getStorage())
        mat[3] = NoeVec3(self.pos.getStorage())

        return mat
        
    def getPosition(self): 
        return self.pos.getStorage()
        
    def getStorage(self):
        return (self.x.getStorage(), self.y.getStorage(), self.z.getStorage(), \
            self.pos.getStorage())   


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
        
    def getNoeMatrix(self):
        mat = NoeMat44()
        mat[0] = NoeVec4(self.x.getStorage())
        mat[1] = NoeVec4(self.y.getStorage())
        mat[2] = NoeVec4(self.z.getStorage())
        mat[3] = NoeVec4(self.pos.getStorage())

        return mat.toMat43()
        
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
        if self.type == BESIEGER_MODEL_TYPE:    
            self.name = CString().read(reader)         
            self.parentIndex = struct.unpack('i', reader.read(4))[0]  
            self.matrix.read(reader)
            self.matrix2.read(reader)
        else:
            self.parentIndex = struct.unpack('i', reader.read(4))[0]  
            self.matrix.read(reader)
            self.matrix2.read(reader)
            self.name = CString().read(reader)                 

    def getTransMat(self):
        return self.matrix.getNoeMatrix()
        
    def getTransMat2(self):
        return self.matrix2.getNoeMatrix()
        
    
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
        if self.modelType == BESIEGER_MODEL_TYPE:
            self.vertexNum = reader.readUInt()
            self.faceNum = int(reader.readUInt())        
        else:
            self.type, self.vertexStartIndex, self.vertexNum, self.faceStartIndex, self.faceVertexNum = \
                struct.unpack('=5I', reader.read(20))
            if self.modelType == IDRAGON_MODEL_TYPE: 
                self.faceNum = reader.readUInt()    
            self.boneIndexes = struct.unpack('=4i', reader.read(16)) 
              
        self.textureName = CString().read(reader)

        if self.modelType == BESIEGER_MODEL_TYPE:        
            self.boneIndexNum = reader.readUInt()        
            self.boneIndexes = struct.unpack('H'*self.boneIndexNum, reader.read(self.boneIndexNum*2)) 
            

class PRSVertex: 
    def __init__(self, type):
        self.type = type
        self.position = Vector3F()
        self.weights = [0]*4 if self.type == BESIEGER_MODEL_TYPE else Vector3F()
        self.normal = Vector3F()        
        self.boneIndexes = [0]*4       
        self.uv = Vector2F()
        
    def read(self, reader):
        self.position.read(reader)       
        if self.type == BESIEGER_MODEL_TYPE: 
            weight = reader.readFloat();
            self.weights = [weight]*4;
            if weight != 1:
                self.weights[1] = 1 - weight;
            self.boneIndexes = struct.unpack('4B', reader.readBytes(4))
            self.normal.read(reader)     
            self.uv.read(reader)
        else:
            self.weights.read(reader)        
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
    def __init__(self, reader, type, t):
        self.type = type    
        self.t = t    
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
            if self.t == 8:
                self.reader.seek(4, NOESEEK_REL)  
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
        
     
class PRSModelAnimationsFile:
    def __init__(self):
        self.reader = None
        self.boneAnimations = []
        self.num = 0
        self.time = 0
        self.filename = ""
        self.type = -1
        self.offset = 0
        self.t = 0
        
    def readHeader(self):
        self.offset = self.reader.readUInt()
        self.type = BESIEGER_ANIMATION_TYPE if self.offset == BESIEGER_ANIMATION_MAGIC_NUMBER \
            else IDRAGON_ANIMATION_TYPE
            
        if self.type == BESIEGER_ANIMATION_TYPE:
            self.time = self.reader.readUInt()        
            self.num = self.reader.readUInt()        
        else:
            self.reader.seek(4, NOESEEK_REL)         
            self.t = self.reader.readUInt()
            self.reader.seek(20, NOESEEK_ABS)
            self.num = self.reader.readUInt()
            self.time = self.reader.readUInt()            
            self.reader.seek(self.offset, NOESEEK_ABS)      
            
    def readBonesAnimationFrames(self):
        for i in range(self.num):
            boneAnims = PRSModelBoneAnimation(self.reader, self.type, self.t)
            boneAnims.read()
            self.boneAnimations.append(boneAnims)           

    def load(self, filename): 
        with open(filename, "rb") as filereader:
            self.reader = NoeBitStream(filereader.read())           
            self.filename = filename 
          
            self.readHeader()  
            self.readBonesAnimationFrames()            
            

class PSMeshFile: 
    def __init__(self, reader):
        self.type = 0
        self.reader = reader
        self.faceCount = 0
        self.vertexCount = 0
        self.faceIndexCount = 0
        self.boneCount = 0
        self.matCount = 0
        self.meshCount = 0
        self.vertexAttributes = []
        self.faces = []        
        self.meshes = []        
        self.bones = [] 
        self.name = ""      
        self.bbox = None      
        
    def readHeader(self, reader):
        offset = self.reader.readUInt()
        if offset == BESIEGER_MAGIC_NUMBER:
            self.type = BESIEGER_MODEL_TYPE
            reader.seek(56, NOESEEK_ABS)         
        else:
            magic = self.reader.readUInt()
            if magic != IDRAGON_MAGIC_NUMBER2:
                self.type = IDRAGON_MODEL_TYPE
                reader.seek(offset - 28 - 48, NOESEEK_ABS)
                self.bbox = Matrix4x3()
                self.bbox.read(reader)              
            else:
                self.type = IDRAGON_MODEL_TYPE_SHORT
                reader.seek(offset - 16, NOESEEK_ABS)  
                       
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
            self.vertexCount, self.faceIndexCount, self.meshCount, self.boneCount = \
                struct.unpack('=IIII', reader.read(16))  
            self.faceCount = int(self.faceIndexCount / 3)
        
            if self.type == IDRAGON_MODEL_TYPE:
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
            self.meshCount = self.reader.readUInt() 
        
        index1 = 0
        index2 = 0
      
        for i in range(self.meshCount):        
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
        self.options = {"AnimationFile": "", "TextureFolder": "", "AnimationsPath": "", "isLoadAllAnimations": False, "TransformCoordinates": False}
        self.isCanceled = True
        self.animationListBox = None
        self.anmPathEditBox = None
        self.texturePathEditBox = None
        self.actorFileNameEditBox = None
        self.animationsCheckBox = None
        self.transformCoordinatesCheckBox = None
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
  
        self.loadAnimationsListFromPath(self.anmDir)
                     
        return True     
        
    def buttonGetTexturePathOnClick(self, noeWnd, controlId, wParam, lParam):
        dialog = noewinext.NoeUserOpenFolderDialog("Choose folder with texture files")
        self.texturePathEditBox.setText(dialog.getOpenFolderName())
        
        return True
        
    def buttonLoadOnClick(self, noeWnd, controlId, wParam, lParam):
        self.options["isLoadAllAnimations"] = bool(self.animationsCheckBox.isChecked())
        self.options["TransformCoordinates"] = bool(self.transformCoordinatesCheckBox.isChecked())
        if not self.options["isLoadAllAnimations"]:    
            filename = self.animationListBox.getStringForIndex(self.animationListBox.getSelectionIndex())
    
            if filename is not None:
                self.options["AnimationFile"] = os.path.join(self.anmDir, filename) 
                self.options["AnimationsPath"] = self.anmDir
                            
        if os.path.isdir(self.texturePathEditBox.getText()):
            self.options["TextureFolder"] = self.texturePathEditBox.getText()
        
        self.isCanceled = False
        self.noeWnd.closeWindow()   

        return True

    def buttonCancelOnClick(self, noeWnd, controlId, wParam, lParam):
        self.isCanceled = True
        self.noeWnd.closeWindow()

        return True
        
    def loadAnimationsListFromPath(self, path):
        if path:
            for file in os.listdir(os.path.dirname(path)):
                if file.lower().endswith(".anm"):
                    self.animationListBox.addString(file)     

    def create(self):
        self.noeWnd = noewin.NoeUserWindow("Load model", "openModelWindowClass", 610, 375)
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
            # self.texturePathEditBox.setText("F:/git/primal/scripts/unpack_bsg/Textures.res")            
            
            self.noeWnd.createButton("Open", 505, 22, 90, 22, self.buttonGetTexturePathOnClick)

            self.noeWnd.createStatic("Path to .anm files", 5, 50, 300, 20)
            # 
            index = self.noeWnd.createEditBox(5, 70, 490, 20, "", None, True)
            self.anmPathEditBox = self.noeWnd.getControlByIndex(index)
            
            self.noeWnd.createButton("Open/Load", 505, 68, 90, 22, self.buttonGetAnimationListOnClick)
            
            self.noeWnd.createStatic("Animations:", 5, 100, 75, 20)
            index = self.noeWnd.createListBox(5, 120, 490, 195)
            self.animationListBox = self.noeWnd.getControlByIndex(index)
            
            index = self.noeWnd.createCheckBox("Load all animations", 5, 310, 150, 20)
            self.animationsCheckBox = self.noeWnd.getControlByIndex(index)
            self.animationsCheckBox.setChecked(1)
            
            index = self.noeWnd.createCheckBox("Transform coordinates", 5, 330, 200, 20)
            self.transformCoordinatesCheckBox = self.noeWnd.getControlByIndex(index)
            self.transformCoordinatesCheckBox.setChecked(1)            
            
            self.noeWnd.createButton("Load", 505, 280, 90, 30, self.buttonLoadOnClick)
            self.noeWnd.createButton("Cancel", 505, 315, 90, 30, self.buttonCancelOnClick)
            
            self.loadAnimationsListFromPath(noesis.getSelectedFile())           

            self.noeWnd.doModal()
       

def loadKeyFramedAnimation(file, boneNames, transMatrix, bones, options):
    keyFramedAnimation = None   

    animation = PRSModelAnimationsFile()
    animation.load(file)
    
    if animation.filename:
        kfBones = []            
        try:                          
            for bone in animation.boneAnimations:
                bindex = boneNames.index(bone.boneName)           
                keyFramedBone = NoeKeyFramedBone(bindex)
                rkeys = []
                pkeys = []
                   
                for index, frame in enumerate(bone.frames): 
                    if animation.type == BESIEGER_ANIMATION_TYPE:
                        matx = NoeQuat(frame.rotation.getStorage()).toMat43(1)
                        matx[3] = NoeVec3(frame.position.getStorage())
                    
                        #if bindex == 0:                            
                            #matx *= transMatrix
                        
                        rkeys.append(NoeKeyFramedValue(index * 1.0 / ANIM_EVAL_FRAMERATE, matx.toQuat()))           
                        pkeys.append(NoeKeyFramedValue(index * 1.0 / ANIM_EVAL_FRAMERATE, matx[3]))                
                    else: 
                        matx = frame.matrix.getNoeMatrix()
                        if options:
                            if transMatrix is not None and bindex == 0:                            
                                matx *= NoeMat43( ((0, 1, 0), (0, 0, 1), (1, 0, 0), (0, 0, 0)) )

                        rkeys.append(NoeKeyFramedValue(frame.time, matx.toQuat()))                                
                        pkeys.append(NoeKeyFramedValue(frame.time, matx[3]))
                        
                keyFramedBone.setRotation(rkeys)                       
                keyFramedBone.setTranslation(pkeys)
       

                kfBones.append(keyFramedBone)  
            keyFramedAnimation = NoeKeyFramedAnim(file, bones, kfBones, SAMPLE_RATE)
        except Exception as e: 
            print("error ", e)
            pass

                
    return keyFramedAnimation
    
    
def idModelCheckType(data):

    return 1     
    

def idModelLoadModel(data, mdlList):
    #print(noesis.getSelectedFile())
    noesis.logPopup()
    path = ""
    animationsFilePath = ""
    createAnimations = False
    loadAllAnimations = False
    transformCoordinates = False
    
    if not noesis.optWasInvoked("-nogui"):
        dialogWindow = PRSViewSettingsDialogWindow()
        dialogWindow.create()
    
        if not dialogWindow.isCanceled:
            path = dialogWindow.options["TextureFolder"]
            anmFile = dialogWindow.options["AnimationFile"]
            animationsFilePath = dialogWindow.options["AnimationsPath"]
            if not animationsFilePath:
                animationsFilePath = os.path.dirname(noesis.getSelectedFile())
            loadAllAnimations = dialogWindow.options["isLoadAllAnimations"]
            transformCoordinates = dialogWindow.options["TransformCoordinates"]
            if not loadAllAnimations and not anmFile:
                createAnimations = False
            else:
                createAnimations = True
    else:
        if noesis.optWasInvoked("-texturespath"):
            path = noesis.optGetArg("-texturespath")
            if not os.path.exists(path):
                path = ""
        if noesis.optWasInvoked("-animationspath"):
            animationsFilePath = noesis.optGetArg("-animationspath")
        if not animationsFilePath:
            animationsFilePath = os.path.dirname(noesis.getSelectedFile())
        
        createAnimations = False if noesis.optWasInvoked("-noanimations") else True       
        loadAllAnimations = True                   
        transformCoordinates = True
        
    meshFile = PSMeshFile(NoeBitStream(data))
    meshFile.read()

    ctx = rapi.rpgCreateContext()

    transMatrix = None 
    if transformCoordinates:
        transMatrix = NoeMat43( ((0, 1, 0), (0, 0, 1), (1, 0, 0), (0, 0, 0)) )
        #rapi.rpgSetOption(noesis.RPGOPT_TRIWINDBACKWARD, 1)
        rapi.rpgSetTransform(transMatrix)
    
    # load textures
    mats = []
    textures = [] 

    for index, mesh in enumerate(meshFile.meshes):
        rapi.rpgSetName("{} {}".format("Mesh: ", index))     
        matName = "{} {}".format("Material", index) 
        name, _ = os.path.splitext(os.path.join(path, mesh.textureName))

        filename = name 
        if not ".tga" in name:
            filename = name + ".dds"
            if not rapi.checkFileExists(filename):
                filename = name + ".tga"
                     
        mat = NoeMaterial(matName, filename)
        #mat.setFlags(noesis.NMATFLAG_TWOSIDED, 1)
        rapi.rpgSetMaterial(matName) 

        texture = rapi.loadExternalTex(filename)
        #print(filename)

        if texture is None:
            texture = NoeTexture(filename, 0, 0, bytearray())
            
        mats.append(mat) 
        
        textures.append(texture) 
             
        if meshFile.type == BESIEGER_MODEL_TYPE: 
            mesh.faceNum = int(mesh.faceNum / 3)
            faceStartIndex = int(mesh.faceStartIndex / 3)
        else:
            mesh.faceNum = int(mesh.faceVertexNum / 3)
            faceStartIndex = mesh.faceStartIndex

        bi = [bind for bind in mesh.boneIndexes if bind > -1]      
            
        rapi.immBegin(noesis.RPGEO_TRIANGLE) 
 
        for face in meshFile.faces[faceStartIndex: (faceStartIndex + mesh.faceNum)]:        
            for vIndex in face.getStorage():
                if meshFile.type == BESIEGER_MODEL_TYPE:            
                    vIndex += mesh.vertexStartIndex                    
                rapi.immUV2(meshFile.vertexAttributes[vIndex].uv.getStorage())  
                rapi.immNormal3(meshFile.vertexAttributes[vIndex].normal.getStorage())
                
                if meshFile.type == BESIEGER_MODEL_TYPE:                    
                    bi = [mesh.boneIndexes[index] for index in meshFile.vertexAttributes[vIndex].boneIndexes]   
                    
                rapi.immBoneIndex(bi)
                               
                if meshFile.type == BESIEGER_MODEL_TYPE:
                    rapi.immBoneWeight(meshFile.vertexAttributes[vIndex].weights)
                else:
                    if len(bi) == 1:
                        weights = [meshFile.vertexAttributes[vIndex].weights.getStorage()[0]]
                    elif len(bi) == 2: 
                        weights = meshFile.vertexAttributes[vIndex].weights.getStorage()[0:2]
                    else:
                        weights = list(meshFile.vertexAttributes[vIndex].weights.getStorage())
                        if weights[0] == 0:
                            weights[2] = 1 - weights[1]                                                                       
                    rapi.immBoneWeight(weights)                      
                rapi.immVertex3(meshFile.vertexAttributes[vIndex].position.getStorage())   
                      
        rapi.immEnd()

    # show skeleton
    bones = []
    for index, bone in enumerate(meshFile.bones):
        boneName = bone.name
        parentName = meshFile.bones[bone.parentIndex].name
        
        if transformCoordinates:
            bone.transMatrix = bone.getTransMat() * transMatrix
        else:
            bone.transMatrix = bone.getTransMat()
        
        if bone.parentIndex >= 0:         
            parentMat = meshFile.bones[bone.parentIndex].transMatrix                      
        else:
            parentName = ""            

        bones.append(NoeBone(index, boneName, bone.transMatrix, parentName, bone.parentIndex))   
       
    anims = []
    if createAnimations: 
        boneNames = [bone.name for bone in meshFile.bones]
        if loadAllAnimations:
            for file in os.listdir(animationsFilePath):           
                if file.lower().endswith(".anm"):
                    keyFramedAnimation = loadKeyFramedAnimation(os.path.join(animationsFilePath, file), boneNames, transMatrix, bones, transformCoordinates)
                    if keyFramedAnimation is not None:                    
                        anims.append(keyFramedAnimation)
        else:
            keyFramedAnimation = loadKeyFramedAnimation(os.path.join(animationsFilePath, anmFile), boneNames, transMatrix, bones, transformCoordinates)
            if keyFramedAnimation is not None:                         
                anims.append(keyFramedAnimation)
     
    #rapi.rpgOptimize() 
    mdl = rapi.rpgConstructModel()      
    mdl.setBones(bones)  
    if mats:    
        mdl.setModelMaterials(NoeModelMaterials(textures, mats))    
    
    mdl.setAnims(anims)        
    mdlList.append(mdl)

    #rapi.setPreviewOption("setAngOfs", "0 180 0")
    #rapi.setPreviewOption("setAnimSpeed", "20.0")
	
    return 1   


class mshFileHeader:
    def __init__(self, offset, magic, unk1, unk2, unk3, unk4, unk5, faceNum, bbox):
        self.offset = offset
        self.magic = magic
        self.unk1 = unk1
        self.unk2 = unk2
        self.unk3 = unk3
        self.unk4 = unk4
        self.unk5 = unk5
        self.faceNum = faceNum

    def toBytes(self):
        result = bytearray()
        result += self.offset.to_bytes(4, byteorder='little')
        result += self.magic.to_bytes(4, byteorder='little')
        result += self.unk1.to_bytes(4, byteorder='little')
        result += self.unk2.to_bytes(4, byteorder='little')
        result += self.unk3.to_bytes(4, byteorder='little')
        result += self.unk4.to_bytes(4, byteorder='little')
        result += self.unk5.to_bytes(4, byteorder='little')
        result += self.faceNum.to_bytes(4, byteorder='little')
        result += bytes(48)
        
        return result


class mshFileMesh:
    def __init__(self, data):
        self.data = data
        
    def toBytes(self):
        result = bytearray()
        result += self.data[0].to_bytes(4, byteorder='little')
        result += self.data[1].to_bytes(4, byteorder='little')
        result += self.data[2].to_bytes(4, byteorder='little')
        result += self.data[3].to_bytes(4, byteorder='little')
        result += self.data[4].to_bytes(4, byteorder='little')
        result += self.data[5].to_bytes(4, byteorder='little')
        result += self.data[6].to_bytes(4, byteorder='little')       
        result += struct.pack("{size}i".format(size = len(self.data[7])), *self.data[7])       
        result += len(self.data[8]).to_bytes(4, byteorder='little')
        result += self.data[8].encode(encoding='ASCII')
        
        return result        


class mshFileVertex:
    def __init__(self, data):
        self.data = data
        
    def toBytes(self):
        result = bytearray()
        for data in self.data:
            result += struct.pack("{size}f".format(size = len(data)), *data)
        
        return result
       
class mshFileIndex:
    def __init__(self, data):
        self.data = data
        
    def toBytes(self):
        result = bytearray()
        result += struct.pack("{size}H".format(size = len(self.data)), *self.data)

        return result
        
        
class mshFileBone:
    def __init__(self, data):
        self.data = data
        
    def toBytes(self):
        result = bytearray()
        result += self.data[0].to_bytes(4, byteorder='little', signed = True)
        
        for part in self.data[1]:
            result += struct.pack("{size}f".format(size = len(part)), *part)
            result += struct.pack("{size}f".format(size = len(part)), *part)
              
        result += len(self.data[2]).to_bytes(4, byteorder='little')
        result += self.data[2].encode(encoding='ASCII')
        
        return result

        
#write it
def idModelWriteModel(mdl, filewriter):     
    vertexes = []  
    indices = []
    meshes = [] 

    vertpos = 0
    facepos = 0   
    for mesh in mdl.meshes:     
        for index, vertex in enumerate(mesh.positions):
             
            weights = [0, 0, 0] 
            if len(mesh.weights[index].weights) == 1:
                weights[0] = mesh.weights[index].weights[0]
            elif len(mesh.weights[index].weights) == 2:    
                weights[0] = mesh.weights[index].weights[0] 
                weights[1] = mesh.weights[index].weights[1]
            else:
                weights = mesh.weights[index].weights           
            
            vrt = (vertex, weights, mesh.normals[index], mesh.uvs[index][0:2]) 
            vertexes.append(vrt)
        
        vnum = int(len(mesh.positions) / 3)
        fnum = int(len(mesh.indices) / 3)       
        indices.extend(mesh.indices)         

        windices = [-1, -1, -1, -1]
        type = 0        
        if len(mesh.weights[0].indices) == 1:
            windices[0] = mesh.weights[0].indices[0]
        elif len(mesh.weights[0].indices) == 2:    
            windices[0] = mesh.weights[0].indices[0] 
            windices[1] = mesh.weights[0].indices[1]
            type = 1
        else:
            windices[0] = mesh.weights[0].indices[0] 
            windices[1] = mesh.weights[0].indices[1]
            windices[3] = mesh.weights[0].indices[2]
            type = 2
                
        msh = (44, type, vertpos, vnum, facepos, len(mesh.indices), fnum, windices, mesh.matName)
        facepos += vnum * 3
        vertpos += vnum         
        meshes.append(msh)
     
    bones = []     
    for bone in mdl.bones:
        bn = (bone.parentIndex, bone.getMatrix(), bone.name)
        bones.append(bn) 
      
    filewriter.writeBytes(mshFileHeader(108, 536938242, 44, 2, 132, 0, 121, int(facepos / 3) ).toBytes())

    x = y = z = 0
    x1 = y1 = z1 = 100
    
    for vrt in vertexes:
        if vrt[0][0] > x: x = vrt[0][0] 
        if vrt[0][1] > y: y = vrt[0][1] 
        if vrt[0][2] > z: z = vrt[0][2] 

        if vrt[0][0] <= x1: x1 = vrt[0][0] 
        if vrt[0][1] <= y1: y1 = vrt[0][1] 
        if vrt[0][2] <= z1: z1 = vrt[0][2]
        
    print(x, y, z, x1, y1, z1)
    
    filewriter.writeInt(len(vertexes))
    filewriter.writeInt(len(indices))
    filewriter.writeInt(len(mdl.meshes))    
    filewriter.writeInt(len(mdl.bones))    
    filewriter.writeInt(0)    
    filewriter.writeInt(0)    
    filewriter.writeInt(0)     
    
  
    for vrt in vertexes:
        filewriter.writeBytes(mshFileVertex(vrt).toBytes())
        
    filewriter.writeBytes(mshFileIndex(indices).toBytes())         
    for msh in meshes:
        filewriter.writeBytes(mshFileMesh(msh).toBytes())
    for bn in bones:
        filewriter.writeBytes(mshFileBone(bn).toBytes())

    filewriter.writeInt(0)        
    filewriter.writeInt(0)        

    return 1
    