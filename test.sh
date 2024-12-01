#!/usr/bin/env bash

this_dir=$(cd $(dirname $0) && pwd)

source ${this_dir}/env-diff-cmd.bash

_env-diff-test(){
    g(){
        echo "This is G"
    }
    printf "\n\033[1;35m------------------ TEST 1: Normal\033[0m\n"
    env-diff -F ${this_dir}/dot-config-env-diff.yml 'A=B;
    export X=Y;
    unset USER;
    f(){ echo "hello" ; };
    g(){ echo "This is new G" ; };
    declare -A assoc; assoc[y]=v;
    BASH_ALIASES[booggers]=balls;
    PATH=BANANNA:${PATH}:APPLE:;
    shopt -so errexit;
    shopt -u sourcepath;'
    printf "\n\033[1;35m------------------ TEST 2: Add colon to PATH\033[0m\n"
    env-diff -F ${this_dir}/dot-config-env-diff.yml 'PATH=${PATH}:'
    printf "\n\033[1;35m------------------ TEST 3: Add colon to PATH with --list-diff\033[0m\n"
    env-diff -F ${this_dir}/dot-config-env-diff.yml --list-diff 'PATH=${PATH}:'
    printf "\n\033[1;35m------------------ TEST 4: Normal with --no-ignore\033[0m\n"
    env-diff --no-ignore -F ${this_dir}/dot-config-env-diff.yml 'A=B;
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
