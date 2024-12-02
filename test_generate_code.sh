#!/usr/bin/env bash
set -uEo pipefail
shopt -s inherit_errexit

source ./env-diff-cmd.bash

tmpdir=$(mktemp -d tmp.test-gencode.XXXXXX)

alias ls='ls --hello=world'
shopt -s expand_aliases
test_log(){
    printf "\033[1;35m$0: %s\033[0m\n" "$*" >&2
}

(
    test_log "saving ${tmpdir}/before"
    env-diff-save ${tmpdir}/before

    test_log "Changing environment"
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

    test_log "saving ${tmpdir}/after"
    env-diff-save ${tmpdir}/after
)

python3 env-diff-generate-code.py ${tmpdir}/before ${tmpdir}/after > ${tmpdir}/diff.sh

source ${tmpdir}/diff.sh
env-diff-save ${tmpdir}/after-source

diff="$(env-diff-compare -F /dev/null ${tmpdir}/after ${tmpdir}/after-source)"
if [[ -z "${diff}" ]] ; then
    test_log "SUCCESS: No differences"
else
    test_log "Potential failure: there were some differences:"
    test_log "${diff}"
fi



