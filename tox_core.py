#!/bin/env python

import os
import glob
import sys
import argparse
import os.path
import fnmatch
from itertools import product

indexFileBase=".tox-index"

def prompt(msg,defValue):
    sys.stderr.write("%s" % msg)
    res=raw_input("[%s]:" % defValue)
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
        if N >= len(mx):
            return None
        return mx[N]

    if len(mx)==1:
        return mx[0]

    # Prompt user from matching entries:
    px=[]
    for i in range(1,len(mx)+1):
        px.append("%d: %s" % (i,mx[i-1]))
    px.append("Select index ")

    while True:
        resultIndex=prompt( '\n'.join(px), str( N if N else '1' ))
        resultIndex=int(resultIndex)
        if resultIndex < 1 or resultIndex > len(mx):
            sys.stderr.write("Invalid index: %d\n" % resultIndex)
        else:
            break

    return mx[resultIndex-1]

if __name__=="__main__":
    p=argparse.ArgumentParser()

    p.add_argument("-a",action='store_true',dest='add_to_index',help="Add current dir to index")
    p.add_argument("-x",action='store_true',dest='reindex',help='Rebuild index with tree scan')
    p.add_argument("-s",action='store_true',dest='sortindex',help='Re-sort index')
    p.add_argument("-q",action='store_true',dest='indexinfo',help="Print index information/location")
    p.add_argument("pattern",help="Glob pattern to match against index")
    p.add_argument("N",nargs='?',help="Select N'th matching directory")
    args=p.parse_args()
    
    print(resolvePatternToDir( args.pattern, args.N ))



