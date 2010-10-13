#!/usr/bin/python

'''
Created on Oct 3, 2010

@author: greg
'''
from subprocess import PIPE
import subprocess
import re
import sys
import os.path
import json




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
        print "total:" + str(self.TotalChanges()) + " added: " + str(self.added) + " deleted: " + str(self.deleted) + " modified: " + str(self.modified)
    
    def TotalChanges(self):
        return self.added + self.deleted + self.modified
    
    def default(self,my_class):
        if not isinstance(my_class, FileStat):
            print "You cnann't use the JSON custom MyClassEncoder"
            return
        return {'mode': my_class.mode, 'fromfile' : my_class.fromfile, 'tofile' : my_class.tofile , 'added': my_class.added, 
                'deleted' : my_class.deleted, 'modified' : my_class.modified, 'file_ext' : my_class.file_ext }


class MyEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj,FileStat):
            return obj.default(obj)
        elif isinstance(obj,LogEntry):
            return obj.default(obj)
        elif isinstance(obj,PatchStat):
            return obj.default(obj)
        else:
            return json.JSONEncoder.default(self,obj)

class PatchStat:
    'PatchStat is the complete patch stat'
    fromref = ""
    toref = ""
    files = []
    file_stats = FileStat()
    newfiles = 0
    deletedfiles = 0
    modifiedfiles = 0
    def default(self,obj):
        return {'fromref' : obj.fromref, 'toref' : obj.toref, 'files' : obj.files, 'file_stats' : obj.file_stats,
                'newfiles' : obj.newfiles, 'deletedfiles' : obj.deletedfiles, 'modifiedfiles' : obj.modifiedfiles }

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
    def default(self,obj):
        return {'author' : obj.author , 'committer' : obj.committer, 'patch_stats' : obj.patch_stats, 'weekday' : obj.weekday,
                'year' : obj.year, 'month' : obj.month, 'day' : obj.day, 'order': obj.order, 'subject' : obj.subject, 'parents' : obj.parents, 
                'tree_hash' : obj.tree_hash , 'commit_hash' : obj.commit_hash }
    
def ProcessLog(refStart, refEnd):
    log=[]
    le = LogEntry()
    p = subprocess.Popen(["git","log","--pretty=author:\%ae\%ncommitter:\%ce\%ndate:\%aD\%ncommit:\%H\%nparents:\%P\%nsubject:\%s\%n@@@@@@",refStart + ".." +refEnd],stdout=PIPE)
    for line in p.stdout:     
        if(re.match("^author",line)):
            mo = re.match("^author:(.*)",line)
            le.author = mo.groups(1)[0]
        elif(re.match("^committer:",line)):
            mo = re.match("^committer:(.*)",line)
            le.committer = mo.groups(1)[0]
        elif(re.match("^date:",line)):
            mo = re.match("^date:(.*)",line)
            le.date = mo.groups(1)[0]
            mo = re.match("^date:(.*), (\d+) (\D+) (\d+)",line)
            le.weekday = mo.group(1)
            le.day = mo.group(2)
            le.month = mo.group(3)
            le.year = mo.group(4)
        elif(re.match("^commit:",line)):
            mo = re.match("^commit:(.*)",line)
            le.commit_hash = mo.groups(1)[0]
        elif(re.match("^parents:",line)):
            mo = re.match("^parents:((.*) )*",line)
            le.parents = mo.groups(1)
        elif(re.match("^commit:",line)):
            mo = re.match("^commit:(.*)",line)
            le.commit_hash = mo.groups(1)[0]
        elif(re.match("^subject:",line)):
            mo = re.match("^subject:(.*)",line)
            le.subject = mo.groups(1)[0]
        elif(re.match("^@@@@",line)):
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
    files_modified = 0
    file_ext_dict  = dict()
    totalFile = FileStat()
    author_dict = dict()
    day_of_week = dict()
    month = dict()
    
    # walk thru the commits
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
            else:
                files_modified += 1
                
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
    # sort from largest to smallest
    for key in sorted(file_ext_dict.iterkeys(),reverse=True):
        print "file ext:" + key 
        value = file_ext_dict[key]
        value.PrintStats()
            
   
    log = ProcessLog(startRef,endRef)
    for le in log:
        print "author: " + le.author
    
    logfile = open('log1.json','w')
    
    s= json.dumps(['foo', {'bar': ('baz', None, 1.0, 2)}])

  
    
      
    json.dump(file_ext_dict,logfile,cls=MyEncoder, indent=2)
    json.dump(log,open('log.json','w'),cls=MyEncoder, indent=2)
   # s = json.JSONEncoder().dumps(file_ext_dict)
#        json.dump(log,logfile);
    
    print "done"

    


