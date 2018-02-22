from tox_core import *

def test1():
    loadIndex()

def test2():
    pm=PathMatcher.find_matching_paths( [ '/ab/bc/cd', '/x/y/z'], '*c' )
    print(pm)

if __name__=="__main__":

    test2()
    test1()


