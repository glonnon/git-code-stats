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
import datetime
import getopt


class FileStat:
    'FileStat is the files statistics'
    mode = 'modified'
    fromfile = ''
    filename = ''
    added = 0 
    deleted = 0
    modified = 0
    file_ext = ''

    def Clone(self):
        fs = FileStat()
        fs.mode = self.mode
        fs.fromfile = self.fromfile
        fs.filename = self.filename
        fs.added  = self.added 
        fs.deleted = self.deleted 
        fs.modified = self.modified
        fs.file_ext = self.file_ext
        return fs
    def AddFileStat(self,fs):
        self.added += fs.added
        self.deleted += fs.deleted
        self.modified += fs.modified
    def PrintAll(self):
        print "mode: " + self.mode
        print "from:"  + self.fromfile  + " to: " + self.filename
        self.PrintStats()   
    def PrintStats(self):
        print "total: " + str(self.TotalChanges()) + " added: " + str(self.added) + " deleted: " + str(self.deleted) + " modified: " + str(self.modified) 
        
    def TotalChanges(self):
        return self.added + self.deleted + self.modified
    def default(self,my_class):
        if not isinstance(my_class, FileStat):
            print "You cnann't use the JSON custom MyClassEncoder"
            return
        return {'mode': my_class.mode, 'fromfile' : my_class.fromfile, 'filename' : my_class.filename , 'added': my_class.added, 
                'deleted' : my_class.deleted, 'modified' : my_class.modified, 'file_ext' : my_class.file_ext }

class MyEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj,FileStat):
            return obj.default(obj)
        elif isinstance(obj,LogEntry):
            return obj.default(obj)
        elif isinstance(obj,PatchStat):
            return obj.default(obj)
        elif isinstance(obj,BranchEntry):
            return obj.default(obj)
        else:
            return json.JSONEncoder.default(self,obj)

class CommitStat:
    'CommitStat is the complete patch stat'
    files_added = 0
    files_deleted = 0
    files_moved = 0
    files_copied = 0
    files_modified = 0
    binary_files_changed = 0
    
    ref = ""
    
    lines_added = 0
    lines_removed = 0
    lines_modifed = 0
    
    fromref = ""
    toref = ""
    
    files = []
    
    def default(self,obj):
        return {'fromref' : obj.fromref, 'toref' : obj.toref, 'files' : obj.files, 'file_stats' : obj.file_stats,
                'newfiles' : obj.newfiles, 'deletedfiles' : obj.deletedfiles, 'modifiedfiles' : obj.modifiedfiles }
    
    # helper method to Process    
    def ProcessChunk(self,file,chunkadd,chunkdel):
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
        return file
      
    # takes two commit hashes and figures out the changes
    def ProcessPatch(self, gitRepoPath,path, startRef, endRef):
        header = 1
        
        self.fromref = startRef
        self.toref = endRef
        self.ref = endRef
        self.files = []
        curFile = FileStat()
        chunk = 0
        chunkadd =0
        chunkdel =0
        modified = 1
        p = subprocess.Popen(["git","diff","-M","-C","-p", "--find-copies-harder",startRef + ".." + endRef,"--",path],stdout=PIPE,cwd=gitRepoPath)
        for line in p.stdout:
            # process the header
            if(header == 1):
                if(re.match("^diff --git",line)):
                        pass
                elif (re.match("^index",line)):
                    pass
                elif (re.match("similarity index",line)):
                    pass
                elif (re.match("^rename from",line)):
                    mo = re.match("^rename from (.*)",line)
                    curFile.mode = "move"
                    curFile.fromfile = str(mo.groups(1)[0])
                    self.files_moved += 1
                    modified = 0
                elif (re.match("^copy from",line)):
                    mo = re.match("^copy from (.*)",line)
                    curFile.mode = "copy"
                    curFile.fromfile = str(mo.groups(1)[0])
                    self.files_copied += 1
                    modified = 0
                elif (re.match("^(rename|copy) to",line)):
                    mo = re.match("^(rename|copy) to (.*)",line)
                    curFile.filename = str(mo.groups(2)[1])
                elif (re.match("^new file mode",line)):
                    curFile.mode = "new"  
                    self.files_added += 1
                    modified = 0  
                elif (re.match("^deleted file mode",line)):
                    curFile.mode = "deleted"  
                    self.files_deleted += 1
                    modified = 0  
                elif (re.match("^\+\+\+ [ab]/(.*)",line)):
                    mo = re.match("^\+\+\+ [ab]/(.*)",line)
                    curFile.filename = str(mo.groups(1)[0])
                elif (re.match("^--- [ab]/(.*)",line)):
                    mo = re.match("^--- [ab]/(.*)",line)
                    curFile.fromfile = str(mo.groups(1)[0])
                elif (re.match("^(new|deleted) file mode",line)):
                    mo = re.match("^(new|deleted) file mode",line)
                    curFile.mode = str(mo.groups(1)[0])
                elif (re.match("^@@",line)):
                    header = 0
                    self.files_modified += modified               
            else: # process the body of the diff (line differences)
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
                        curFile = self.ProcessChunk(curFile,chunkadd,chunkdel);
                        chunkdel = chunkadd = chunk = 0
                    
                    if(re.match("^diff",line)):
                        # new file, store current file stats and process header
                        header = 1
                        modified = 1
                        curFile.file_ext = os.path.splitext(curFile.filename)[1]
                        self.files.append(curFile)
                        curFile = FileStat();
                
        # handle the last chunk for the last file
        curFile = self.ProcessChunk(curFile,chunkadd,chunkdel)
        chunkdel = chunkadd = chunk = 0
        curFile.file_ext = os.path.splitext(curFile.filename)[1]
        self.files.append(curFile)              
        return self

            
class LogEntry:
    author = ''
    committer = ''
    patch_stats = ''
    timestamp = 0
    order = 0 
    subject = ''
    parents = []
    tree_hash = ''
    commit_hash = ''
    def default(self,obj):
        return {'author' : obj.author , 'committer' : obj.committer, 'patch_stats' : obj.patch_stats,
                'timestamp' : obj.timestamp, 'order': obj.order, 'subject' : obj.subject, 'parents' : obj.parents, 
                'tree_hash' : obj.tree_hash , 'commit_hash' : obj.commit_hash }
    
class BranchEntry:
    hash = ''
    ref = ''
    def default(self,obj):
        return {'ref' : obj.ref , 'hash' : obj.hash }    
    
class FileEntry:   
    path = ''
    name = ''
    type = 'blob'
    def default(self,obj):
        return {'path': obj.path, 'name' : obj.name, 'type' : obj.type }

class Repo:
    repoPath = ""
    commits = []
    log = {}
    branches = []
    files = []
    refs = []
    path = ""
    
    def __init__(self,path):
        self.repoPath = path
    def ProcessBranches(self,range):
    
        p = subprocess.Popen(["git","show-ref"],stdout=PIPE,cwd=self.repoPath)
        for line in p.stdout:
                 
            be = BranchEntry()
            mo = re.match("(.*) (.*)\n",line)
            be.ref = mo.groups(1)[1]
            be.hash = mo.groups(1)[0]
            self.branches.append(be)
        p.wait()
        return
    def ProcessLog(self, range):
        self.log = {}
        le = LogEntry()
        p = subprocess.Popen(["git","log","--pretty=author:%ae%ncommitter:%ce%ndate:%ct%ncommit:%H%nparents:%P%nsubject:%s%n@@@@@@",range, "--",self.path],stdout=PIPE,cwd=self.repoPath)
        for line in p.stdout:     
            if(re.match("^author",line)):
                mo = re.match("^author:(.*)\n",line)
                le.author = mo.groups(1)[0]
            elif(re.match("^committer:",line)):
                mo = re.match("^committer:(.*)\n",line)
                le.committer = mo.groups(1)[0]
            elif(re.match("^date:",line)):
                mo = re.match("^date:(.*)\n",line)
                le.timestamp = mo.groups(1)[0]
            elif(re.match("^commit:",line)):
                mo = re.match("^commit:(.*)\n",line)
                le.commit_hash = mo.groups(1)[0]
            elif(re.match("^parents:",line)):
                le.parents = re.findall("[0-9a-f]{40}",line)
            elif(re.match("^commit:",line)):
                mo = re.match("^commit:(.*)\n",line)
                le.commit_hash = mo.groups(1)[0]
            elif(re.match("^subject:",line)):
                mo = re.match("^subject:(.*)\n",line)
                le.subject = mo.groups(1)[0]
            elif(re.match("^@@@@",line)):
                self.log[le.commit_hash] = le
                le = LogEntry()
        p.wait()
        return
    def ProcessCommits(self,range):
        p = subprocess.Popen(["git","log", "--first-parent",
                              "--pretty=%H", "--reverse", range, "--", self.path ],stdout=subprocess.PIPE,cwd=self.repoPath)
        startRef = ""
        endRef = ""
        # read all the references
        for line in p.stdout:
            self.refs.append(line.rstrip("\n"))
        p.wait()
       
        print "commits = ", len(self.refs)
        count = 0
        # walk thru all the refs
        for ref in self.refs:
            if(startRef == ""):
                startRef = ref
                continue
            if(count > 100):
                sys.stdout.write("+")
                sys.stdout.flush()
                count = 0
            else:
                count+=1
                
            endRef = ref
            commit = CommitStat()
            commit.ProcessPatch(self.repoPath, self.path, startRef,endRef)            
            self.commits.append(commit)
            startRef = endRef
        return
    
    def ProcessFiles(self,range):
        p = subprocess.Popen(["git","ls-tree","-r","HEAD"],stdout=PIPE,cwd=self.repoPath)
        for line in p.stdout:             
            fe = FileEntry()
            mo = re.match("^(.*) (.*) (.*) (.*)\n",line)
            fe.type = mo.groups(1)
            fe.path = mo.groups(2)
            fe.name = ''
            self.files.append(fe)
        p.wait()
        return
    def Process(self, range):
        
        print "processing logs"
        self.ProcessLog(range)
        print "processing commits"
        self.ProcessCommits(range)
        print "processing branches"
        #self.ProcessBranches(range)
        print "processing files"
        #self.ProcessFiles(range)
        return
 
    

class Reports:
    filter_out = []
    filter_in = []
    # given a list of commits, returns a summary of changes for each file changed
    
    def Filter(self,name):   
        for filter in self.filter_out:
            result = name.find(filter)
            if(result != -1):
                return True
        return False

        
    def FindAllFileChanges(self,commits):
        files = {}
        
        for c in commits:
            for f in  c.files:   
                if(self.Filter(f.filename)):
                    continue
                  
                if(f.filename in files):
                    files[f.filename].AddFileStat(f)
                else:
                    files[f.filename] = f.Clone()
                    
        return files
    
    def FindFilesChangesByExt(self, files):
        file_ext_dict = {}
        for f in files.values():
            if(self.Filter(f.filename)):
                continue
            
            if(f.file_ext in file_ext_dict):
                file_ext_dict[f.file_ext].AddFileStat(f)
            else:  
                file_ext_dict[f.file_ext] = f.Clone()
            
        return file_ext_dict
    
    def TotalChanges(self, files):
        total = FileStat()
        for f in files.values():
            total.AddFileStat(f)
        return total
    
    
# range and a working directory
# process every first parent reference
# create a 
# FileStat  contains the changes for the modified changes
# CommitStat contains the changes for each Commit
# LogEntry contains the log information
# BranchEntry contains the branche information
  
# MAIN PROGRAM


def main():
    # the range of commits.
    repoPath="."
    range="test_suite_start..test_suite"
    range="master"
    filter_out = []
    filter_in = []
    path= ""
    
    try:
        opts, args = getopt.getopt(sys.argv[1:],"d:f:i:r:p:")
    except getopt.GetoptError:
            sys.exit(1)
    for o, a in opts:
        if o == "-d":
            repoPath=a
        elif o == "-f":
            filter_out.append(a)
        elif o == "-i":
            filter_in.append(a)
        elif o == "-r":
            range=a
        elif o == "-p":
            path=a
    
        
    print "repo path=", repoPath    
    print "filter out = ", filter_out 
    repo = Repo(repoPath)
    repo.path=path
    repo.Process(range)
    
    report = Reports();
    report.filter_out = filter_out;
    
    files = report.FindAllFileChanges(repo.commits)
    files_ext = report.FindFilesChangesByExt(files)
    totalChanges = report.TotalChanges(files)
        
    print "Total Summary:"
    totalChanges.PrintStats()
    
    print "Total by File extension"
    for ext,filestat in files_ext.iteritems():
        print "file ext = ",ext, " total:", filestat.TotalChanges()," added:", filestat.added, " deleted:",filestat.deleted, " modified", filestat.modified
       
        
    print "Foreach Commit:"
  
    for c in repo.commits:
        commits = []
        commits.append(c)
        files = report.FindAllFileChanges(commits)
        file_ext = report.FindFilesChangesByExt(files)
        changes = report.TotalChanges(files)
        print "COMMIT"
        log = repo.log[c.ref]
        print "author :",log.author, "\nDate :", datetime.datetime.fromtimestamp(float(log.timestamp)), "\nhash :", commits[0].ref
        print "subject:", log.subject
        print "summary:"
        print "files added:", c.files_added, " deleted: ", c.files_deleted, " moved: ", c.files_moved, " copied: ", c.files_copied, " modified: ", c.files_modified
        print "files by extension:"    
        for ext,filestat in file_ext.iteritems():
            print "file ext = ",ext, " total:", filestat.TotalChanges()," added:", filestat.added, " deleted:",filestat.deleted, " modified", filestat.modified
            
        print "files:", len(files)
        for fn,fs in files.iteritems():
            print "filename :",fn, " added: ", fs.added, "deleted: ", fs.deleted, "modified: ", fs.modified

        
    sys.exit(0)

    file = open('log.js','w')
    file.write('var log = ')
    json.dump(log,file,cls=MyEncoder,indent=2)
    file.close()
    file = open('commit.js','w')
    file.write('var commit = ')
    json.dump(commits,file,cls=MyEncoder,indent=2)
    file.close()
    file = open('ref.js','w')
    file.write('var ref = ')
    #json.dump(branches,file,cls=MyEncoder,indent=2)
    file.close()

if __name__ == '__main__':
    main()