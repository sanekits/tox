#!/bin/env python

import os
import glob
import sys
import bisect
import argparse
import os.path
import fnmatch
from getpass import getpass


indexFileBase=".tox-index"

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
    return '/'.join( dir.split('/')[:-1] ) 


def findIndex(xdir=None):
    """ Find the index containing current dir, or None """
    if not xdir:
        xdir=os.getcwd()
    global indexFileBase
    if testFile(xdir,indexFileBase):
        return '/'.join([xdir,indexFileBase])
    if xdir=='/':
        return None
    # Recurse to parent dir:
    return findIndex( getParent(xdir))
    
    

def loadIndex(xdir=None):
    """ Load the index for current dir """
    ix=findIndex(xdir)
    if not ix:
        return None

    ic=IndexContent(ix)
    return ic

def resolvePatternToDir( pattern, N ):
    """ Match pattern to index, choose Nth result or prompt user, return dirname to caller """


    hasGlob=len([ v for v in pattern if v in ['*','?']])  # Do we have any glob chars in pattern?
    if not hasGlob:
        pattern='*'+pattern+'*'  # no, make it a wildcard

    ix=loadIndex( os.getcwd() )
    if len(ix)==0:
        return None
    mx=ix.matchPaths(pattern)
    if len(mx)==0:
        return None
    if N:
        N=int(N)
        if N > len(mx):
            return None
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
    """ Add current dir to current index """
    cwd=os.getcwd()

    ix=loadIndex()

    if ix.addDir(cwd):
        ix.write()
        sys.stderr.write("%s added to %s\n" % (cwd,ix.path))
    else:
        sys.stderr.write("%s is already in the index\n" % cwd)

def printIndexInfo():
    ix=loadIndex()
    print("!PWD: %s" % os.getcwd())
    print("Index: %s" % ix.path)
    print("# of dirs in index: %d" % len(ix))
    if os.getcwd()==ix.indexRoot():
        print("PWD == index root")

# class MyArgParser(argparse.ArgumentParser): 
#    def error(self, message):
#       sys.stderr.write('error: %s\n' % message)
#       self.print_help(sys.stderr)
#       sys.exit(2)

if __name__=="__main__":
    p=argparse.ArgumentParser()

    p.add_argument("-a",action='store_true',dest='add_to_index',help="Add current dir to index")
    p.add_argument("-x",action='store_true',dest='reindex',help='Rebuild index with tree scan')
    p.add_argument("-s",action='store_true',dest='sortindex',help='Re-sort index')
    p.add_argument("-q",action='store_true',dest='indexinfo',help="Print index information/location")
    p.add_argument("pattern",nargs='?',help="Glob pattern to match against index")
    p.add_argument("N",nargs='?',help="Select N'th matching directory")
    origStdout=sys.stdout
    try:
        sys.stdout=sys.stderr
        args=p.parse_args()

    finally:
        sys.stdout=origStdout


    empty=True # Have we done anything meaningful?

    if args.add_to_index:
        addCwdToIndex()
        empty=False

    if args.indexinfo:
        printIndexInfo()
        empty=False

    if not args.pattern:
        if not empty:
            sys.exit(0)

        sys.stderr.write("No search pattern specified, try --help\n")
        sys.exit(1)
    
    print(resolvePatternToDir( args.pattern, args.N ))

    sys.exit(0)



