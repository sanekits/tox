#!/usr/bin/env python2

import os
import sys
import bisect
import argparse
import fnmatch
import shutil
from getpass import getpass
from subprocess import call
from os.path import dirname, isdir, realpath, exists, isfile
from os import getcwd, environ

tox_core_root = os.path.dirname(os.path.realpath(__file__))

indexFileBase = ".tox-index"


def pwd():
    """ Return the $PWD value, which is nicer inside
    trees of symlinks, but fallback to getcwd if it's not
    set """
    return environ.get('PWD', getcwd())


def prompt(msg, defValue):
    sys.stderr.write("%s" % msg)
    res = getpass("[%s]:" % defValue, sys.stderr)
    return res if res else defValue


def dirContains(parent, unk):
    """ Does parent dir contain unk dir? """
    return realpath(unk).startswith(realpath(parent))


class IndexContent(list):
    def __init__(self, path):
        self.path = path
        self.protect = False
        self.outer = None  # If we are chaining indices

        with open(self.path, 'r') as f:
            all = f.read().split('\n')
            all = [l for l in all if len(l) > 0]
            if len(all):
                if all[0].startswith('#protect'):
                    self.protect = True
                    self.extend(all[1:])
                else:
                    self.extend(all)

    def Empty(self):
        """ Return true if index chain has no entries at all """
        if len(self):
            return False
        if self.outer is None:
            return True
        return self.outer.Empty()

    def indexRoot(self):
        """ Return dir of our index file """
        return dirname(self.path)

    def absPath(self, relDir):
        """ Return an absolute path if 'relDir' isn't already one """
        if relDir[0] == '/':
            return relDir
        return '/'.join([self.indexRoot(), relDir])

    def relativePath(self, dir):
        """ Convert dir to be relative to our index root """
        try:
            r = self.indexRoot()
            # If the dir starts with our index root, remove that:
            if dir.index(r) == 0:
                return dir[len(r)+1:]
        except:
            pass
        return dir

    def addDir(self, xdir):
        dir = self.relativePath(xdir)
        if dir in self:
            return False  # no change
        n = bisect.bisect(self, dir)
        self.insert(n, dir)
        return True

    def delDir(self, xdir):
        dir = self.relativePath(xdir)
        if not dir in self:
            return False  # no change
        self.remove(dir)
        return True

    def clean(self):
        okPaths = set()
        for path in self:
            full = self.absPath(path)
            if not isdir(full):
                sys.stderr.write("Stale dir removed: %s\n" % full)
            else:
                okPaths.add(path)

        del self[:]
        self.extend(okPaths)
        self.write()
        sys.stderr.write("Cleaned index %s, %s dirs remain\n" %
                         (self.path, len(self)))

    def write(self):
        # Write the index back to file
        with open(self.path, 'w') as f:
            if self.protect:
                f.write("#protect\n")
            for line in sorted(self):
                f.write("%s\n" % line)

    def matchPaths(self, pattern, fullDirname=False):
        """ Returns matches of items in the index. """

        res = []
        for path in self:
            for frag in path.split('/'):
                if fnmatch.fnmatch(frag, pattern):
                    # If fullDirname is set, we'll render an absolute path.
                    # Or... if the relative path is not a dir, we'll also
                    # render it as absolute.  This allows for cases where an
                    # outer index path happens to match a local relative path
                    # which isn't indexed.
                    if fullDirname or not isdir(path):
                        res.append(self.absPath(path))
                    else:
                        res.append(path)
                    break

        if self.outer is not None:
            # We're a chain, so recurse:
            res.extend(self.outer.matchPaths(pattern, True))
        return res


class AutoContent(list):
    """ Reader/parser of the .tox-auto files """

    def __init__(self, path):
        self.path = path
        self.tagsLoc = None
        self.descLoc = None
        if path:
            with open(path, "r") as f:
                self.extend(f.readlines())

        lineNdx = 0
        for line in self:

            # Locate the .TAGS and .DESC content:
            if not self.tagsLoc and line.startswith('# .TAGS:'):
                self.tagsLoc = (lineNdx, 8)
            elif not self.descLoc and line.startswith('# .DESC:'):
                self.descLoc = (lineNdx, 8)

            lineNdx += 1

    def tags(self):
        """ Return the value of .TAGS as array of strings """
        if not self.tagsLoc:
            return []
        raw = self[self.tagsLoc[0]][self.tagsLoc[1]:]
        return raw.split()

    def desc(self):
        """ Return the value of .DESC as a string """
        if self.descLoc is None:
            return ""
        return self[self.descLoc[0]][self.descLoc[1]:].rstrip()


def isFileInDir(dir, name):
    """ True if file 'name' is in 'dir' """
    return exists('/'.join([dir, name]))


def findIndex(xdir=None):
    """ Find the index containing current dir, or HOME/.tox-index, or None """
    if not xdir:
        xdir = pwd()
    global indexFileBase
    if isFileInDir(xdir, indexFileBase):
        return '/'.join([xdir, indexFileBase])
    if xdir == '/':
        # If we've searched all the way up to the root /, try the user's HOME dir:
        return findIndex(environ['HOME'])
    # Recurse to parent dir:
    return findIndex(dirname(xdir))


def loadIndex(xdir=None, deep=False, inner=None):
    """ Load the index for current xdir.  If deep is specified,
    also search up the tree for additional indices """
    if xdir and not isdir(xdir):
        raise RuntimeError("non-dir %s passed to loadIndex()" % xdir)

    ix = findIndex(xdir)
    if not ix:
        return None

    ic = IndexContent(ix)
    if not inner is None:
        inner.outer = ic
    if deep and not xdir == environ['HOME']:
        ix = findIndex(dirname(ic.indexRoot()))
        if ix:
            loadIndex(dirname(ix), True, ic)
    return inner if not inner is None else ic


class ResolveMode(object):
    userio = 1  # interact with user, menu-driven
    printonly = 2  # print the match list
    calc = 3    # calculate the match list and return it


def resolvePatternToDir(pattern, N, mode=ResolveMode.userio):
    """ Match pattern to index, choose Nth result or prompt user, return dirname to caller. If printonly, don't prompt, just return the list of matches."""
    # If N == '//', means 'global': search inner and outer indices
    #    N == '/', means 'skip local': search outer indices only

    # ix is the directory index:
    ix = loadIndex(pwd(), N in ['//', '/'])
    if (N == '/'):
        # Skip inner index, which can be achieved by walking the index chain up one level
        if ix.outer is not None:
            ix = ix.outer

    if N in ['//', '/']:
        N = None

    if ix.Empty():
        return (None, "!No matches for pattern [%s]" % pattern)

    # If the pattern has slash and literally matches something in the index, then we accept it as the One True Match:
    if '/' in pattern and pattern in ix:
        rk = ix.absPath(pattern)
        return ([rk],r)

    # Do we have any glob chars in pattern?
    hasGlob = len([v for v in pattern if v in ['*', '?']])
    if not hasGlob:
        # no, make it a wildcard: our default behavior is 'match any part of path'
        pattern = '*'+pattern+'*'

    mx = ix.matchPaths(pattern)
    if len(mx) == 0:
        return (None,"!No matches for pattern [%s]" % pattern)
    if N:
        N = int(N)
        if N > len(mx):
            sys.stderr.write("Warning: Offset %d exceeds number of matches for pattern [%s]. Selecting index %d instead.\n" % (
                N, pattern, len(mx)))
            N = len(mx)
        rk = ix.absPath(mx[N-1])
        return ([rk],rk)

    if mode == ResolveMode.printonly:
        return printMatchingEntries(mx, ix)

    if len(mx) == 1:
        rk = ix.absPath(mx[0])
        return ([rk],rk)

    if mode == ResolveMode.calc:
        return ([mx,None])

    return promptMatchingEntry(mx, ix)


def printMatchingEntries(mx, ix):
    px = []
    for i in range(1, len(mx)+1):
        px.append(mx[i-1])
    return (mx, '!' + '\n'.join(px))


def promptMatchingEntry(mx, ix):
    # Prompt user from matching entries:
    px = []
    for i in range(1, len(mx)+1):
        px.append("%d: %s" % (i, mx[i-1]))
    px.append("Select index ")
    resultIndex = 1
    while True:
        try:
            resultIndex = prompt('\n'.join(px), '1')
        except KeyboardInterrupt:
            return (mx, "!echo Ctrl+C")
        try:
            if resultIndex.lower() == 'q':
                sys.exit(1)
            resultIndex = int(resultIndex)
        except SystemExit as e:
            raise
        except:
            continue
        if resultIndex < 1 or resultIndex > len(mx):
            sys.stderr.write("Invalid index: %d\n" % resultIndex)
        else:
            break

    return (mx, ix.absPath(mx[resultIndex-1]))


def addDirToIndex(xdir, recurse):
    """ Add dir to active index """
    cwd = xdir if xdir else pwd()
    ix = loadIndex()  # Always load active index for this, even if
    # the dir we're adding is out of tree

    def xAdd(path):
        if ix.addDir(path):
            ix.write()
            sys.stderr.write("%s added to %s\n" % (path, ix.path))
        else:
            sys.stderr.write("%s is already in the index\n" % path)
    xAdd(cwd)
    if recurse:
        for r, dirs, f in os.walk(cwd):
            dirs[:] = [d for d in dirs if not d[0] == '.']  # ignore hidden dirs
            for d in dirs:
                xAdd(r + '/' + d)


def delCwdFromIndex():
    """ Delete current dir from active index """
    cwd = pwd()
    ix = loadIndex()
    if ix.delDir(cwd):
        ix.write()
        sys.stderr.write("%s removed from %s\n" % (cwd, ix.path))
    else:
        sys.stderr.write("%s was not found in the index\n" % cwd)


def editIndex():
    ipath = findIndex()
    print("!!$EDITOR %s" % ipath)


def printIndexInfo(ixpath):
    ix = loadIndex(dirname(ixpath) if ixpath else ixpath, True)
    print("!PWD: %s" % (pwd() if not ixpath else dirname(ixpath)))
    print("Index: %s" % ix.path)
    print("# of dirs in index: %d" % len(ix))
    if environ['PWD'] == ix.indexRoot():
        print("PWD == index root")

    if not ix.outer is None:
        print("   ===  Outer: === ")
        printIndexInfo(ix.outer.path)


def createEmptyIndex():
    sys.stderr.write("First-time initialization: creating %s\n" %
                     indexFileBase)
    tgtDir = environ.get('HOME', '/tmp')
    cwd = pwd()
    if dirContains(tgtDir, cwd):
        # The current dir is within the HOME tree?
        path = '/'.join([tgtDir, indexFileBase])

    else:
        # Put it in the root, if we can
        path = '/' + indexFileBase

    if isfile(path):
        raise RuntimeError(
            "createEmptyIndex found an existing index at %s" % path)
    with open(path, 'w') as f:
        f.write('#protect\n')


def createIndexHere():
    if isfile('./' + indexFileBase):
        sys.stderr.write("An index already exists in %s" %
                         environ.get('PWD', getcwd()))
        return False
    with open(indexFileBase, 'w') as f:
        f.write('#protect\n')
        sys.stderr.write("Index has been created in %s" % pwd())


def cleanIndex():
    ix = loadIndex()
    ix.clean()


def hasToxAuto(dir):
    xf = '/'.join([dir, '.tox-auto'])
    return isfile(xf), xf


def editToxAutoHere(templateFile):
    has, path = hasToxAuto(".")
    if not has:
        # Create from template file first time:
        shutil.copyfile(templateFile, './.tox-auto')
    # Invoke the editor:
    print("!!$EDITOR %s" % '.tox-auto')


def printReport(opts):
    # Report options are single-letter flags:
    #   d: show .DESC in auto files
    #   t: show .TAGS in auto files
    ix = loadIndex()

    sys.stdout.write("!")
    for dir in ix:
        dir = ix.absPath(dir)
        sys.stdout.write(dir)
        has, autoPath = hasToxAuto(dir)
        if has:
            cnt = AutoContent(autoPath)
            if 't' in opts:  # show .TAGS?

                sys.stdout.write(" [.TAGS: %s] " % (','.join(cnt.tags())))

            if 'd' in opts:  # show .DESC?
                sys.stdout.write(cnt.desc())

        sys.stdout.write("\n")


if __name__ == "__main__":
    p = argparse.ArgumentParser('tox - quick directory-changer.')
    p.add_argument("-z", "--debug", action='store_true', dest='debugger',
                   help="Run debugger in main")
    p.add_argument("-x", "--ix-here", action='store_true', dest='create_ix_here',
                   help="Create index in current dir")
    p.add_argument("-r", "--recurse", action='store_true', dest='recurse',
                   help="Recursive mode (e.g. for -a add all dirs in subtree)", default=False)
    p.add_argument("-a", "--add-dir", action='store_true', dest='add_to_index',
                   help="Add dir to index [default=current dir, -r recurses to add all]")
    p.add_argument("-d", "--del-dir", action='store_true', dest='del_from_index',
                   help="Delete current dir from index")
    p.add_argument("-c", "--cleanup", action='store_true',
                   dest='cleanindex', help='Cleanup index')
    p.add_argument("-q", "--query", action='store_true', dest='indexinfo',
                   help="Print index information/location")
    p.add_argument("-e", "--edit", action='store_true',
                   dest='editindex', help="Edit the index")
    p.add_argument("-p", "--printonly", action='store_true', dest='printonly',
                   help="Print matches in plain mode")
    p.add_argument("--auto", "--autoedit", action='store_true', dest='autoedit',
                   help="Edit the local .tox-auto, create first if missing")
    p.add_argument("-t", "--report", action='store_true', dest='do_report', help="Generate report from .tox-auto content") 
    p.add_argument("pattern", nargs='?', help="Glob pattern to match against index")
    p.add_argument(
        "N", nargs='?', help="Select N'th matching directory, or use '/' or '//' to expand search scope.")
    origStdout = sys.stdout

    try:
        sys.stdout = sys.stderr
        args = p.parse_args()
    finally:
        sys.stdout = origStdout

    if args.debugger:
        import pudb
        pudb.set_trace()

    empty = True  # Have we done anything meaningful?

    if not findIndex():
        createEmptyIndex()
        empty = False

    if args.do_report:
        printReport('dt')
        empty = False

    if args.autoedit:
        editToxAutoHere('/'.join([tox_core_root, 'tox-auto-default-template']))

    if args.create_ix_here:
        createIndexHere()
        empty = False

    if args.add_to_index:
        addDirToIndex(args.pattern, args.recurse)
        sys.exit(0)

    elif args.del_from_index:
        delCwdFromIndex()
        empty = False

    if args.indexinfo:
        printIndexInfo(findIndex())
        empty = False

    if args.editindex:
        editIndex()
        sys.exit(0)

    if args.cleanindex:
        cleanIndex()
        empty = False

    if not args.pattern:
        if not empty:
            sys.exit(0)

        sys.stderr.write("No search pattern specified, try --help\n")
        sys.exit(1)

    rmode=ResolveMode.printonly if args.printonly else ResolveMode.userio
    res = resolvePatternToDir(args.pattern, args.N, rmode)
    if res[1]:
        print(res[1])

    sys.exit(0)
