# tox-core.py

import os
import glob
import os.path
import fnmatch
from itertools import product

indexFileBase=".tox-index"

class PathMatcher(object):

    
    # Cross-Python dictionary views on the keys 
    if hasattr(dict, 'viewkeys'):
        # Python 2
        def _viewkeys(d):
            return d.viewkeys()
    else:
        # Python 3
        def _viewkeys(d):
            return d.keys()


    @staticmethod
    def _in_trie(trie, path):
        """Determine if path is completely in trie"""
        current = trie
        for elem in path:
            try:
                current = current[elem]
            except KeyError:
                return False
        return None in current


    @staticmethod
    def find_matching_paths(paths, pattern):
        """Produce a list of paths that match the pattern.

        * paths is a list of strings representing filesystem paths
        * pattern is a glob pattern as supported by the fnmatch module

        """
        if os.altsep:  # normalise
            pattern = pattern.replace(os.altsep, os.sep)
        pattern = pattern.split(os.sep)

        # build a trie out of path elements; efficiently search on prefixes
        path_trie = {}
        for path in paths:
            if os.altsep:  # normalise
                path = path.replace(os.altsep, os.sep)
            _, path = os.path.splitdrive(path)
            elems = path.split(os.sep)
            current = path_trie
            for elem in elems:
                current = current.setdefault(elem, {})
            current.setdefault(None, None)  # sentinel

        matching = []

        current_level = [path_trie]
        for subpattern in pattern:
            if not glob.has_magic(subpattern):
                # plain element, element must be in the trie or there are
                # 0 matches
                if not any(subpattern in d for d in current_level):
                    return []
                matching.append([subpattern])
                current_level = [d[subpattern] for d in current_level if subpattern in d]
            else:
                # match all next levels in the trie that match the pattern
                matched_names = fnmatch.filter({k for d in current_level for k in d}, subpattern)
                if not matched_names:
                    # nothing found
                    return []
                matching.append(matched_names)
                current_level = [d[n] for d in current_level for n in _viewkeys(d) & set(matched_names)]

        return [os.sep.join(p) for p in product(*matching)
                if _in_trie(path_trie, p)]



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

    def matchIndex( self, args ):
         """ Returns matches of items in the index. """

         #res=[ path for path in self if contains(path,args) ]


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
    print(ic)




if __name__=="__main__":
    pass
