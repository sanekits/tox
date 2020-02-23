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
    print("tox_core_root=" + tox_core_root)
    loadIndex()


def test_2():

    # Treat the test1 as if it were the root:
    with TmpSwap(os.getcwd(), tox_core_root + '/test1', os.chdir):
        with TmpSwap(file_sys_root, tox_core_root + '/test1', set_file_sys_root):
            ix = loadIndex('./a1')
            pm = ix.matchPaths(patterns=['c*'])
            assert len(pm) == 1

            assert len(ix.matchPaths(['*1'])) == 7


def test_3():
    with TmpSwap(file_sys_root, tox_core_root + '/tree-2/', set_file_sys_root):
        ix = loadIndex()


if __name__ == "__main__":

    test_2()
    test_1()
    test_3()
