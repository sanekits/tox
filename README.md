# tox: Quick directory-changer

The tox shell function provides a fast directory-change navigation tool.

The basic idea is that most directory-changes involve directories with long paths that you visit frequently, and it's better to do less typing to get there.

`tox` uses an index (which defaults to ~/.tox-index) to maintain a list of user-specified directories. It provides wildcard matching for fast destination specification, and resolves ambiguity by providing match menus.

Admin functions allow adding/removing index entries quickly. Indices can be local to a subtree or global.

Whenever you use `tox` to change directories, you can use `popd` to return to the previous dir without specifying its name.

## Usage


`tox -a`
  * Adds the current directory to active index

`tox bin`
  * Find directories in the index matching 'bin'.  If only one match, go there immediately.

`tox bin 2`
  * Choose the 2nd directory matching 'bin' and go to it immediately

`tox bin //`
  * Show menu of all dirs matching 'bin' in current and parent indices

`tox -e`
   * Load the [active index](#active_index) into $EDITOR

`tox -q`
   * Print information about the current and parent indices

`tox -d`
   * Delete current directory from the active index

`tox -c`
   * Clean the index, removing dead/duplicate dirs

`tox -p [pattern]`
   * Print matching entries, but don't change dir


## Bash shell name completion

If you're using bash as your shell, tox supports directory-name completion, e.g.:

`tox myproj[tab]`  will cause tox to match 'myproj' against the active index and print a list of matches, so that you can more easily complete directory names.

## The active index and index trees
<a name='active_index' />

By default, when `tox` runs the first time, it creates `~/.tox-index` and uses it as the "active" index.  However, you can have other indices: whenever you run `tox`, it does a search of parent directories for the current directory.  The first .tox-index encountered in that search becomes the active index and is the default list that will be searched for name matching.

This is useful if you have a project with several directories that are visited regularly and you wish to limit the scope of name matching to that project -- by placing a .tox-index file in the root of your project, you're effectively limiting the scope of the default search behavior.

## TODO
These things have NOT been implemented yet:

* Bug - no cd if arg matches index entry exactly

* Add - a '.tox-meta' file that can offer extended info about the project/dir

* Add 'add all child dirs'

* Add -i for 'print matching entries, plus info about each (# of names, last modified, contents of .tox-desc'

* Add 'prune all matches'

* Allow this:
    `tox bin /`
    "Search immediate ancestors "

* Allow this:
    `tox -a /etc/init.d`
    "Add an arbitrary dir to active index"




