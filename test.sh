#!/usr/bin/env bash

this_dir=$(cd $(dirname $0) && pwd)

source ${this_dir}/env-diff-cmd.bash

_env-diff-test(){
    g(){
        echo "This is G"
    }
    echo "------------------ TEST 1"
    env-diff 'A=B;
    export X=Y;
    unset USER;
    f(){ echo "hello" ; };
    g(){ echo "This is new G" ; };
    declare -A assoc; assoc[y]=v;
    BASH_ALIASES[booggers]=balls;
    PATH=BANANNA:${PATH}:APPLE:;
    shopt -so errexit;
    shopt -u sourcepath;'
    echo "------------------ TEST 2"
    env-diff 'PATH=${PATH}:'
    echo "------------------ TEST 3"
    env-diff --list-diff 'PATH=${PATH}:'
    echo "------------------ TEST 4"
    env-diff --no-ignore -F ${_env_diff_root}/dot-config-env-diff.yml 'A=B;
    export X=Y;
    unset USER;
    f(){ echo "hello" ; };
    g(){ echo "This is new G" ; };
    declare -A assoc; assoc[y]=v;
    BASH_ALIASES[booggers]=balls;
    PATH=BANANNA:${PATH}:APPLE:;
    shopt -so errexit;
    shopt -u sourcepath;'
}

_env-diff-test
