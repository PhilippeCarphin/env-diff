#!/bin/bash

_env_diff_completing_options(){
    # Previous words, excluding the first one which is
    # the command, and the last one
    for w in "${words[@]:1 :cword-1}" ; do
        if [[ "${w}" == -- ]] ; then
            return 1
        fi
    done

    # All previous non-command words are env-diff options
    # and if the current word doesn't start with '-', that's going to be
    # taken care of by the fact that the compgen command below will
    # return no matches and regular completion will take over.
    return 0
}

_env_diff_options=(
    --help
    -h
)

_env_diff_compare_options=(
    --no-ignore
    --keep-tmpdir
    --local-tmpdir
    --help
    -h
)
_env_diff_cmd_options=(
    --show-function-bodies
    --list-diff
    -F
)
_env_diff_cmd_arg_options=(
    -F
)
_env_diff_is_arg_option(){
    for o in "${_env_diff_cmd_arg_options[@]}" ; do
        if [[ "${o}" == "${1}" ]] ; then
            return 0
        fi
    done
    return 1
}

_env_diff(){
    local cur prev words cword
    _init_completion || return

    # Iterate on words before the one at index cword (note: cword is
    # for "cursor word", the index of the word containing the cursor)
    for ((i=1;i<cword;i++)) ; do
        if [[ "${words[i]}" == "--" ]] ; then
            return
        fi

        if _env_diff_is_arg_option "${words[i]}" ; then
            ((i++))
            continue
        fi

        if [[ "${words[i]}" == -* ]] ; then
            continue
        else
            # As soon as we spot a word on the command line that is
            # not an option and not the argument to an option
            # we are writing the COMMAND argument and completion should stop
            compopt -o default
            return
        fi
    done

    COMPREPLY=( $(compgen -W "${_env_diff_options[*]} ${_env_diff_cmd_options[*]} ${_env_diff_compare_options[*]}" -- ${cur}) )
}

_env_diff_compare(){
    local cur prev words cword
    _init_completion || return

    COMPREPLY=( $(compgen -W "${_env_diff_options[*]} ${_env_diff_compare_options[*]}" -- ${cur}) )
}

_env_diff_dash_dash_seen(){
    local arg
    for arg in "${words[@]:1:cword-1}" ; do
        if [[ "${arg}" == "--" ]] ; then
            return 0
        fi
    done
    return 1
}

complete -F _env_diff env-diff
complete -F _env_diff_compare env-diff-compare
