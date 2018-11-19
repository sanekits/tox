#!/usr/bin/env python2

from tox_core import *

class TmpSwap(object):
    ''' context object to make symmetric set calls on __enter__ and __exit__ '''

    def __init__(self, origVal, newVal, setFunc):
        self.newval = newVal
        self.origval = origVal
        self.setfunc = setFunc

    def __enter__(self):
        self.setfunc(self.newval)
        return self

    def __exit__(self, *args):
        self.setfunc(self.origval)

def test_1():
    print "tox_core_root=" + tox_core_root
    loadIndex()


def test_2():

    with TmpSwap(os.getcwd(),tox_core_root,os.chdir):
        ix = loadIndex('./test1/a1')
        pm = ix.matchPaths(pattern='c*')
        assert len(pm) == 1

        assert len(ix.matchPaths('*1')) == 6


def test_3():
    pass


if __name__ == "__main__":

    test_1()
    test_3()
    test_2()
