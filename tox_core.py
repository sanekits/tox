# tox-core.py

import os

indexFileBase=".tox-index"

class indexContent(object):
    def __init__(self,path):
        self.path=path
        self.protect=False
        self.lines=[]

        with open(self.path,'r') as f:
            all=f.read().split('\n')
            if all[0].startswith('#protect'):
                self.protect=True
                self.lines=all[1:]
            else:
                self.lines=all


def testFile(dir,name):
    if os.path.exists('/'.join([dir,name])):
        return True
    return False

def getParent(dir):
    return '/'.join( xdir.split('/')[:-1] ) 


def findIndex(xdir=None):
    """ Find the index containing current dir, or None """
    if not xdir:
        xdir=os.getcwd()
    if testFile(xdir,indexBaseFile):
        return '/'.join([xdir,indexBaseFile])
    if xdir=='/':
        return None
    # Recurse to parent dir:
    return findIndex( getParent(xdir))
    
    

def loadIndex():
    """ Load the index for current dir """
    ix=findIndex()



if __name__=="__main__":
    pass
