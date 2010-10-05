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

    def PrintAll(self):
        print "mode: " + f.mode
        print "from:"  + f.fromfile  + " to: " + f.tofile
        self.PrintStats()
        
    def PrintStats(self):
        print "total:" + str(self.TotalChanges()) + " added: " + str(self.added) + " deleted: " + str(self.deleted) + "modifed: " + str(self.modified)
    
    def TotalChanges(self):
        return self.added + self.deleted + self.modified

class PatchStat:
    'PatchStat is the complete patch stat'
    fromref = ""
    toref = ""
    files = []
    file_stats = FileStat()
    newfiles = 0
    deletedfiles = 0
    modifiedfiles = 0

class LogEntry:
    author = ''
    committer = ''
    patch_stats = ''
    weekday = ''
    year  = ''
    month = ''
    day = ''
    order = 0 
    subject = ''
    parents = []
    tree_hash = ''
    commit_hash = ''
    
def ProcessLog(refStart, refEnd):
    log=[]
    p = subprocess.Popen(["git","log","--pretty=author:%ae%ncommitter:%ce%ndate:%aD%ncommit:%H%nparents:%P%nsubject:%s%n@@@@@@",ref1 + ".." + ref2],stdout=PIPE)
    for line in p.stdout:
        le = LogEntry()
        if(re.match("^author:)")):
            mo = re.match("^author:(.*)",line)
            le.author = mo.groups(1)[0]
        elif(re.match("^committer:)")):
            mo = re.match("^committer:(.*)",line)
            le.author = mo.groups(1)[0]
        elif(re.match("^date:)")):
            mo = re.match("^date:(.*)",line)
            le.date = mo.groups(1)[0]
            mo = re.match("^date:(.*), (d+) (.*) (d+)",line)
            le.weekday = mo.groups(1)[0]
            le.day = mo.gruops(2)[0]
            le.month = mo.groups(3)[0]
            le.year = mo.groups(4)[0]
        elif(re.match("^commit:)")):
            mo = re.match("^commit:(.*)",line)
            le.commit_hash = mo.groups(1)[0]
        elif(re.match("^parents:)")):
            mo = re.match("^parents:((.*) )*",line)
            le.parents = mo.groups(1)
        elif(re.match("^commit:)")):
            mo = re.match("^commit:(.*)",line)
            le.commit_hash = mo.groups(1)[0]
        elif(re.match("^subject:)")):
            mo = re.match("^subject:(.*)",line)
            le.subject = mo.groups(1)[0]
        elif(re.match("^@@@@)")):
            log.append(le)
            le = LogEntry()
    p.wait()
    
    return log
    
    
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



if __name__ == '__main__':
    p = subprocess.Popen(["git","log", "--first-parent","--pretty=%H", "--reverse", "HEAD"],stdout=subprocess.PIPE)
    startRef = ref1= p.stdout.readline().rstrip("\n")
    commits = []
    count = 0
    for line in p.stdout:
        if(count > 100):
            sys.stdout.write(".")
            sys.stdout.flush()
            count = 0
        count += 1
        ref2=line.rstrip("\n")
        patch = ProcessPatchCodeChurn(ref1,ref2)
        commits.append(patch)
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
    totalFile = FileStat()
    for p in commits:
        print p.fromref + ".." + p.toref
        for f in p.files:
            f.PrintAll()
            
            totalFile.AddFileStat(f)
            
            if(f.mode == "new"):
                files_new += 1
            elif (f.mode == "copy"):
                files_copied += 1
            elif (f.mode == "rename"):
                files_renamed += 1
            if(f.file_ext in file_ext_dict):
                file_ext_dict[f.file_ext].AddFileStat(f)
            else:
                file_ext_dict[f.file_ext] = f
    
    print "Totals"
    totalFile.PrintStats()
   
    print "files new    : " + str(files_new)
    print "files copied : " + str(files_copied)
    print "files renamed: " + str(files_renamed)
    print "By file extension"
    
    for key, value in file_ext_dict.iteritems():
        print "file ext:" + key 
        value.PrintStats()
            
   
    log = ProcessLog(startRef,endRef)
    for le in log:
        print "author: " + le.author
    
    print "done"

    


