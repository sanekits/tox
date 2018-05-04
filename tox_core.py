#!/usr/bin/env python

import os
import glob
import sys
import bisect
import argparse
import os.path
import fnmatch
import shutil 
import toxroot
from getpass import getpass
from subprocess import call

tox_core_root=""  # Where is our stuff?

indexFileBase=".tox-index"

def pwd():
    """ Return the $PWD value, which is nicer inside
    trees of symlinks, but fallback to getcwd if it's not
    set """
    return os.environ.get('PWD',os.getcwd())

def dirContains(parent,unk):
    """ Does parent dir contain unk dir? """
    left=os.path.realpath(parent)
    right=os.path.realpath(unk)
    if right.startswith(left):
        return True
    return False


def prompt(msg,defValue):
    sys.stderr.write("%s" % msg)
    try:
        res=getpass("[%s]:" % defValue,sys.stderr)
    except KeyboardInterrupt,e:
        sys.stderr.write("^C\n")
        sys.exit(1)
    if not res:
        return defValue
    return res


class IndexContent(list):
    def __init__(self,path):
        self.path=path
        self.protect=False
        self.outer=None  # If we are chaining indices

        with open(self.path,'r') as f:
            all=f.read().split('\n')
            all=[ l for l in all if len(l) > 0 ]
            if len(all):
                if all[0].startswith('#protect'):
                    self.protect=True
                    self.extend(all[1:])
                else:
                    self.extend(all)

    def Empty(self):
        """ Return true if index chain has no entries at all """
        if len(self):
            return False
        if self.outer is None:
            return True
        return self.outer.Empty()

    def indexRoot(self):
        """ Return dir of our index file """
        return os.path.dirname(self.path)

    def absPath(self,relDir):
        """ Return an absolute path if 'relDir' isn't already one """
        if relDir[0]=='/':
            return relDir
        return '/'.join([ self.indexRoot(), relDir])

    def relativePath(self,dir):
        """ Convert dir to be relative to our index root """
        try:
            r=self.indexRoot()
            if dir.index(r) == 0: # If the dir starts with our index root, remove that:
                return dir[len(r)+1:]
        except:
            pass
        return dir

    def addDir(self,xdir):
        dir=self.relativePath(xdir)
        if dir in self:
            return False # no change
        n=bisect.bisect(self,dir)
        self.insert(n,dir)
        return True

    def delDir(self,xdir):
        dir=self.relativePath(xdir)
        if not dir in self:
            return False # no change
        self.remove(dir)
        return True

    def clean(self):
        okPaths=set()
        for path in self:
            full=self.absPath(path)
            if not os.path.isdir(full):
                sys.stderr.write("Stale dir removed: %s\n" % full)
            else:
                okPaths.add(path)

        del self[:]
        self.extend(okPaths)
        self.write()
        sys.stderr.write("Cleaned index %s, %s dirs remain\n" % (self.path,len(self)))


    def write(self):
        # Write the index back to file
        with open(self.path,'w') as f:
            if self.protect:
                f.write("#protect\n")
            for line in sorted(self):
                f.write("%s\n" % line)



    def matchPaths( self, pattern, fullDirname=False):
        """ Returns matches of items in the index. """

        res=[]
        for path in self:
            for frag in path.split('/'):
                if fnmatch.fnmatch(frag,pattern):
                    # If fullDirname is set, we'll render an absolute path.
                    # Or... if the relative path is not a dir, we'll also
                    # render it as absolute.  This allows for cases where an 
                    # outer index path happens to match a local relative path
                    # which isn't indexed.
                    if fullDirname or not os.path.isdir(path):
                        res.append( self.absPath(path))
                    else:
                        res.append( path) 
                    break

        if self.outer is not None:
            # We're a chain, so recurse:
            res.extend( self.outer.matchPaths( pattern,True ))
        return res


class AutoContent(list):
    """ Reader/parser of the .tox-auto files """
    def __init__(self,path):
        self.path=path
        self.tagsLoc=None
        self.descLoc=None
        if path:
            with open(path,"r") as f:
                self.append(f.readlines())

        lineNdx=0
        for line in self:

            # Locate the .TAGS and .DESC content:
            if not self.tagsLoc and line.startswith('# .TAGS:'):
                self.tagsLoc=(lineNdx, 7)
            elif not self.descLoc and line.startswith('# .DESC:'):
                self.descLoc=(lineNdx, 7)

            lineNdx += 1 

    def tags(self):
        """ Return the value of .TAGS as array of strings """
        if not self.tagsLoc:
            return []
        raw=self[ self.tagsLoc[0] ] [ self.tagsLoc[1] : ]
        return raw.split()

    def desc(self):
        """ Return the value of .DESC as a string """
        pass


def testFile(dir,name):
    if os.path.exists('/'.join([dir,name])):
        return True
    return False

def getParent(dir):
    v=dir.split('/')[:-1] 
    if len(v)>1:
        return '/'.join( dir.split('/')[:-1] ) 
    return '/'


def findIndex(xdir=None):
    """ Find the index containing current dir, or None """
    if not xdir:
        xdir=pwd()
    global indexFileBase
    if testFile(xdir,indexFileBase):
        return '/'.join([xdir,indexFileBase])
    if xdir=='/':
        return None
    # Recurse to parent dir:
    return findIndex( getParent(xdir))
    
    

def loadIndex(xdir=None,deep=False,inner=None):
    """ Load the index for current xdir.  If deep is specified,
    also search up the tree for additional indices """
    if xdir and not os.path.isdir(xdir):
        raise RuntimeException("non-dir %s passed to loadIndex()" % xdir)

    ix=findIndex(xdir)
    if not ix:
        return None

    ic=IndexContent(ix)
    if not inner is None:
        inner.outer=ic
    if deep:
        ix=findIndex(getParent(ic.indexRoot()))
        if ix:
           loadIndex(os.path.dirname(ix),True,ic)
    return inner if not inner is None else ic



def resolvePatternToDir( pattern, N, printonly ):
    """ Match pattern to index, choose Nth result or prompt user, return dirname to caller. If printonly, don't prompt, just return the list
    of matches """
    # If N == '//', means 'global': search inner and outer indices 
    #    N == '/', means 'skip local': search outer indices only


    ix=loadIndex( pwd(), N in ['//','/'])
    if (N=='/'):
        # Skip inner index, which can be acheived by walking the index chain up one level
        if ix.outer is not None:
            ix=ix.outer

    if N in ['//','/']:
        N=None

    # If the pattern has slash and is a literal match for something in the index, then fine:
    if '/' in pattern and pattern in ix:
        return ix.absPath(pattern)

    hasGlob=len([ v for v in pattern if v in ['*','?']])  # Do we have any glob chars in pattern, 
    if not hasGlob:
        pattern='*'+pattern+'*'  # no, make it a wildcard

    if ix.Empty():
        return "!No matches for pattern [%s]" % pattern

    mx=ix.matchPaths(pattern)
    if len(mx)==0:
        return "!No matches for pattern [%s]" % pattern
    if N:
        N=int(N)
        if N > len(mx):
            return "!Offset %d exceeds number of matches for pattern [%s]" % (N,pattern)
        return ix.absPath(mx[N-1])

    if printonly:
        return printMatchingEntries(mx,ix)

    if len(mx)==1:
        return ix.absPath(mx[0])


    return promptMatchingEntry(mx,ix)

def printMatchingEntries(mx,ix):
    px=[]
    for i in range(1,len(mx)+1):
        px.append( mx[i-1])
    return '!' + '\n'.join(px)


def promptMatchingEntry(mx,ix):
    # Prompt user from matching entries:
    px=[]
    for i in range(1,len(mx)+1):
        px.append("%d: %s" % (i,mx[i-1]))
    px.append("Select index ")

    while True:
        resultIndex=prompt( '\n'.join(px), '1')
        resultIndex=int(resultIndex)
        if resultIndex < 1 or resultIndex > len(mx):
            sys.stderr.write("Invalid index: %d\n" % resultIndex)
        else:
            break

    return ix.absPath(mx[resultIndex-1])

def addDirToIndex(xdir, recurse):
    """ Add dir to active index """
    if not xdir:
        cwd=pwd()
    else:
        cwd=xdir

    ix=loadIndex() # Always load active index for this, even if
                   # the dir we're adding is out of tree

    def xAdd(path):
        if ix.addDir(path):
            ix.write()
            sys.stderr.write("%s added to %s\n" % (path,ix.path))
        else:
            sys.stderr.write("%s is already in the index\n" % path)

    xAdd(cwd)
    if recurse:
        for r, dirs, f in os.walk(cwd):
            dirs[:] = [ d for d in dirs if not d[0]=='.' ] # ignore hidden dirs
            for d in dirs:
                xAdd( r + '/' + d) 


def delCwdFromIndex():
    """ Delete current dir from active index """
    cwd=pwd()

    ix=loadIndex()

    if ix.delDir(cwd):
        ix.write()
        sys.stderr.write("%s removed from %s\n" % (cwd,ix.path))
    else:
        sys.stderr.write("%s was not found in the index\n" % cwd)

def editIndex():
    ipath=findIndex()
    print ("!!$EDITOR %s" % ipath)


def printIndexInfo(ixpath):
    ix=loadIndex(os.path.dirname(ixpath) if ixpath else ixpath,True)
    print("!PWD: %s" % (pwd() if not ixpath else os.path.dirname(ixpath)))
    print("Index: %s" % ix.path)
    print("# of dirs in index: %d" % len(ix))
    if os.environ['PWD']==ix.indexRoot():
        print("PWD == index root")

    if not ix.outer is None:
        print("   ===  Outer: === ")
        printIndexInfo( ix.outer.path )

def createEmptyIndex():
    sys.stderr.write("First-time initialization: creating %s\n" % indexFileBase )
    tgtDir=os.environ.get('HOME','/tmp')
    cwd=pwd()
    if dirContains(tgtDir,cwd):
        # The current dir is within the HOME tree?
        path='/'.join([tgtDir,indexFileBase])

    else:
        # Put it in the root, if we can
        path='/' + indexFileBase

    if os.path.isfile(path):
        raise RuntimeError("createEmptyIndex found an existing index at %s" % path)
    with open( path,'w') as f:
        f.write('#protect\n')

def createIndexHere():
    if os.path.isfile('./' + indexFileBase):
        sys.stderr.write("An index already exists in %s" % os.environ.get('PWD',os.getcwd()))
        return False
    with open(indexFileBase,'w') as f:
        f.write('#protect\n')
        sys.stderr.write("Index has been created in %s" % pwd())

def cleanIndex():
    ix=loadIndex()
    ix.clean()

def hasToxAuto(dir ):
    xf='/'.join([dir,'.tox-auto']) 
    return os.path.isfile(xf),xf


def editToxAutoHere(templateFile):
    has,path=hasToxAuto(".")
    if not has:
        # Create from template file first time:
        shutil.copyfile( templateFile,'./.tox-auto') 
    # Invoke the editor:
    print ("!!$EDITOR %s" % '.tox-auto')



def findToxCoreRoot(mods):

    keys=list(mods.iterkeys())
    for k in keys:
        try:
            v=mods[k]
            if v.__file__.find('tox_core.py') > 0:
                return os.path.dirname(v.__file__)
        except:
            pass

def printReport(opts):
    # Report options are single-letter flags:
    #   d: show .DESC in auto files
    #   t: show .TAGS in auto files
    ix=loadIndex()

    for dir in ix:
        sys.stdout.write(dir)
        has,autoPath=hasToxAuto(dir)
        if has:
            cnt=AutoContent(autoPath)
            if 't' in opts:  # show .TAGS?

                pass
            if 'd' in opts:  # show .DESC?
                pass
            

    


if __name__ == "__main__" :

    tox_core_root=findToxCoreRoot(sys.modules)

    p=argparse.ArgumentParser('tox - quick directory-changer.')

    p.add_argument("-x",action='store_true',dest='create_ix_here',help="Create index in current dir")
    p.add_argument("-r",action='store_true',dest='recurse',help="Recursive mode (e.g. for -a add all dirs in subtree)", default=False)
    p.add_argument("-a",action='store_true',dest='add_to_index',help="Add dir to index [default=current dir, -r recurses to add all]")
    p.add_argument("-d",action='store_true',dest='del_from_index',help="Delete current dir from index")
    p.add_argument("-c",action='store_true',dest='cleanindex',help='Cleanup index')
    p.add_argument("-q",action='store_true',dest='indexinfo',help="Print index information/location")
    p.add_argument("-e",action='store_true',dest='editindex',help="Edit the index")
    p.add_argument("-p",action='store_true',dest='printonly',help="Print matches in plain mode")
    p.add_argument("--auto",action='store_true',dest='autoedit',help="Edit the local .tox-auto, create first if missing")
    p.add_argument("--report",action='store',dest='reportOpts',help="Generate report from index: d=[show desc]\nt=[show tags]")
    p.add_argument("pattern",nargs='?',help="Glob pattern to match against index")
    p.add_argument("N",nargs='?',help="Select N'th matching directory, or use '/' or '//' to expand search scope.")
    origStdout=sys.stdout

    try:
        sys.stdout=sys.stderr
        args=p.parse_args()

    finally:
        sys.stdout=origStdout


    empty=True # Have we done anything meaningful?
    if not findIndex():
        createEmptyIndex()
        empty=False

    if args.reportOpts:
        printReport( args.reportOpts)

    if args.autoedit:
        editToxAutoHere('/'.join([tox_core_root,'tox-auto-default-template']))

    if args.create_ix_here:
        createIndexHere()
        empty=False

    if args.add_to_index:
        addDirToIndex(args.pattern, args.recurse)
        sys.exit(0)
        
    elif args.del_from_index:
        delCwdFromIndex()
        empty=False

    if args.indexinfo:
        printIndexInfo(findIndex())
        empty=False

    if args.editindex:
        editIndex()
        sys.exit(0)

    if args.cleanindex:
        cleanIndex()
        empty=False


    if not args.pattern:
        if not empty:
            sys.exit(0)

        sys.stderr.write("No search pattern specified, try --help\n")
        sys.exit(1)

    print(resolvePatternToDir( args.pattern, args.N, args.printonly ))

    sys.exit(0)

