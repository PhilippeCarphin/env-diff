
if ! (return 0 2>/dev/null) ; then
    echo "This script must be sourced and should not have execute permissions"
    exit 1;
fi

_env_diff_root="$(cd -P $(dirname ${BASH_SOURCE[0]}) && pwd)"
_env_diff_cmd=""
_env_diff_log(){
    local level=$1 ; shift
    local color
    case ${level} in
        INTERNAL_ERROR) color=$'\033[1;41;37m' ;;
        ERROR) color=$'\033[1;31m' ;;
        WARNING) color=$'\033[33m' ;;
        INFO) color=$'\033[35m' ;;
        DEBUG) color=$'\033[36m' ;;
        *) _env_diff_log ERROR "Unknown log level ${level}" ; return 1 ;;
    esac
    local format="[${_env_diff_cmd} ${color}${level}\033[0m] %s\n"
    if [[ ${level} == DEBUG ]] ; then
        format="[${_env_diff_cmd} ${color}${level}\033[0m - ${FUNCNAME[1]}] %s\n"
    fi
    printf "${format}" "$*" >&2
}

_env-diff-short_help(){
    cat <<- EOF
		env-diff [options] COMMAND

		    Display the effect of COMMAND on the shell environment: exported
		    variables, unexported variables, arrays, associative arrays, shell
		    functions, shell options and traps.

		OPTIONS
		    --list-diff             Use diff for list comparison
		    --no-ignore             Bypass ignoring of variables
		    -F CONFIG FILE          Use alternate config file
		    --keep-tmpdir           Do not delete temp dir after running
		    --local-tmpdir          Create temp dir in PWD
		    --help                  Display manpage for env-diff
		    --show-function-bodies  Show code of modified/added functions
		    -h                      Display this help text and exit
	EOF
}

################################################################################
# Toplevel command.  This function is separate from _env_diff_internal simply
# to allow early returns in _env_diff_internal while still ensuring that the
# temporary directory gets deleted.
################################################################################
env-diff(){
    local -a _env_diff_compare_args=()
    local _env_diff_keep_tmpdir=false
    local _env_diff_local_tmpdir=false
    local _env_diff_cmd=env-diff

    local _env_diff_python3=""
    local _env_diff_sort=""
    local _env_diff_comm=""
    local _env_diff_jq=""
    local _env_diff_cut=""
    local _env_diff_cat=""
    local _env_diff_mkdir=""
    local _env_diff_jq_length_str=""
    local _env_diff_the_cmd

    if ! _env-diff-setup ; then
        return 1;
    fi

    while [[ "$1" == -* ]] ; do
        case "$1" in
            --list-diff) _env_diff_compare_args+=(--list-diff); shift ;;
            --no-ignore) _env_diff_compare_args+=(--no-ignore); shift ;;
            -F)          _env_diff_compare_args+=(-F $2); shift ; shift ;;
            --keep-tmpdir) _env_diff_keep_tmpdir=true ; shift ;;
            --local-tmpdir) _env_diff_local_tmpdir=true ; shift ;;
            --help) man ${_env_diff_root}/manpages/env-diff.1 ; return 0 ;;
            --show-function-bodies) _env_diff_compare_args+=(--show-function-bodies) ; shift ;;
            -h) _env-diff-short_help ; return 0 ;;
            --) shift ; break ;;
            *) _env_diff_log ERROR "unknown argument '$1'"
               _env-diff-short_help ; return 1 ;;
        esac
    done

    _env_diff_the_cmd=("$@")
    set --
    local _env_diff_tmpdir
    if ${_env_diff_local_tmpdir} ; then
        _env_diff_tmpdir=$(mktemp -d tmp.env-diff.XXXXXX) || return 1
    else
        _env_diff_tmpdir=$(mktemp -d) || return 1
    fi
    _env_diff_log INFO "tmpdir in '${_env_diff_tmpdir}'"

    _env-diff-internal

    if ! ${_env_diff_keep_tmpdir} ; then
        local cmd=(rm -rf "${_env_diff_tmpdir}")
        _env_diff_log INFO "Deleting tmpdir '${cmd[*]}'"
        "${cmd[@]}"
    fi
}

env-diff-gencode(){
    if [[ $1 == -h ]] ; then
        cat <<-EOF
			usage: ${FUNCNAME[0]} [-h|--help] [--debug] [--output FILE] BEFORE AFTER

			    Generate shell code to go from environment BEFORE to environment AFTER
			    where BEFORE and AFTER are directories created with env-diff-save.

			Options:

			    -h                Print short help
			    --help            Show manpage
			    --debug           Set log level to debug
			    --output FILE     Set ouput to FILE (default is STDOUT)
		EOF
        return
    elif [[ $1 == --help ]] ; then
        man ${_env_diff_root}/manpages/env-diff-gencode.1
        return
    fi

    local _env_diff_cmd=env-diff-gencode
    env _env_diff_cmd=${_env_diff_cmd} python3 ${_env_diff_root}/env-diff-generate-code.py "$@"
}

env-diff-load(){
    if [[ $1 == -h ]] ; then
        cat <<-EOF
			usage: ${FUNCNAME[0]} [-h|--help] [--debug] DIR

			    Load environment DIR where DIR is a saved environment created
			    with env-diff-save

			Options:

			    -h                Print short help
			    --help            Show manpage
			    --debug           Set log level to debug
		EOF
        return
    elif [[ $1 == --help ]] ; then
        man ${_env_diff_root}/manpages/env-diff-load.1
        return
    fi
    local _env_diff_cmd=env-diff-load

    local _env_diff_tmpdir=$(mktemp -d tmp.env-diff-load.XXXXXX) || return 1
    _env_diff_log INFO "Using tmpdir=${_env_diff_tmpdir} to save current environment"
    env-diff-save "${_env_diff_tmpdir}/current" || return 1
    _env_diff_log INFO "Generating code to go from ${_env_diff_tmpdir}/current to $1"
    if [[ $1 == --debug ]] ; then
        shift
        env-diff-gencode "${_env_diff_tmpdir}/current" --debug "$1" > ${_env_diff_tmpdir}/to_source
        _env_diff_log DEBUG "sourcing ${_env_diff_tmpdir}/to_source"
        source ${_env_diff_tmpdir}/to_source
    else
        env-diff-gencode "${_env_diff_tmpdir}/current" "$1" > ${_env_diff_tmpdir}/to_source
        source ${_env_diff_tmpdir}/to_source
        _env_diff_log INFO "Deleting tmpdir=${_env_diff_tmpdir}"
        rm -rf "${_env_diff_tmpdir}"
    fi
}

################################################################################
# Main function of env-diff: We save everything, run the command, save everything
# again and finally run the python comparison script
################################################################################
_env-diff-internal(){

    if ! (
        # Save initial info inside the same subshell as where for variables
        # like BASHPID and BASH_SUBSHELL to be the same
        ${_env_diff_mkdir} ${_env_diff_tmpdir}/before || return 1
        if ! _env-diff-save_all_info ${_env_diff_tmpdir}/before ; then
            _env_diff_log ERROR "saving initial info"
            return 1
        fi

        _env_diff_log INFO "Running command '$*'"
        # See Notes/eval-command/ about why we don't just do 'eval "$@"'
        if ! eval "${_env_diff_the_cmd[@]}" ; then
            _env_diff_log INFO "Command '${cmd[*]}' returned non-zero return code"
        fi

        ${_env_diff_mkdir} -p ${_env_diff_tmpdir}/after || return 1
        if ! _env-diff-save_all_info ${_env_diff_tmpdir}/after ; then
            _env_diff_log ERROR "saving final info"
            return 1
        fi

        #
        # Deactivate the exit trap (only affects this subshell).  Normally
        # an EXIT trap is not run when a subshell exits.  However if an EXIT
        # trap is set WITHIN a subshell, then it IS run when that subshell
        # exits.  The command above may contain code that sets an EXIT trap.
        # Therefore we deactivate it here.
        #
        # We do this after saving everything so that info on traps can be added
        # in the future
        #
        trap - EXIT

    ) ; then return 1 ; fi

    if ! ${_env_diff_python3} ${_env_diff_root}/env-diff-compare.py \
            "${_env_diff_compare_args[@]}" \
            "${_env_diff_tmpdir}/before" "${_env_diff_tmpdir}/after" ; then
        _env_diff_log ERROR "in python comparison script"
        return 1
    fi
}

env-diff-compare(){
    local _env_diff_cmd=env-diff-compare
    if [[ $1 == --help ]] ; then
        man ${_env_diff_root}/manpages/env-diff-compare.1
        return
    fi
    env _env_diff_cmd=${_env_diff_cmd} python3 ${_env_diff_root}/env-diff-compare.py "$@"
}

_env-diff-setup(){
    # We are saving paths to all programs because the command we are trying
    # may mess some things up.  The use of jq, python3, ... in the second
    # call to _env-diff_save_all_info would not be found.
    local -n nameref
    for nameref in _env_diff_python3 _env_diff_sort _env_diff_comm _env_diff_jq _env_diff_cut _env_diff_cat _env_diff_mkdir ; do
        local program=${!nameref##_env_diff_}
        # Check if variable exists regardless of it being empty or non-empty.
        # Note: bash 3 (the version that comes with MacOS) does not have [[ -v
        # VARNAME ]] so we have to do it with declare.
        if ! declare -p ${!nameref} >/dev/null 2>&1 ; then
            _env_diff_log INTERNAL_ERROR "The variable '${!nameref}' must be declared in the calling scope"
            return 1
        fi

        if ! nameref=$(which ${program} 2>/dev/null) ; then
            _env_diff-log ERROR "Program ${program} not found in PATH : required for operation"
            return 1
        fi
    done

    if ! [[ -v _env_diff_jq_length_str ]] ; then
        _env_diff_log INTERNAL_ERROR "The variable '_env_diff_jq_length_str' must be declared in the calling scope"
        return 1
    fi
    _env_diff_jq_length_str=$(
        jq_version=$(${_env_diff_jq} --version)
        minor_patch=${jq_version#*.}
        minor=${minor_patch%%.*}
        if (( ${minor} < 7 )) ; then
            echo "(length-0.5)"
        else
            echo "(length-1)"
        fi
    )
}

env-diff-save(){
    # Declarations must be followed by `=""` so that the test '[[ -v .... ]]'
    # will say that it the variable is declared
    local _env_diff_cmd=env-diff-save
    local _env_diff_python3=""
    local _env_diff_sort=""
    local _env_diff_comm=""
    local _env_diff_jq=""
    local _env_diff_cut=""
    local _env_diff_cat=""
    local _env_diff_mkdir=""
    local _env_diff_jq_length_str=""

    if ! _env-diff-setup ; then
        return 1
    fi

    if [[ "$1" == -h ]] ; then
        cat <<-EOF
			${FUNCNAME[0]} DIR

			Save all info for use by env-diff-compare.
			Run \`env-diff-save --help\` for more information
		EOF
        return 0
    elif [[ "$1" == --help ]] ; then
        man ${_env_diff_root}/manpages/env-diff-save.1
        return 0
    fi

    if (( $# != 1 )) ; then
        ${FUNCNAME[0]} -h
        _env_diff_log ERROR "This function takes exactly one argument"
        return 1
    fi

    if [[ -e "$1" ]] ; then
        _env_diff_log ERROR "Cannot create save directory '$1': already exists"
        return 1
    fi

    if ! mkdir "$1" ; then
        _env_diff_log ERROR "Could not create directory '$1'"
        return 1
    fi

    _env-diff-save_all_info "$1"
}

################################################################################
# Saving all info to files inside $1.
################################################################################
_env-diff-save_all_info(){
    compgen -v | ${_env_diff_sort} >$1/all_vars.txt || return 1
    compgen -e | ${_env_diff_sort} >$1/env_vars.txt || return 1
    compgen -A arrayvar | ${_env_diff_sort} >$1/arrays.txt || return 1# includes associative arrays
    declare -A | ${_env_diff_cut} -d ' ' -f 3 | ${_env_diff_cut} -d = -f 1 | ${_env_diff_sort} > $1/assoc_arrays.txt || return 1

    # Shell variables = all_vars - env_vars - array_vars - assoc_arrays
    # Note: In BASH 5+ compgen -A arrayvar includes associative arrays so only
    # the first two lines would be necessary here, however in BASH4, it does not
    # so we have to remove arrays.txt and assoc_arrays.txt.
    # I.E. the 3rd line is necessary in BASH4 but not in BASH5
    ${_env_diff_comm} -23 $1/all_vars.txt $1/env_vars.txt > $1/no_env.txt || return 1
    ${_env_diff_comm} -23 $1/no_env.txt $1/arrays.txt > $1/no_arrays.txt || return 1
    ${_env_diff_comm} -23 $1/no_arrays.txt $1/assoc_arrays.txt > $1/shell_vars.txt || return 1

    # Normal arrays = array_vars - assoc_arrays
    # NOTE: In BASH4, compgen -A arrayvar gives just the normal arrays but in
    # BASH5, it includes associative arrays.  Therefore to be sure we subtract
    # associative arrays in case arrays.txt includes associative ones.
    # I.E. this line is necessary in BASH5 but not in BASH4
    ${_env_diff_comm} -23 $1/arrays.txt $1/assoc_arrays.txt > $1/normal_arrays.txt || return 1

    # Dump all variables to JSON
    ${_env_diff_python3} -c "import os,json ; print(json.dumps(dict(os.environ)))" >$1/env_vars.json || return 1
    <$1/shell_vars.txt _env-diff-shell_vars_to_json > $1/shell_vars.json || return 1
    <$1/assoc_arrays.txt _env-diff-assoc_arrays_to_json > $1/assoc_arrays.json || return 1
    <$1/normal_arrays.txt _env-diff-assoc_arrays_to_json > $1/normal_arrays.json || return 1

    # Save all functions to individual files
    ${_env_diff_mkdir} "$1/functions" || return 1
    compgen -A function | ${_env_diff_sort} > $1/func_names.txt || return 1
    local f
    while read f ; do
        declare -f ${f} > $1/functions/BASH_FUNC_${f}.bash || return 1
    done < $1/func_names.txt

    # Save shell options
    shopt > $1/shopt.txt || return 1
    shopt -o > $1/shopt_set.txt || return 1

    # Traps
    _env-diff-traps_to_json >$1/traps.json
}

################################################################################
# Save all shell variables as JSON.  Code for JQ was found in this answer on
# stack overflow https://stackoverflow.com/a/44792751/5795941
#
# Because the splitting behavior is dependant on the version, we use (length-1)
# or (length) based on the version: length for versions below 1.7 and (length-1)
# for versions equal to or above 1.7.  The _env_diff_jq_length_str variable
# is used for all 3 functions that use jq.
#
# I left a comment on the linked answer
################################################################################
_env-diff-shell_vars_to_json(){
    local _env_diff_shell_var
    while read _env_diff_shell_var ; do
        printf "%s\0%s\0" "${_env_diff_shell_var}" "${!_env_diff_shell_var}"
    done | ${_env_diff_jq} -Rs 'split("\u0000")
                    | . as $a
                    | reduce range(0;'${_env_diff_jq_length_str}'/2) as $i
                     ({}; . + {($a[2*$i]): ($a[2*$i + 1])})'
}

################################################################################
# Dump all associative arrays to a single JSON object.
# Keys are array identifiers and values are the associative arrays themseles
# converted to JSON.
################################################################################
_env-diff-assoc_arrays_to_json(){
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
                        | reduce range(0;(length/2)-0.5) as $i
                        ({}; . + {($a[2*$i]): ($a[2*$i + 1])})'
        # The lenght/2 - 0.5 does what I want for any version of JQ.  For 1.7+
        # the length will be say 7 for an assoc array with 3 key-value pairs
        # and 7/2 - 0.5 will be 3 so $i will do 0,1,2.
        # And for jq 1.6-, the length will be 6 and 6/2 - 0.5 will be 2.5 and
        # because of how it works in JQ, because 2.5 is greater than 2, the
        # index 2 will be included in the iteration so $i will also do 0,1,2.
        # I'm not sure how JQ works, but this is how I make sense of why
        # (length/2)-0.5 works for both versions.
        first=false
    done
    printf "}"
}

################################################################################
# Dump all normal arrays to JSON:
# Keys are array identifiers and values are the arrays themselves as JSON arrays
################################################################################
_env-diff-normal_arrays_to_json(){
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
                       | reduce range(0;'${_env_diff_jq_length_str}') as $i
                         ([] ; . + ([$a[$i]]))'
        first=false
    done
    printf "}"
}

################################################################################
# Save traps to JSON.  Save the special bash only traps ERR, EXIT, DEBUG, RETURN
# and save all the traps for UNIX signals from signals.h.  Since these numbers
# are not the same on all systems but they seem to always be sequencial, we just
# check signals starting at 1 and incrementing by 1 until the trap command
# returns a non-zero exit code.
################################################################################
_env-diff-traps_to_json(){
    local t s
    {
        for s in ERR EXIT DEBUG RETURN ; do
            t="$(trap -p $s)"
            if [[ "${t}" == "" ]] ; then
                continue
            fi
            eval arr=("${t}")
            if (( ${#arr[@]} == 4 )) ; then
                printf "%s\0%s\0" "${arr[3]}" "${arr[2]}"
            else
                echo "env-diff: ERROR: Could not extract trap for signal '${s}'" >&2
                return 1
            fi
        done

        # Traps for the signals from signal.h
        # We could use `for t in $(trap -l | sed 's/) [^ \t]*/\n/g') ; do...`
        # but assuming there are no gaps in signal numbers, just going until
        # trap returns non-zero is simple
        local n=1
        while true ; do
            if ! t="$(trap -p ${n} 2>/dev/null)"; then
                # printf "Breaking at number ${n}" >&2
                break
            fi
            ((n++))
            if [[ "${t}" == "" ]] ; then
                continue
            fi
            eval arr=("${t}")
            if (( ${#arr[@]} == 4 )) ; then
                printf "%s\0%s\0" "${arr[3]}" "${arr[2]}"
            else
                echo "env-diff: ERROR: Could extract trap for signal '${n}'" >&2
                return 1
            fi
        done
    } | ${_env_diff_jq} -Rs 'split("\u0000")
                       | . as $a
                       | reduce range(0;'${_env_diff_jq_length_str}'/2) as $i
                         ({}; . + {($a[2*$i]): ($a[2*$i + 1])})'
}

source ${_env_diff_root}/env-diff-completion.bash
