# tox-completion.bash
# vim: filetype=sh :

# Recommended: source this from .bashrc 

# bash completion support for tox:
[[ -z $LmHome ]] && export LmHome=$HOME

use_tox_core=true

if [[ -d ${LmHome}/bin/tox-py ]]; then
    # tox_core is a python script:
    function tox {
        local newDir=$( $LmHome/bin/tox-py/tox_core.py $* )
        if [[ ! -z $newDir ]]; then
            if [[ "${newDir:0:1}" != "!" ]]; then
                pushd "$newDir" >/dev/null
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
    }
else
	function tox {
		echo "This function only works if ${LmHome}/bin/tox-py is present."
	}
fi

_tox()  # Here's our readline completion handler
{
    COMPREPLY=()
    local cur="${COMP_WORDS[COMP_CWORD]}"
    #echo "cur=[$cur]" >&2  Stub
    local toxfile=$(tox -q 2>&1 | egrep -m 1 '^Index' | awk '{print $2'})

    local opts="$(cat ${toxfile} | egrep -v '^#protect' )"

    COMPREPLY=( $(compgen -W "${opts}" -- ${cur}) )        
    return 0
}

complete -F _tox tox

