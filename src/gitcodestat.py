#!/usr/bin/python

'''
Created on Oct 3, 2010

@author: greg
'''
from subprocess import PIPE
import subprocess;
import re;
import sys;
import os.path;


class FileStat:
    'FileStat is the files statistics'
    mode = 'modified'
    fromfile = ''
    tofile = ''
    added = 0 
    deleted = 0
    modified = 0
    file_ext = ''
    def AddFileStat(self,fs):
        self.added += fs.added
        self.deleted += fs.deleted
        self.modified += fs.modified
    def PrintStats(self):
        print "total:" + str(self.TotalChanges()) + " added: " + str(self.added) + " deleted: " + str(self.deleted) + "modifed: " + str(self.modified)
    def TotalChanges(self):
        return self.added + self.deleted + self.modified
class PatchStat:
    'PatchStat is the complete patch stat'
    fromref = ""
    toref = ""
    files = []
    
def ProcessChunk(file,chunkadd,chunkdel):
    if(chunkadd != 0 and chunkdel != 0):
        if(chunkadd > chunkdel):
            file.modified += chunkdel
            file.added += chunkadd - chunkdel
        else:
            file.modified += chunkadd
            file.deleted += chunkdel - chunkadd
    else:
        file.added += chunkadd
        file.deleted += chunkdel
 

def ProcessPatchCodeChurn(ref1, ref2):
    header = 1
    patch = PatchStat()
    patch.fromref = ref1
    patch.toref = ref2
    patch.files = []
    curFile = FileStat()
    chunk = 0
    chunkadd =0
    chunkdel =0
    p = subprocess.Popen(["git","diff","-M","-C","-p", "--find-copies-harder",ref1 + ".." + ref2],stdout=PIPE)
    for line in p.stdout:
        # process the header
        if(header == 1):
            if(re.match("^diff --git",line)):
                pass
            elif (re.match("^index",line)):
                pass
            elif (re.match("similarity index",line)):
                pass
            elif (re.match("^(rename|copy) from",line)):
                mo = re.match("^(rename|copy) from (.*)",line)
                curFile.mode = str(mo.groups(1)[0])
                curFile.fromfile = str(mo.groups(2)[1])
            elif (re.match("^(rename|copy) to",line)):
                mo = re.match("^(rename|copy) to (.*)",line)
                curFile.tofile = str(mo.groups(2)[1])
            elif (re.match("^new file mode",line)):
                curFile.mode = "new"    
            elif (re.match("^\+\+\+ (.*)",line)):
                mo = re.match("^\+\+\+ (.*)",line)
                curFile.tofile = str(mo.groups(1)[0])
            elif (re.match("^--- (.*)",line)):
                mo = re.match("^--- (.*)",line)
                curFile.fromfile = str(mo.groups(1)[0])
            elif (re.match("^(new|deleted) file mode",line)):
                mo = re.match("^(new|deleted) file mode",line)
                curFile.mode = str(mo.groups(1)[0])
            elif (re.match("^@@",line)):
                header = 0               
        else:
            # the chunks of the patch files need to be processed
            if(re.match("^-",line)):
                chunkdel += 1
                chunk = 1
            elif(re.match("^\+",line)):
                chunkadd += 1
                chunk = 1
            else:
                # process the chunk
                if(chunk == 1):
                    ProcessChunk(curFile,chunkadd,chunkdel);
                    chunkdel = chunkadd = chunk = 0
                
                if(re.match("^diff",line)):
                    # new file, store current file stats and process header
                    header = 1
                    curFile.file_ext = os.path.splitext(curFile.tofile)[1]
                    patch.files.append(curFile)
                    curFile = FileStat();
                
    # handle the last chunk for the last file
    ProcessChunk(curFile,chunkadd,chunkdel)
    curFile.file_ext = os.path.splitext(curFile.tofile)[1]
    patch.files.append(curFile)
                    
    return patch

def ProcessHistory(startRef,endRef):
    #p = subprocess.Popen(["git","log"])
    pass


if __name__ == '__main__':
    p = subprocess.Popen(["git","log", "--first-parent","--pretty=%H", "--reverse", "HEAD"],stdout=subprocess.PIPE)
    startRef =ref1= p.stdout.readline().rstrip("\n")
    churn = []
    commit_count = 0
    for line in p.stdout:
        if(commit_count % 100 == 0):
            sys.stdout.write(".")
            sys.stdout.flush()
        commit_count += 1
        ref2=line.rstrip("\n")
        patch = ProcessPatchCodeChurn(ref1,ref2)
        churn.append(patch)
        endRef= ref1 = ref2
    p.wait()
    
    added = 0
    deleted = 0
    modified = 0
    files_new = 0
    files_renamed = 0
    files_copied = 0
    num_commits = 0
    file_ext_dict  = dict()
    for p in churn:
        print p.fromref + ".." + p.toref
        for f in p.files:
            print "mode: " + f.mode
            print "from:"  + f.fromfile  + " to: " + f.tofile
            print "added: " + str(f.added) + " deleted: " + str(f.deleted) + " modifed: " + str(f.modified)
            added += f.added
            deleted += f.deleted
            modified += f.modified
            if(f.mode == "new"):
                files_new += 1
            elif (f.mode == "copy"):
                files_copied += 1
            elif (f.mode == "rename"):
                files_renamed += 1
            num_commits += 1
            if(f.file_ext in file_ext_dict):
                file_ext_dict[f.file_ext].AddFileStat(f)
            else:
                file_ext_dict[f.file_ext] = f
    
    print "Totals"
    print "lines added  : " + str(added)
    print "lines deleted: " + str(deleted)
    print "line modifed : " + str(modified) 
    print "files new    : " + str(files_new)
    print "files copied : " + str(files_copied)
    print "files renamed: " + str(files_renamed)
    print "By file extension"
    
    for key, value in file_ext_dict.iteritems():
        print "file ext:" + key 
        value.PrintStats()
            
    
    history = ProcessHistory(startRef,endRef)

    


