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
    def Process(self, gitRepoPath, startRef, endRef):
        header = 1
        
        self.fromref = startRef
        self.toref = endRef
        self.files = []
        curFile = FileStat()
        chunk = 0
        chunkadd =0
        chunkdel =0
        p = subprocess.Popen(["git","diff","-M","-C","-p", "--find-copies-harder",startRef + ".." + endRef],stdout=PIPE,cwd=gitRepoPath)
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
                    curFile.filename = str(mo.groups(2)[1])
                elif (re.match("^new file mode",line)):
                    curFile.mode = "new"    
                elif (re.match("^\+\+\+ (.*)",line)):
                    mo = re.match("^\+\+\+ (.*)",line)
                    curFile.filename = str(mo.groups(1)[0])
                elif (re.match("^--- (.*)",line)):
                    mo = re.match("^--- (.*)",line)
                    curFile.fromfile = str(mo.groups(1)[0])
                elif (re.match("^(new|deleted) file mode",line)):
                    mo = re.match("^(new|deleted) file mode",line)
                    curFile.mode = str(mo.groups(1)[0])
                elif (re.match("^@@",line)):
                    header = 0               
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
                        curFile.file_ext = os.path.splitext(curFile.filename)[1]
                        self.files.append(curFile)
                        curFile = FileStat();
                
        # handle the last chunk for the last file
        curFile = self.ProcessChunk(curFile,chunkadd,chunkdel)
        curFile.file_ext = os.path.splitext(curFile.filename)[1]
        self.files.append(curFile)              
        return self

class CommitStat:
    files_added = 0;
    files_removed = 0;
    files_renamed = 0;
    files_copied = 0;
    files_deleted = 0;
    binary_files_changed = 0;
    ref = "";
    files_changed_by_ext = [];
    total_lines_added = 0;
    total_lines_removed = 0;
    total_lines_modifed = 0;
    patch = PatchStat()
            
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
        p = subprocess.Popen(["git","log","--pretty=author:%ae%ncommitter:%ce%ndate:%ct%ncommit:%H%nparents:%P%nsubject:%s%n@@@@@@",range],stdout=PIPE,cwd=self.repoPath)
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
                              "--pretty=%H", "--reverse", range ],stdout=subprocess.PIPE,cwd=self.repoPath)
        startRef = ""
        endRef = ""
        # read all the references
        for line in p.stdout:
            self.refs.append(line.rstrip("\n"))
        p.wait()
        # walk thru all the refs
        for ref in self.refs:
            if(startRef == ""):
                startRef = ref
                continue
            endRef = ref
            patch = PatchStat()
            patch.Process(self.repoPath, startRef,endRef)
            commit = CommitStat();
            commit.patch = patch
            commit.ref = ref
            
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
    # given a list of commits, returns a summary of changes for each file changed
    def FindAllFileChanges(self,commits):
        files = {}
        
        for c in commits:
            for f in  c.patch.files:   
                if(f.filename in files):
                    files[f.filename].AddFileStat(f)
                else:
                    files[f.filename] = f
        return files
    
    def FindFilesChangesByExt(self, files):
        file_ext_dict = {}
        for filename,f in files.iteritems():
            if(f.file_ext in file_ext_dict):
                file_ext_dict[f.file_ext].AddFileStat(f)
            else:
                file_ext_dict[f.file_ext] = f
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
    try:
        opts, args = getopt.getopt(sys.argv[1:],"dfir")
    except getopt.GetoptError, err:
            sys.exit(1)
    for o, a in opts:
        if o == "-d":
            repoPath=a
        elif o == "-f":
            filter_out=a 
        elif o == "-i":
            filter_in=a 
        elif o == "-r":
            range=a
         
    repo = Repo(repoPath)
    repo.Process(range)
    
    report = Reports();
    
    files = report.FindAllFileChanges(repo.commits)
    files_ext = report.FindFilesChangesByExt(files)
    totalChanges = report.TotalChanges(files)
        
    print "Total Summary:"
    totalChanges.PrintStats()
    
    print "Total by File extension"
    for ext,filestat in files_ext.iteritems():
        print "ext = ",ext, " file stats"
        filestat.PrintStats()
        
    print "Foreach Commit:"
  
    for c in repo.commits:
        commits = []
        commits.append(c)
        files = report.FindAllFileChanges(commits)
        file_ext = report.FindFilesChangesByExt(files)
        changes = report.TotalChanges(files)
        print "COMMIT"
        log = repo.log[commits[0].ref]
        print "author :",log.author, "\nDate :", datetime.datetime.fromtimestamp(float(log.timestamp)), "\nhash :", commits[0].ref
        print "subject:", log.subject
        print "summary:"
        
        print "files by extension:"    
        for ext,fs in file_ext.iteritems():
            print "file ext ", ext , "stats =",  "added: ", fs.added, "deleted: ", fs.deleted, "modified: ", fs.modified
            
        print "files:", len(files)
        for fn,fs in files.iteritems():
            print "filename :",fn, "stats =",  "added: ", fs.added, "deleted: ", fs.deleted, "modified: ", fs.modified

        
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