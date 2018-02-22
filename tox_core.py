# tox-core.py

import os
import glob
import os.path
import fnmatch
from itertools import product

indexFileBase=".tox-index"






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
    
    

def loadIndex():
    """ Load the index for current dir """
    ix=findIndex()

    ic=IndexContent(ix)
    return ic




if __name__=="__main__":
    pass
