from tox_core import *

def test1():
    loadIndex()

def test2():
    ix=loadIndex('./test1/k1')
    pm=ix.matchPaths( pattern='*c' )
    print(pm)

if __name__=="__main__":

    test2()
    test1()


