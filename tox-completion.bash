# tox-completion.bash
# vim: filetype=sh :

# Recommended: source this from .bashrc 

# Requires: you have a ~/bin/tox-py directory containing tox_core.py, or
# you set $TOXHOME=[dir] before sourcing tox-completion.bash


# bash completion support for tox:
[[ -z $LmHome ]] && export LmHome=$HOME

[[ -z $TOXHOME ]] && TOXHOME=${LmHome}/bin/tox-py


if [[ -f ${TOXHOME}/tox_core.py ]]; then
    # tox_core is a python script:

    function tox_cd_enter {
        local newDir=$1
        # When entering a directory, look for the '.tox-auto' file:
        if [[ $PWD ==  $newDir ]]; then
            return
        fi
        pushd "$newDir" >/dev/null
        if [[ -f ./.tox-auto ]]; then
            # Before we source this, we want to figure out if it's a null operation, otherwise we'll
            # print a meaningless sourcing message.
            if [[ $( egrep -v '^#' ./.tox-auto ) == "" ]]; then
                return  # Yes, there's a .tox-auto, but it has no initialization logic, it's just comments
            fi
            echo -n "   (tox sourcing ./.tox-auto: [" >&2
            source ./.tox-auto
            echo "] DONE)" >&2
        fi
    }

    function tox_w {
        # The tox alias invokes tox_w: Our job is to pass args to
        # tox_core.py, and then decide whether we're supposed to change dirs,
        # print the result, or execute the command returned.
        local newDir=$( $TOXHOME/tox_core.py $* )
        if [[ ! -z $newDir ]]; then
            if [[ "${newDir:0:1}" != "!" ]]; then
                # We're supposed to change to the dir identified:
                tox_cd_enter "$newDir"
            else
                if [[ "${newDir:0:2}" == "!!" ]]; then
                    # A double !! means "run this"
                    eval "${newDir:2}"
                else
                    # A single bang means "print this"
                    echo "${newDir:1}"
                fi
            fi
        fi
        set +f
    }
    alias tox='set -f;tox_w'
    alias to='set -f;tox_w'
    alias toxr='set -f; tox_w --report td'
    alias toa='toxa'
    alias tod='toxd'

    function toxa { # Add current directory to ~/.tox-index, works for out-of-tree dirs also
                    # TODO: change the python to do this by default
        if /bin/egrep -q "^${PWD}\$" ~/.tox-index 2>/dev/null ; then
            echo "$PWD is already in ~/.tox-index"
            return
        fi
        echo $PWD >> ~/.tox-index
        sort -u ~/.tox-index | cat > ~/.tox-index
        echo "$(pwd) added to ~/.tox-index"
    }
    function toxd { # Remove current dir from ~/.tox-index, works out-of-tree
                    # TODO: change the python to do this by default
        if ! /bin/egrep -q "^${PWD}\$" ~/.tox-index 2>/dev/null ; then
            echo "$PWD is not in ~/.tox-index"
            return
        fi
        /bin/egrep -v "^${PWD}\$" ~/.tox-index 2>/dev/null | cat > ~/.tox-index
        echo "$(pwd) removed from ~/.tox-index"
    }
else
	function tox {
		echo "This function only works if \$TOXHOME/tox_core.py exists."
	}
    alias toxa=tox
    alias toxd=tox
fi

_tox()  # Here's our readline completion handler
{
    COMPREPLY=()
    local cur="${COMP_WORDS[COMP_CWORD]}"

    local toxfile=$(tox -q 2>&1 | egrep -m 1 '^Index' | awk '{print $2'})

    local opts="$(cat ${toxfile} | egrep -v '^#protect' )"

    COMPREPLY=( $(compgen -W "${opts}" -- ${cur}) )        
    return 0
}

complete -F _tox tox

