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
import copy

class BaseStats:
    added = 0
    deleted = 0
    moved = 0
    modified = 0
    def toArray(self):
        return [self.added,self.deleted,self.moved,self.modified]
    def toString(self):
        s = ""
        for n in self.toArray():
            s = s + str(n)
    def Add(self,fs):
        self.added += fs.added
        self.deleted += fs.deleted
        self.moved += fs.moved
        self.modified += fs.modified
            
class Stats:
    lines = BaseStats()
    files = BaseStats()
    def Add(self,st):
        self.lines.Add(st.lines)
        self.files.Add(st.files)

class FileInfo (BaseStats):
    'FileStat is the files statistics'
    mode = 'modified'
    fromfile = None
    filename = None
    file_ext = None

    def AddFileInfo(self,fs):
        self.Add(fs)
    def PrintAll(self):
        if(self.mode != None):
            print "mode: " + self.mode
        print "from:"  + self.fromfile  + " to: " + self.filename
        self.PrintStats()   
    def PrintStats(self):
        print "total: " + str(self.TotalChanges()) + " added: " + str(self.added) + " deleted: " + str(self.deleted) + " modified: " + str(self.modified) 
        
    def TotalChanges(self):
        return self.added + self.deleted + self.modified
    def default(self,my_class):
        if not isinstance(my_class, FileInfo):
            print "You cnann't use the JSON custom MyClassEncoder"
            return
        return {'mode': my_class.mode, 'fromfile' : my_class.fromfile, 'filename' : my_class.filename , 'added': my_class.added, 
                'deleted' : my_class.deleted, 'modified' : my_class.modified, 'file_ext' : my_class.file_ext }

class FileExtInfo(Stats):
    file_ext = None
    
    def AddFileStat(self,fs):
        self.line_added += fs.added
        self.line_deleted = fs.deleted
        self.line_modified += fs.modified
        if(fs.mode == "new"):
            self.file_new +=1
        elif(fs.mode == "copy"):
            self.file_copied +=1
        elif(fs.mode == "deleted"):
            self.file_deleted +=1
        elif(fs.mode == "move"):
            self.file_moved += 1
        elif(fs.mode == "modified"):
            self.file_modified +=1
    def Print(self):
        print "ext:",self.file_ext," files: new :",self.file_new, " deleted:", self.file_deleted," copy:",self.file_copied, " moved:", self.file_moved, " modified:",self.file_modified, "lines: added", self.line_added, " deleted:", self.line_deleted, " modified:",self.line_modified

class MyEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj,FileInfo):
            return obj.default(obj)
        elif isinstance(obj,LogEntry):
            return obj.default(obj)
        elif isinstance(obj,BranchEntry):
            return obj.default(obj)
        else:
            return json.JSONEncoder.default(self,obj)

class PatchEngine:
    # helper method to Process  
    @staticmethod  
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
        return file
    # takes two commit hashes and figures out the changes as an array of fileinfosfiles and lines
    @staticmethod  
    def ProcessPatch(gitRepoPath,path, startRef, endRef):
        curFile = FileInfo()
        files = []
        header = 1
        chunk = 0
        chunkadd =0
        chunkdel =0
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
                elif (re.match("^copy from",line)):
                    mo = re.match("^copy from (.*)",line)
                    curFile.mode = "copy"
                    curFile.fromfile = str(mo.groups(1)[0])
                elif (re.match("^(rename|copy) to",line)):
                    mo = re.match("^(rename|copy) to (.*)",line)
                    curFile.filename = str(mo.groups(2)[1])
                elif (re.match("^new file mode",line)):
                    curFile.mode = "new"  
                elif (re.match("^deleted file mode",line)):
                    curFile.mode = "deleted"  
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
                        curFile = PatchEngine.ProcessChunk(curFile,chunkadd,chunkdel);
                        chunkdel = chunkadd = chunk = 0
                    
                    if(re.match("^diff",line)):
                        # new file, store current file stats and process header
                        header = 1
                        curFile.file_ext = os.path.splitext(curFile.filename)[1]
                        files.append(curFile)
                        curFile = FileInfo();
                
        # handle the last chunk for the last file
        curFile = PatchEngine.ProcessChunk(curFile,chunkadd,chunkdel)
        curFile.file_ext = os.path.splitext(curFile.filename)[1]
        files.append(curFile)              
        return files

class Commit:
    'CommitStat is the complete patch stat'
    file_st = BaseStats()
    line_st = BaseStats()    
    parents = []
    hash = ""
    files = None
    log = None
    repo = None
    

    def Process(self):
        self.files = PatchEngine.ProcessPatch(self.repo.repoPath,self.repo.path , self.parents[0],self.hash)
        self.log = self.repo.log[self.hash]
        
    def default(self,obj):
        return {'fromref' : obj.fromref, 'toref' : obj.toref, 'files' : obj.files, 'file_stats' : obj.file_stats,
                'newfiles' : obj.newfiles, 'deletedfiles' : obj.deletedfiles, 'modifiedfiles' : obj.modifiedfiles }
           
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
    hash = None
    ref = None
    def default(self,obj):
        return {'ref' : obj.ref , 'hash' : obj.hash }    
    
class FileEntry:   
    path = None
    name = None
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
            commit = Commit()
            commit.repo = self
            commit.hash = endRef
            commit.parents = [startRef]
            commit.Process()        
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
    filter = []
    # given a list of commits, returns a summary of changes for each file changed
    
    def Filter(self,name):   
        # in and then out filtering
        found_in = True
        
        for filter in self.filter_in:
            found_in = False
            result = name.find(filter);
            if(result >= 0):
                found_in = True
                break
        
        if(not(found_in)):
            return True
        
        for filter in self.filter_out:
            result = name.find(filter)
            if(result >= 0):
                return True
        return False
        
    def FindAllFileChanges(self,commits):
        files = {}
        
        for c in commits:
            for f in  c.files:   
                if(self.Filter(f.filename)):
                    continue
                  
                if(f.filename in files):
                    files[f.filename].AddFileInfo(f)
                else:
                    files[f.filename] = copy.deepcopy(f)  
        return files
    
    def FindFilesChangesByExt(self, files):
        file_ext_dict = {}
        for f in files.values():
            if(self.Filter(f.filename)):
                continue
            if(f.file_ext in file_ext_dict):
                file_ext_dict[f.file_ext].AddFileInfo(f)
            else:
                file_ext_dict[f.file_ext] =  copy.deepcopy(f)
                file_ext_dict[f.file_ext].filename = None
                file_ext_dict[f.file_ext].fromfile = None
                file_ext_dict[f.file_ext].mode = None
        return file_ext_dict
    
    def FindStats(self,commits):
        for c in commits:
           st = Stats()
           
    
    def TotalChanges(self, files):
        total = FileInfo()
        for f in files.values():
            total.AddFileInfo(f)
        return total
    
    def FindCommitsByWeek(self,commits):
        changes = {}
        
        for c in commits:
            d = datetime.date.fromtimestamp(float(c.log.timestamp))
            isodate = d.isocalendar()
            ds = str(isodate[0]) + "-" + str(isodate[1])
            if not(ds in changes):
                changes[ds] = []
            changes[ds].append(c)
        return changes

    def FindCommitsByWeekday(self,commits):
        changes = []
        
        for c in commits:
            d = datetime.date.fromtimestamp(float(c.log.timestamp))
            isodate = d.isocalender()
            weekday = isodate[2]
            if(changes[weekday] == None):
                changes[weekday] = []
            changes[weekday].append(c)

        return changes
    
            
    
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
    filter = []
    path= ""
    
    try:
        opts, args = getopt.getopt(sys.argv[1:],"d:o:i:r:p:")
    except getopt.GetoptError:
            print args
            sys.exit(1)
    for o, a in opts:
        if o == "-d":
            repoPath=a
        elif o == "-o":
            filter_out.append(a)
            filter.append([0,a])
        elif o == "-i":
            filter_in.append(a)
            filter.append([1,a])
        elif o == "-r":
            range=a
        elif o == "-p":
            path=a
    
        
    print "repo path=", repoPath    
    print "filter out = ", filter_out 
    print "filter in =", filter_in
    
    repo = Repo()
    repo.path=path
    repo.repoPath = repoPath
    
    repo.Process(range)
    
    report = Reports();
    report.filter_out = filter_out;
    report.filter_in = filter_in;
    
    files = report.FindAllFileChanges(repo.commits)
    files_ext = report.FindFilesChangesByExt(files)
    totalChanges = report.TotalChanges(files)
        
    print "Total Summary:"
    totalChanges.PrintStats()
    
    print "Total by File extension"
    for ext,fileextstat in sorted(files_ext.iteritems()):
        print "file ext : ",ext,fileextstat.PrintStats()     
        
    print "Foreach Commit:"
  
    for c in repo.commits:
        commits = []
        commits.append(c)
        files = report.FindAllFileChanges(commits)
        file_ext = report.FindFilesChangesByExt(files)
        print "COMMIT"
        log = c.log
        print "author :",log.author, "\nDate :", datetime.datetime.fromtimestamp(float(log.timestamp)), "\nhash :", commits[0].hash
        print "subject:", log.subject
        print "summary:"
        print "files:", c.file_st.toString()
        print "files by extension:"    
        for ext,fileextstat in sorted(file_ext.iteritems()):
            print "file ext : ",ext,fileextstat.PrintStats()     
            
            
        print "files:", len(files)
        for fn,fs in files.iteritems():
            print "filename :",fn, " added: ", fs.added, "deleted: ", fs.deleted, "modified: ", fs.modified

    print "By Time"
    week = report.FindCommitsByWeek(repo.commits)
    for d,commits in sorted(week.iteritems()):
        files = report.FindAllFileChanges(commits)
        changes = report.TotalChanges(files)
        print "week" , d
        changes.PrintStats()
    
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