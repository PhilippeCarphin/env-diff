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
    --show-function-bodies
    --list-diff
    -F
    --debug
)
_env_diff_cmd_options=(
)
_env_diff_cmd_arg_options=(
    -F
)
_env_diff_gencode_options=(
    --help
    --debug
)
_env_diff_load_options=(
    --help
    --debug
)
_env_diff_is_arg_option(){
    local o
    for o in "${_env_diff_cmd_arg_options[@]}" ; do
        if [[ "${o}" == "${1}" ]] ; then
            return 0
        fi
    done
    return 1
}

_env_diff_get_completion_func(){
    local cmd=$1
    local compspec
    if ! compspec=($(complete -p ${cmd} 2>/dev/null)) ; then
        if declare -F _completion_loader >/dev/null 2>&1 ; then
            _completion_loader ${cmd}
            echo _completion_loader ${cmd} >> ~/.log.txt
            complete -p ${cmd} &>> ~/.log.txt
        fi
        if ! compspec=($(complete -p ${cmd})) ; then
            return 1
        fi
    fi
    for ((i=1;i<${#compspec[@]};i++)) ; do
        case ${compspec[i]} in -F) comp_func=${compspec[i+1]} ; return 0 ;; esac
    done
}

_env_diff(){
    local cur prev words cword
    _init_completion || return

    local posargs=()
    # Iterate on words before the one at index cword (note: cword is
    # for "cursor word", the index of the word containing the cursor)
    local i
    for ((i=1;i<=cword;i++)) ; do
        if [[ "${words[i]}" == "--" ]] ; then
            return
        fi

        if _env_diff_is_arg_option "${words[i]}" ; then
            # current word is an option that takes an argument,
            # don't count the next word
            ((i++))
            continue
        fi

        if [[ "${words[i]}" == -* ]] ; then
            # Current argument is an option
            continue
        fi
        posargs+=("${words[i]}")
    done
    if [[ ${cur} != -* ]] ; then
        if ((${#posargs[@]} == 1)) ; then
            COMPREPLY=($(compgen -c -- ${cur}))
        else
            local comp_func
            if _env_diff_get_completion_func ${posargs[0]} ; then
                COMP_WORDS=("${posargs[@]}")
                COMP_CWORD=$((${#posargs[*]}-1))
                echo ${comp_func} "${cmd}" "${posargs[-1]:-}" "${posargs[-2]:-}" >> ~/.log.txt
                ${comp_func} "${cmd}" "${posargs[-1]:-}" "${posargs[-2]:-}"
                return
            fi
            compopt -o default
        fi
    fi

    COMPREPLY+=( $(compgen -W "${_env_diff_options[*]} ${_env_diff_cmd_options[*]} ${_env_diff_compare_options[*]}" -- ${cur}) )
}

_env_diff_compare(){
    local cur prev words cword
    _init_completion || return

    if [[ ${cur} == -* ]] ; then
        COMPREPLY=( $(compgen -W "${_env_diff_options[*]} ${_env_diff_compare_options[*]}" -- ${cur}) )
    fi
    _filedir -d
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

_env_diff_gencode(){
    local cur prev words cword
    _init_completion || return

    if [[ ${cur} == -* ]] ; then
        COMPREPLY=( $(compgen -W "${_env_gencode_options[*]}" -- ${cur}) )
    fi
    _filedir -d
}

_env_diff_load(){
    local cur prev words cword
    _init_completion || return

    if [[ ${cur} == -* ]] ; then
        COMPREPLY=( $(compgen -W "${_env_load_options[*]}" -- ${cur}) )
    fi
    _filedir -d
}

complete -F _env_diff env-diff
complete -o default -F _env_diff_compare env-diff-compare
complete -o default -F _env_diff_gencode env-diff-gencode
complete -o default -F _env_diff_load env-diff-load
