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

# churn is the amount of changes in a given file, commit, repo.
# it can be based on either files or lines
class Churn:
    "Churn is the smallest unit of changes"
    def __init__(self):
        self.added = 0
        self.deleted = 0
        self.moved = 0
        self.modified = 0
    def toArray(self):
        return [self.added,self.deleted,self.moved,self.modified]
    def toString(self):
        s = ""
        for n in self.toArray():
            if(s !=""): 
                s = s +","
            s = s + str(n)
        return s
    def Add(self,ch):
        self.added += ch.added
        self.deleted += ch.deleted
        self.moved += ch.moved
        self.modified += ch.modified
    def TotalChurn(self):
        return self.added + self.deleted + self.moved + self.modified    
    def Clone(self):
        c = Churn()
        c.added = self.added
        c.deleted = self.deleted
        c.moved = self.moved
        c.modified = self.modified
        return c

class FileInfo:
    'FileStat is the files statistics'
    
    
    def __init__(self):
        self.mode = "modified"
        self.fromfile = None
        self.filename = None
        self.file_ext = None
        self.line_churn = Churn()
        self.file_ext = None
    
    def Add(self,fi):
        self.line_churn.Add(fi.line_churn)
    def PrintAll(self):
        if(self.mode != None):
            print "mode: " + self.mode
        print "from:"  + self.fromfile  + " to: " + self.filename
        self.PrintStats()   
    def PrintStats(self):
        print self.line_churn.toString()
    def default(self,my_class):
        if not isinstance(my_class, FileInfo):
            print "You cnann't use the JSON custom MyClassEncoder"
            return
        return {'mode': my_class.mode, 'fromfile' : my_class.fromfile, 'filename' : my_class.filename , 'added': my_class.added, 
                'deleted' : my_class.deleted, 'modified' : my_class.modified, 'file_ext' : my_class.file_ext }
    def Clone(self):
        fi = FileInfo()
        fi.mode = self.mode
        fi.fromfile = self.fromfile
        fi.filename = self.filename
        fi.file_ext = self.file_ext
        fi.line_churn = self.line_churn.Clone()
        return fi
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
                file.line_churn.modified += chunkdel
                file.line_churn.added += chunkadd - chunkdel
            else:
                file.line_churn.modified += chunkadd
                file.line_churn.deleted += chunkdel - chunkadd
        else:
            file.line_churn.added += chunkadd
            file.line_churn.deleted += chunkdel
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
   
    
    def __init__(self):
        self.file_churn = Churn()
        self.line_churn = Churn()    
        self.parents = []
        self.hash = ""
        self.files = None
        self.log = None
        self.repo = None
    
    def Process(self):
        self.files = PatchEngine.ProcessPatch(self.repo.repoPath,self.repo.path , self.parents[0],self.hash)
        self.log = self.repo.log[self.hash]
        for f in self.files:
            self.line_churn.Add(f.line_churn)
            if(f.mode == None):
                continue
            elif(f.mode == "new"):
                self.file_churn.added += 1
            elif(f.mode == "copy"):
                self.file_churn.moved += 1
            elif(f.mode == "deleted"):
                self.file_churn.deleted +=1
            elif(f.mode == "move"):
                self.file_churn.moved += 1
            elif(f.mode == "modified"):
                self.file_churn.modified +=1
            
            
        
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
    
    def __init__(self):
        self.repoPath = ""
        self.commits = []
        self.log = {}
        self.branches = []
        self.files = []
        self.refs = []
        self.path = ""
        
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
    # given a list of commits, returns a summary of changes for each file changed
    def __init__(self):
        self.filter_out = []
        self.filter_in = []
        self.filter = []
    
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
                    files[f.filename].Add(f)
                else:
                    files[f.filename] = f.Clone() 
        return files
    
    def FindFilesChangesByExt(self, files):
        file_ext_dict = {}
        for f in files.values():
            if(self.Filter(f.filename)):
                continue
            if(f.file_ext in file_ext_dict):
                file_ext_dict[f.file_ext].Add(f)
            else:
                file_ext_dict[f.file_ext] =  f.Clone()
        return file_ext_dict
    
    def FindStats(self,commits):
        for c in commits:
           st = Stats()
              
    def TotalChanges(self, files):
        total = FileInfo()
        for f in files.values():
            total.Add(f)
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
    for ext,fi in sorted(files_ext.iteritems()):
        print "file ext : ",ext,fi.PrintStats()     
    
    print "Total By File"
    for fn,fi in sorted(files.iteritems()):
        print "file: ",fn,fi.PrintStats()
    
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
        print "files:", c.file_churn.toString()
        print "Total by File extension"
        for ext,fi in sorted(file_ext.iteritems()):
            print "file ext : ",ext,fi.PrintStats()     
        print "Total By File"
        for fn,fi in sorted(files.iteritems()):
            print "file: ",fn,fi.PrintStats()
        

    print "Week"
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