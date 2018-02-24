#!/usr/bin/env python

import os
import glob
import sys
import bisect
import argparse
import os.path
import fnmatch
from getpass import getpass
from subprocess import call


indexFileBase=".tox-index"

def pwd():
    """ Return the $PWD value, which is nicer inside
    trees of symlinks, but fallback to getcwd if it's not
    set """
    return os.environ.get('PWD',os.getcwd())

def prompt(msg,defValue):
    sys.stderr.write("%s" % msg)
    res=getpass("[%s]:" % defValue,sys.stderr)
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
            if all[0].startswith('#protect'):
                self.protect=True
                self.extend(all[1:])
            else:
                self.extend(all)

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



    def matchPaths( self, pattern ):
        """ Returns matches of items in the index. """

        res=[]
        for path in self:
            for frag in path.split('/'):
                if fnmatch.fnmatch(frag,pattern):
                    res.append(path)
                    break

        return res


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
        ix=findIndex(getParent(xdir))
        if ix:
           loadIndex(os.path.dirname(ix),True,ic)
    return inner if not inner is None else ic

def resolvePatternToDir( pattern, N ):
    """ Match pattern to index, choose Nth result or prompt user, return dirname to caller """

    ix=loadIndex( pwd())
    # If the pattern is a literal match for something in the index, then fine:
    if pattern in ix:
        return ix.absPath(pattern)

    hasGlob=len([ v for v in pattern if v in ['*','?']])  # Do we have any glob chars in pattern?
    if not hasGlob:
        pattern='*'+pattern+'*'  # no, make it a wildcard

    if len(ix)==0:
        return "!No matches for pattern [%s]" % pattern

    mx=ix.matchPaths(pattern)
    if len(mx)==0:
        return "!No matches for pattern [%s]" % pattern
    if N:
        N=int(N)
        if N > len(mx):
            return "!Offset %d exceeds number of matches for pattern [%s]" % (N,pattern)
        return ix.absPath(mx[N-1])

    if len(mx)==1:
        return ix.absPath(mx[0])

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

def addCwdToIndex():
    """ Add current dir to active index """
    cwd=pwd()

    ix=loadIndex()

    if ix.addDir(cwd):
        ix.write()
        sys.stderr.write("%s added to %s\n" % (cwd,ix.path))
    else:
        sys.stderr.write("%s is already in the index\n" % cwd)

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
    sys.stderr.write("First-time initialization: creating ~/%s\n" % indexFileBase )
    home=os.environ.get('HOME','/tmp')
    path='/'.join([home,indexFileBase])
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

# class MyArgParser(argparse.ArgumentParser): 
#    def error(self, message):
#       sys.stderr.write('error: %s\n' % message)
#       self.print_help(sys.stderr)
#       sys.exit(2)

if __name__=="__main__":
    p=argparse.ArgumentParser('tox - quick directory-changer.')

    p.add_argument("-x",action='store_true',dest='create_ix_here',help="Create index in current dir")
    p.add_argument("-a",action='store_true',dest='add_to_index',help="Add current dir to index")
    p.add_argument("-d",action='store_true',dest='del_from_index',help="Delete current dir from index")
    p.add_argument("-c",action='store_true',dest='cleanindex',help='Cleanup index')
    p.add_argument("-q",action='store_true',dest='indexinfo',help="Print index information/location")
    p.add_argument("-e",action='store_true',dest='editindex',help="Edit the index")
    p.add_argument("pattern",nargs='?',help="Glob pattern to match against index")
    p.add_argument("N",nargs='?',help="Select N'th matching directory")
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

    if args.create_ix_here:
        createIndexHere()
        empty=False

    if args.add_to_index:
        addCwdToIndex()
        empty=False
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
    
    print(resolvePatternToDir( args.pattern, args.N ))

    sys.exit(0)



