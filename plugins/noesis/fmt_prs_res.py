from inc_noesis import *
import noewin
import os


def registerNoesisTypes():
    handle = noesis.register("I of the Dragon (2002) / Besieger (2004) archive file", ".res")
    noesis.setHandlerExtractArc(handle, prsExtractRESFile)
    
    
    toolHandle = noesis.registerTool("Pack PRS Resource", prsResourcePackerToolMethod, \
        "Pack game resources.")

    return 1
        
        
class PRSArchivePacker:  
    def __init__(self):
        self.filename = "output.res"
        self.extensions = (".msh", ".anm", ".dds", ".tga", ".dat", ".ahu", ".psd")
     
    def packArchive(self, filepath):
        archiveName = "{}\{}".format(filepath, self.filename)          
        
        log = []
        filenames = []
        osize = 0
        length = 0
        for root, dirs, files in os.walk(filepath):
            for file in files:
                filename = os.path.join(root, file)
                if os.path.isfile(filename):
                    length += len(filename.replace(filepath + "\\", ''))
                    filenames.append(filename)
                    _, ext = os.path.splitext(filename)
                    
                    if ext.lower() in self.extensions:
                        log.append("Added: {}.".format(filename))
                    else:
                        log.append("Added (other extension): {}.".format(filename))                   
         
        if filenames: 
            filelist = []
            length += 12 * len(filenames) + 4
            padding2 = 0 if length%16 == 0 else (16 - length%16)
            print(length)            
      
            for filename in filenames:
                size = os.path.getsize(filename)
                offset = padding2 + length + osize
                relpath = filename.replace(filepath + "\\", '')
                padding = 0 if size%16 == 0 else (16 - size%16)
                filelist.append(PRSFileRec(filename, relpath, size, offset, padding))
                osize += size + padding
            
            with open(archiveName, "wb") as archiveFile:     
                archiveFile.seek(0)            
                warningNum = 0 
            
                log.append("Created archive file: {}.".format(archiveName))
                archiveFile.write(len(filelist).to_bytes(4, "little"))
                           
                for file in filelist:                        
                    try:                         
                        archiveFile.write(file.toBytes())                       
                    except:                     
                        log.append("Can't write {} file.".format(file.filename))  
                        
                        return log
                        
                archiveFile.write(bytes(padding2))    
                        
                for file in filelist:                        
                    try:                         
                        with open(file.filename, "rb") as prsFile:                           
                            archiveFile.write(prsFile.read() + bytes(file.padding))
                            
                    except:                     
                        warningNum += 1
                        log.append("Can't open {} .".format(file.filename))                         
                        
                if warningNum == 0:
                    log.append("Done.".format(archiveName))                   
                else:
                    log.append("There are {} problem files.".format(warningNum)) 
        else:
            log.append("No files found.")
            
        return log
        
        
class PRSArchivePackerDialogWindow:
    def __init__(self):
        self.packer = PRSArchivePacker()

    def archivePackerButtonPack(self, noeWnd, controlId, wParam, lParam):
        output = ""
        for line in self.packer.packArchive(self.pathEdit.getText()):
            output += "{}\r\n".format(line)
        # self.outputEdit.setText("")    
        self.outputEdit.setText(output)         
        
        return True  
        
    def archivePackerButtonCancel(self, noeWnd, controlId, wParam, lParam):
        self.noeWnd.closeWindow()
         
        return True    
    
    def create(self):   
        self.noeWnd = noewin.NoeUserWindow( \
            "Primal Software archive packer (.res)", "PRSPackerWindowClass", \
            620, 255) 
        noeWindowRect = noewin.getNoesisWindowRect()
        
        if noeWindowRect:
            windowMargin = 100
            self.noeWnd.x = noeWindowRect[0] + windowMargin
            self.noeWnd.y = noeWindowRect[1] + windowMargin   
            
        if self.noeWnd.createWindow():
            self.noeWnd.setFont("Arial", 12)    
            
            self.noeWnd.createStatic("File path:", 5, 5, 50, 20)
            self.noeWnd.createStatic("Files:", 5, 35, 50, 20)
            #            
            index = self.noeWnd.createEditBox(60, 5, 550, 20, "", None, \
                False, False)
            self.pathEdit = self.noeWnd.getControlByIndex(index)
            
            #            
            index = self.noeWnd.createEditBox(60, 35, 550, 150, "")
            self.outputEdit = self.noeWnd.getControlByIndex(index)            
                     
            self.noeWnd.createButton("Pack archive", 60, 195, 80, 30, \
                 self.archivePackerButtonPack)
            self.noeWnd.createButton("Cancel", 530, 195, 80, 30, \
                 self.archivePackerButtonCancel)
            
            self.noeWnd.doModal()   
            
    
#see if the pvr reorder context tool should be visible
def prsArchivePackerVisible(toolIndex, selectedFile):
    
    
    return 1        
        
        
def prsResourcePackerToolMethod(toolIndex):
    # noesis.logPopup()
    main = PRSArchivePackerDialogWindow()
    main.create()       
        
    return 1 
    
        
class PRSFileRec:
    def __init__(self, filename, relpath, size, offset, padding):
        self.filename = filename
        self.relpath = relpath
        self.size = size
        self.offset = offset       
        self.padding = padding  
        
    def read(self, filereader):  
        length = filereader.readUInt()      
        self.filename = noeAsciiFromBytes(filereader.readBytes(length))
        self.offset = filereader.readUInt()       
        self.size = filereader.readUInt()
        
    def toBytes(self):
        data = bytes()
        data += len(self.relpath).to_bytes(4, byteorder='little')
        data += self.relpath.encode("ASCII")
        data += self.offset.to_bytes(4, byteorder='little')
        data += self.size.to_bytes(4, byteorder='little')
        
        return data
        
    
class PRSFile:    
    def __init__(self,  filename = "", data = None):
        self.filename = filename
        self.data = data


class PRSArchiveFile:  
    def __init__(self, filereader):
        self.reader = filereader
        self.fileRecs = []
    
    def readFileRecs(self):
        self.fileNum = self.reader.readUInt()  
        for _ in range(self.fileNum):
            rec = PRSFileRec()
            rec.read(self.reader)    
            self.fileRecs.append(rec)
        
    def getUnpackedFiles(self):        
        for rec in self.fileRecs:
            self.reader.seek(rec.offset, NOESEEK_ABS)
            data = self.reader.readBytes(rec.size)
            file = PRSFile(rec.filename, data)              
            yield file         
    
    def read(self):
        self.readFileRecs()
        
    
def prsExtractRESFile(fileName, fileLen, justChecking):
    with open(fileName, "rb") as f:
        if justChecking: #it's valid
            return 1       

        prsArchive = PRSArchiveFile(NoeBitStream(f.read()))
        prsArchive.read()

        for file in prsArchive.getUnpackedFiles():              
            rapi.exportArchiveFile(file.filename, file.data)
                        
    return 1
