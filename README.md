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

`tox --auto`
   * Edit the local [.tox-auto](#using-tox-auto) file (create if needed)


## Bash shell name completion

If you're using bash as your shell, tox supports directory-name completion, e.g.:

`tox myproj[tab]`  will cause tox to match 'myproj' against the active index and print a list of matches, so that you can more easily complete directory names.

## The active index and index trees
<a name='active_index' />

By default, when `tox` runs the first time, it creates `~/.tox-index` and uses it as the "active" index.  However, you can have other indices: whenever you run `tox`, it does a search of parent directories for the current directory.  The first .tox-index encountered in that search becomes the active index and is the default list that will be searched for name matching.

This is useful if you have a project with several directories that are visited regularly and you wish to limit the scope of name matching to that project -- by placing a .tox-index file in the root of your project, you're effectively limiting the scope of the default search behavior.

## Using .tox-auto
If you run `tox --auto` in any directory, the directory will be added to the index and a `.tox-auto` file is created.  This file is a shell script with some comment metadata.  It offers the following features:

- Auto-shell init on change directory:
The `.tox-auto` script is automatically sourced by `tox` when you enter a directory that contains it.  This is useful if you like to initialize the shell with settings that are relevant to the project in that dir.


## TODO
These things have NOT been implemented yet:

* Bug - no cd if arg matches index entry exactly

* Add - Allow a '#rootpath=/parent/path' property in .tox-index, so that 
    a symlink to the index will be loadable from alien locations and correctly interpreted.

* Add .TAGS and .DESC support for .tox-auto

* Add 'add all child dirs'

* Add -i for 'print matching entries, plus info about each (# of names, last modified, contents of .tox-auto'

* Add 'prune all matches'

* Add "print matching dirs without prompt or fluff" (for use in scripts, etc.)

* Allow this:
    `tox bin /`
    "Search immediate ancestors "

* Allow this:
    `tox -a /etc/init.d`
    "Add an arbitrary dir to active index"




