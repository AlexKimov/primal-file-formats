from inc_noesis import *
import os


def registerNoesisTypes():
    handle = noesis.register("I of the Dragon (2002) / Besieger (2004) archive file", ".res")
    noesis.setHandlerExtractArc(handle, prsExtractRESFile)
    
    return 1
        
        
class PRSFileRec:
    def __init__(self):
        self.filename = ""
        self.size = 0
        self.offset = 0        
        
    def read(self, filereader):     
        self.filename = noeAsciiFromBytes(filereader.readBytes(length))
        self.offset = filereader.readUInt()       
        self.size = filereader.readUInt()
        
    
class PRSFile:    
    def __init__(self,  filename = "", data = None):
        self.filenem = filename
        self.data = data


class prsArchiveFile:  
    def __init__(self, filereader):
        self.reader = filereader
        self.fileRecs = []
    
    def readFileRecs(self):
        self.fileNum = self.reader.readUInt()  
        for _ in range(self.fileNum):
            rec = PRSFileRec(self.reader)
            rec.read()    
            self.fileRecs.append(rec)

    def decypherFileData(self, data):
        key =  [ord(char) for char in "GBDFYTNE"]
        data = data[2:]
        for index, byte in enumerate(data):
            data[index] = byte ^ key[index % 8]
            
        return data
        
    def getUnpackedFiles(self):        
        for rec in self.fileRecs:
            self.reader.seek(rec.offset, NOESEEK_ABS)
            data = self.reader.readBytes(rec.size)
            _, file_extension = os.path.splitext(rec.filename)
            extensions = (".fir", ".dat", ".city", ".dsc")
            if file_extension in extensions:
                data = self.decypherFileData(data)
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
