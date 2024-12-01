#!/usr/bin/env bash
set -euEo pipefail
shopt -s inherit_errexit

source ./env-diff-cmd.bash

tmpdir=$(mktemp -d codegen.tmpXXXXXX)

alias ls='ls --hello=world'
shopt -s expand_aliases

(
    echo "saving ${tmpdir}/before"
    env-diff-save ${tmpdir}/before

    echo "Changing environment"
    A=B;
    export X=Y;
    export -n HOME
    unset USER;
    f(){ echo "hello" ; };
    g(){ echo "This is new G" ; };
    declare -A assoc; assoc[y]=v;
    BASH_ALIASES[say-hello]='echo "HELLO"';
    alias say-hello='echo "HELLO WORLD"';
    unalias ls
    PATH=BANANNA:${PATH}:APPLE:;
    shopt -so errexit;
    shopt -u sourcepath;

    echo "saving ${tmpdir}/after"
    env-diff-save ${tmpdir}/after
)

python3 env-diff-generate-code.py ${tmpdir}/before ${tmpdir}/after > ${tmpdir}/diff.sh

source ${tmpdir}/diff.sh
env-diff-save ${tmpdir}/after-source

diff="$(env-diff-compare -F /dev/null ${tmpdir}/after ${tmpdir}/after-source)"
if [[ -z "${diff}" ]] ; then
    echo "SUCCESS: No differences"
else
    echo "Potential failure: there were some differences:"
    echo "${diff}"
fi



