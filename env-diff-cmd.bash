#!/bin/bash

_env_diff_root="$(cd -P $(dirname ${BASH_SOURCE[0]}) && pwd)"

# In case the command is `env-diff 'PATH=""'`
_env_diff_python_exec=$(which python3)
_env_diff_sort=$(which sort)
_env_diff_comm=$(which comm)
_env_diff_jq=$(which jq)
_env_diff_cut=$(which cut)
_env_diff_cat=$(which cat)


################################################################################
# Toplevel command.  This function is separate from _env_diff_internal simply
# to allow early returns in _env_diff_internal while still ensuring that the
# temporary directory gets deleted.
################################################################################
env-diff(){
    local _env_diff_tmpdir=$(mktemp -d tmp.XXXXXX)

    local -a _env_diff_compare_args=()
    local _env_diff_keep_tmpdir=false
    while [[ "$1" == -* ]] ; do
        case "$1" in
            --list-diff) _env_diff_compare_args+=(--list-diff); shift ;;
            --no-ignore) _env_diff_compare_args+=(--no-ignore); shift ;;
            --keep-tmpdir) _env_diff_keep_tmpdir=true ; shift ;;
            --) shift ; break ;;
            *) echo "env-diff: ERROR unknown argument '$1'" >&2 ; return 1 ;;
        esac
    done

    _env-diff-internal "$@"
    if ! ${_env_diff_keep_tmpdir} ; then
        rm -rf ${_env_diff_tmpdir}
    fi
}

################################################################################
# Main function of env-diff: We save everything, run the command, save everything
# again and finally run the python comparison script
################################################################################
_env-diff-internal(){

    if ! mkdir -p ${_env_diff_tmpdir}/before/functions ; then
        return 1
    fi

    if ! mkdir -p ${_env_diff_tmpdir}/after/functions ; then
        return 1
    fi

    if ! _env-diff-save_all_info ${_env_diff_tmpdir}/before ; then
        echo "ERROR saving initial info" >&2
        return 1
    fi

    if ! (

        if ! eval "$@" ; then
            echo "Command '$*' failed" >&2
            return 1
        fi

        if ! _env-diff-save_all_info ${_env_diff_tmpdir}/after ; then
            echo "ERROR saving final info" >&2
            return 1
        fi

    ) ; then return 1 ; fi

    if ! ${_env_diff_python_exec} ${_env_diff_root}/env-diff-compare.py "${_env_diff_compare_args[@]}" "${_env_diff_tmpdir}/before" "${_env_diff_tmpdir}/after" ; then
        echo "ERROR in python comparison script" >&2
        return 1
    fi
}

################################################################################
# Saving all info to files inside $1.
################################################################################
_env-diff-save_all_info(){
    compgen -v | ${_env_diff_sort} >$1/all_vars.txt || return 1
    compgen -e | ${_env_diff_sort} >$1/env_vars.txt || return 1
    compgen -A arrayvar | ${_env_diff_sort} >$1/arrays.txt || return 1# includes associative arrays
    declare -A | ${_env_diff_cut} -d ' ' -f 3 | ${_env_diff_cut} -d = -f 1 | ${_env_diff_sort} > $1/assoc_arrays.txt || return 1

    # Shell variables = all_vars - env_vars - array_vars
    ${_env_diff_comm} -23 $1/all_vars.txt $1/env_vars.txt > $1/no_env.txt || return 1
    ${_env_diff_comm} -23 $1/no_env.txt $1/arrays.txt > $1/shell_vars.txt || return 1

    # Normal arrays = array_vars - assoc_arrays
    ${_env_diff_comm} -23 $1/arrays.txt $1/assoc_arrays.txt > $1/normal_arrays.txt || return 1

    # Dump all variables to JSON
    ${_env_diff_python_exec} -c "import os,json ; print(json.dumps(dict(os.environ)))" >$1/env_vars.json || return 1
    <$1/shell_vars.txt _env-diff-shell_vars_to_json > $1/shell_vars.json || return 1
    <$1/assoc_arrays.txt _env-diff_assoc_arrays_to_json > $1/assoc_arrays.json || return 1
    <$1/normal_arrays.txt _env-diff_normal_arrays_to_json > $1/normal_arrays.json || return 1

    # Save all functions to individual files
    declare -F | ${_env_diff_cut} -d ' ' -f 3 | ${_env_diff_sort} > $1/func_names.txt || return 1
    while read f ; do
        type ${f} > $1/functions/BASH_FUNC_${f}.bash || return 1
    done < $1/func_names.txt

    # Save shell options
    shopt > $1/shopt.txt || return 1
    shopt -o > $1/shopt_set.txt || return 1
}

################################################################################
# Save all shell variables as JSON.  Code for JQ was found in this answer on
# stack overflow https://stackoverflow.com/a/44792751/5795941
#
# NOTE: Mine is different from the answer in that I use '(length-1)/2' instead
# of 'length/2'.  For me the trailing \0 after the last element puts an empty
# string at the end of the input stream: With length/2 the BASH array
# ([a]=b # [c]=d) leads to an output of a\0b\0c\0d\0 which leads to the array
# [a, b, c, d, ''] which leads to the JSON : {"a":"b", "c":"d", "":null}.
# Each of the following functions uses JQ uses almost the same code
#
# In this function we use _env_diff_shell_var_name as the iteration variable
# to avoid collisions with other variables.  This is not necessary in the
# other _env-diff_*_to_json functions because they are not saving shell
# variables.  The use of a name like i or _i would not be good because one
# use for this tool is to detect variables that should be made local and doing
# for((i=0;i<8;i++)) is the most frequent way I inadvertantly create a global
# variable.
################################################################################
_env-diff-shell_vars_to_json(){
    local _env_diff_shell_var
    while read _env_diff_shell_var ; do
        printf "%s\0%s\0" "${_env_diff_shell_var}" "${!_env_diff_shell_var}"
    done | ${_env_diff_jq} -Rs 'split("\u0000")
                    | . as $a
                    | reduce range(0;(length-1)/2) as $i
                     ({}; . + {($a[2*$i]): ($a[2*$i + 1])})'
}

################################################################################
# Dump all associative arrays to a single JSON object.
# Keys are array identifiers and values are the associative arrays themseles
# converted to JSON.
################################################################################
_env-diff_assoc_arrays_to_json(){
    printf "{\n"
    local first=true
    local name
    while read name ; do
        if [[ "${name}" == "" ]] ; then
            continue
        fi
        local -n ref=${name}
        # Ensure no comma after the last element by putting one before
        # each element except the first one
        if ! ${first} ; then
            printf ","
        fi
        printf "\n    \"%s\": " "${name}"
        for k in "${!ref[@]}" ; do
            printf "%s\0%s\0" "${k}" "${ref[$k]}"
        done | ${_env_diff_jq} -Rs 'split("\u0000")
                        | . as $a
                        | reduce range(0;(length-1)/2) as $i
                        ({}; . + {($a[2*$i]): ($a[2*$i + 1])})'
        first=false
    done
    printf "}"
}

################################################################################
# Dump all normal arrays to JSON:
# Keys are array identifiers and values are the arrays themselves as JSON arrays
################################################################################
_env-diff_normal_arrays_to_json(){
    printf "{\n"
    local first=true
    local name
    while read name ; do
        local -n ref=${name}
        if ! ${first} ; then
            printf ","
        fi
        printf "\n    \"%s\": " "${name}"
        for v in "${ref[@]}" ; do
            printf "%s\0" "${v}"
        done | ${_env_diff_jq} -Rs 'split("\u0000")
                       | . as $a
                       | reduce range(0;length-1) as $i
                         ([] ; . + ([$a[$i]]))'
        first=false
    done
    printf "}"
}

################################################################################
# Run a simple test to manually confirm that most parts are working
################################################################################
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
}
if [[ "$1" != "" ]] ; then _env-diff-test ; fi
