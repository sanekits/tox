from tox_core import *

def test1():
    loadIndex()

def test2():
    # test1/.tox-index looks like this:
    # |-- a1
    # |   `-- b1
    # |       `-- c1
    # `-- x1
    #     `-- y1
    #         `-- z1

    ix=loadIndex('./test1/k1')
    pm=ix.matchPaths( pattern='c*' )
    assert(len(pm)==1)

    assert(len( ix.matchPaths( '*1' ))==6 )

if __name__=="__main__":

    test2()
    test1()


