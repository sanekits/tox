#!/bin/bash
cd
ln -sf /app/tree-3 .
cd tree-3
source /app/tox-completion.bash
set -x
for dd in $(find . -name kkk); do
    ( cd $dd; tox_w -a $PWD; )
done
