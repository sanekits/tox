#!/bin/bash

#!/bin/sh
# :vim filetype=sh :
#

set -ue

canonpath() {
    ( cd -L -- "$(dirname -- $0)"; echo "$(pwd -P)/$(basename -- $0)" )
}

Script=$(canonpath "$0")
Scriptdir=$(dirname -- "$Script")

red() {
    echo -en "\033[;31m$@\033[;0m"
}
green() {
    echo -en "\033[;32m$@\033[;0m"
}
yellow() {
    echo -en "\033[;33m$@\033[;0m"
}

die() {
    red "$@\n" >&2
    exit 1
}

init_homedir() {
    # This emits the script which is run as target $USER in container to initialize
    # their environment/home dir, etc.
    local CurUser="$1"
    cat <<-EXOF
echo "init_homedir($CurUser) starting:"
die() { echo "ERROR: \$@" >&2; exit 1; }
echo "HOME=\$HOME"
cd \$HOME || die 201
Src="\$(cd -)"
echo "Src=\$Src"
rsync -av \$Src/home.\$USER/ . || die 202
ln -sf /host-projects ./projects
echo "init_homedir: Ok"
EXOF
}

set +u
if [ -z "$sourceMe" ]; then
    set -u
    [[ -f /.dockerenv ]] || die "$Script should only run in docker container"
    [[ $UID == 0 ]] || die "$Script should run as root in container"
    [[ -f ./current_user_home ]] || die "Can't find $PWD/current_user_home.  Did you run container_prepare?"

    CurUser=$(cat current_user_home | cut -d'.' -f2)
    if [[ ! -d /home/$CurUser ]]; then
        useradd --create-home $CurUser || die useradd failed
        yellow "User $CurUser created in container\n"
    else
        yellow "User $CurUser already exists in container\n"
    fi
    su $CurUser --command /bin/bash - < <(init_homedir $CurUser)


    green "$(basename $Script): Ok\n"
fi
