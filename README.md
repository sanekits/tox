# tox: Quick directory-changer

The tox shell function provides a fast directory-change navigation tool.

The basic idea is that most directory-changes involve directories with long paths that you visit frequently, and it's better to do less typing to get there.

`tox` uses an index (which defaults to ~/.tox-index) to maintain a list of user-specified directories. You use wildcard matching to enter part of a directory name, and if there are multiple matches a menu is presented. 

If there's only 1 match, the change occurs immediately, and the previous directory is pushed onto the dirstack so that you can return quickly with `popd`.

#  (quick directory changing)

## Usage


## TODO
These things have NOT been implemented yet!

* Allow this:
    `tox bin //`
    "Search globally thru all indexes"

* Allow this:
    `tox bin /`
    "Search immediate ancestors "

* Allow this:
    `tox -a /etc/init.d`
    "Add an arbitrary dir to local index"



