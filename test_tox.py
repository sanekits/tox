from tox_core import *


def test_1():
    print "stub1"
    loadIndex()


def test_2():

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
