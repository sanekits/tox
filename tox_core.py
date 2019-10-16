#!/usr/bin/env python3

import os
import sys
tox_core_root = os.path.dirname(os.path.realpath(__file__))

sys.path.insert(0, tox_core_root)

from io import StringIO
import re
import bisect
import argparse
import fnmatch
import shutil
from getpass import getpass
from subprocess import call
from os.path import dirname, isdir, realpath, exists, isfile
from os import getcwd, environ, stat
from pwd import getpwuid
from setutils import IndexedSet


toxRootKey = 'ToxSysRoot'
file_sys_root = os.getenv(toxRootKey, '/')
# Swap this for chroot-like testing


def set_file_sys_root(d):
    global file_sys_root
    prev = file_sys_root
    file_sys_root = d
    return prev

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
                return dir[len(r) + 1:]
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
        with open(self.path+'.tmp', 'w') as f:
            if self.protect:
                f.write("#protect\n")
            for line in sorted(self):
                f.write("%s\n" % line)
        os.rename(self.path+'.tmp',self.path)

    def matchPaths(self, patterns, fullDirname=False):
        """ Returns matches of items in the index. """

        xs = IndexedSet()
        # Identify all the potential matches, filter by all patterns:
        cand_paths = self[:]
        for pattern in patterns:
            qual_paths = []
            for path in cand_paths:
                for frag in path.split('/'):
                    if fnmatch.fnmatch(frag, pattern):
                        # If fullDirname is set, we'll render an absolute path.
                        # Or... if the relative path is not a dir, we'll also
                        # render it as absolute.  This allows for cases where an
                        # outer index path happens to match a local relative path
                        # which isn't indexed.
                        if fullDirname or not isdir(path):
                            qual_paths.append(self.absPath(path))
                        else:
                            qual_paths.append(path)
            cand_paths = qual_paths

        # Remove dupes:
        for path in cand_paths:
            xs.add(path)
        if self.outer is not None:
            # We're a chain, so recurse:
            pp = self.outer.matchPaths(patterns, True)
            xs = xs.union(pp)
        return list(xs)


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


def isChildDir(parent, cand):
    ''' Returns true if parent is an ancestor of cand. '''
    if cand.startswith(parent) and len(cand) > len(parent):
        return True
    return False


def ownerCheck(xdir,filename,only_mine):
    ''' Apply ownership rule to file xdir/filename, such that:
       - If only_mine is True, owner of the file must match os.environ['USER']
       - If only_mine is False, we don't care who owns it.
       return True if rule check passes. '''
    if not only_mine:
        return True
    owner = stat( '/'.join((xdir,filename))).st_uid
    user = os.environ['USER']
    return getpwuid(owner).pw_name == user

def findIndex(xdir=None,only_mine=True):
    """ Find the index containing current dir or 'xdir' if supplied.  Return HOME/.tox-index as a last resort, or None if there's no indices whatsoever. 

    only_mine: ignore indices which don't have $USER as owner on the file.
    """
    if not xdir:
        xdir = pwd()
    global indexFileBase
    if not isChildDir(file_sys_root, xdir):
        xdir = os.path.realpath(xdir)
        if not isChildDir(file_sys_root, xdir):
            if len(xdir) < len(file_sys_root):
                return None
            if xdir != file_sys_root:
                # If we've searched all the way up to the root /, try the
                # user's HOME dir:
                return findIndex(environ['HOME'])
    if isFileInDir(xdir, indexFileBase) and ownerCheck(xdir,indexFileBase,only_mine):
        return '/'.join([xdir, indexFileBase])
    # Recurse to parent dir:
    if xdir == file_sys_root:
        # If we've searched all the way up to the root /, try the user's HOME
        # dir:
        return findIndex(environ['HOME'])
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
        ix = findIndex(dirname(ic.indexRoot()))  # Bug?
        #ix = findIndex(ic.indexRoot())
        if ix:
            loadIndex(dirname(ix), True, ic)
    return inner if not inner is None else ic


class ResolveMode(object):
    userio = 1  # interact with user, menu-driven
    printonly = 2  # print the match list
    calc = 3    # calculate the match list and return it


def resolvePatternToDir(patterns, N, K, mode=ResolveMode.userio):
    """ Match patterns to index, choose Nth result or prompt user, return dirname to caller. If printonly, don't prompt, just return the list of matches."""
    # patterns are 'and-ed' together: a dir must match all patterns to be included
    # in the search set.
    # If K == '//', means 'global': search inner and outer indices
    #    K == '/', means 'skip local': search outer indices only

    pattern_0 = patterns[0] if len(
        patterns) == 1 else ''  # Todo: use all patterns

    # ix is the directory index:
    ix = loadIndex(pwd(), K in ['//', '/'])
    if (K == '/'):
        # Skip inner index, which can be achieved by walking the index chain up
        # one level
        if ix.outer is not None:
            ix = ix.outer

    if K in ['//', '/']:
        K = None

    if ix.Empty():
        return (None, "!No matches for [%s]" % '+'.join(patterns))

    # If pattern_0 has slash and literally matches something in the index,
    # then we accept it as the One True Match:
    if '/' in pattern_0 and pattern_0 in ix:
        rk = ix.absPath(pattern_0)
        return ([rk], r)

    k_patterns = []
    for p in patterns:
        # Do we have any glob chars in pattern?
        hasGlob = len([v for v in p if v in ['*', '?']])
        if not hasGlob:
            # no, make it a wildcard: our default behavior is 'match any part
            # of path'
            k_patterns.append('*' + p + '*')
        else:
            k_patterns.append(p)

    mx = ix.matchPaths(k_patterns)
    if len(mx) == 0:
        return (None, "!No matches for pattern [%s]" % '+'.join(patterns))
    if N:
        N = int(N)
        if abs(N) > len(mx):
            sys.stderr.write("Warning: Offset %d exceeds number of matches for pattern [%s]. Selecting index %d instead.\n" % (
                N, '+'.join(patterns), len(mx)))
            N = len(mx) * (1 if N >= 0 else -1)
        if N >= 1:
            rk = ix.absPath(mx[N - 1])
        else:
            rk = ix.absPath(mx[N])
        if mode == ResolveMode.printonly:
            return printMatchingEntries([rk], rk)
        return ([rk], rk)

    if mode == ResolveMode.printonly:
        return printMatchingEntries(mx, ix)

    if len(mx) == 1:
        rk = ix.absPath(mx[0])
        return ([rk], rk)

    if mode == ResolveMode.calc:
        return ([mx, None])

    return promptMatchingEntry(mx, ix)


def printMatchingEntries(mx, ix):
    px = []
    for i in range(1, len(mx) + 1):
        px.append(mx[i - 1])
    return (mx, '!' + '\n'.join(px))


def promptMatchingEntry(mx, ix):
    # Prompt user from matching entries:
    px = []
    for i in range(1, len(mx) + 1):
        px.append("%d: %s" % (i, mx[i - 1]))
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

    return (mx, ix.absPath(mx[resultIndex - 1]))


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
            dirs[:] = [d for d in dirs if not d[
                0] == '.']  # ignore hidden dirs
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


def ensureHomeIndex():
    global indexFileBase
    loc = '/'.join((environ['HOME'], indexFileBase))
    if not os.path.isfile(loc):
        with open(loc,'w') as ff:
            sys.stderr.write("Tox first-time initialization: creating %s\n" % loc)
            ff.write("# This is your HOME dir .tox-index, try 'to --help' \n")


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


def printGrep(pattern, ostream=None):
    if pattern:
        ostream = StringIO.StringIO()
    else:
        ostream = sys.stdout
    ix = loadIndex()
    sys.stdout.write("!")
    for dir in ix:
        dir = ix.absPath(dir)
        ostream.write(dir)
        has, autoPath = hasToxAuto(dir)
        if has:
            cnt = AutoContent(autoPath)
            ostream.write(" [.TAGS: %s] " % (','.join(cnt.tags())))
            ostream.write(cnt.desc())
        ostream.write("\n")

    matchCnt = 0
    if not pattern:
        return len(ix) > 0
    else:
        # Match the pattern and print matches
        lines = ostream.getvalue().split('\n')
        for line in lines:
            try:
                vv = re.search(pattern, line)
                if vv:
                    matchCnt += 1
                    print(line)
            except:
                pass

        return matchCnt > 0


if __name__ == "__main__":
    p = argparse.ArgumentParser('''tox - quick directory-changer {python%d.%d}''' % (sys.version_info[0],sys.version_info[1]))
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
    p.add_argument("-g", "--grep", action='store_true', dest='do_grep',
                   help="Match dirnames and .tox-auto search properties against a regular expression")
    #p.add_argument("patterns", nargs='?', help="Pattern(s) to match. If final arg is integer, it is treated as list index. ")
    # p.add_argument(
    # "N", nargs='?', help="Select N'th matching directory, or use '/' or '//' to expand search scope.")
    origStdout = sys.stdout

    try:
        sys.stdout = sys.stderr
        args, vargs = p.parse_known_args()
    finally:
        sys.stdout = origStdout

    if args.debugger:
        import pudb
        pudb.set_trace()

    N = None  # None or an integer indicating index-of-match
    K = None  # Either None, '/' or //' to indicate scope operator
    patterns = vargs
    try:
        # Dir index is the last arg if its an integer
        if len(vargs) > 1:
            N = int(vargs[-1])
            del vargs[-1]
    except:
        pass

    try:
        if vargs[-1] in ['/', '//']:
            K = vargs[-1]
            del vargs[-1]
    except:
        pass
    empty = True  # Have we done anything meaningful?

    ensureHomeIndex()

    if args.do_grep:
        vv = printGrep(patterns[0] if len(patterns) else None)
        sys.exit(0 if vv else 1)

    if args.autoedit:
        editToxAutoHere('/'.join([tox_core_root, 'tox-auto-default-template']))
        sys.exit(0)

    if args.create_ix_here:
        createIndexHere()
        empty = False

    if args.add_to_index:
        addDirToIndex(patterns[0] if len(patterns) else None, args.recurse)
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

    if not patterns:
        if not empty:
            sys.exit(0)

        sys.stderr.write("No search patterns specified, try --help\n")
        sys.exit(1)

    rmode = ResolveMode.printonly if args.printonly else ResolveMode.userio
    res = resolvePatternToDir(patterns, N, K, rmode)
    if res[1]:
        print(res[1])

    sys.exit(0)
