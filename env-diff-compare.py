import os
import json
import sys
import difflib
import re
import argparse
import envdiff
import envdifflogging
import logging

envdifflogging.configureLogging()

have_yaml = False
try:
    import yaml
    have_yaml = True
except:
    logging.warning(f"The python package 'pyyaml' could not be imported.  It can be installed with `python3 -m pip install [--user] pyyaml`.  No config file will be loaded (see 'env-diff --help' for more info)")
    pass

try:
    import pygments
    import pygments.formatters
    import pygments.lexers.shell
    import pygments.styles
    import pygments.token
except:
    pass

DESCRIPTION = """
    Report the difference caused on the shell environment by a command.

    The shell function env-diff() is the driver for this.  It saves everything
    about the environment before and after the command in JSON files in a
    temporary directory and calls this program to load those files and print
    a report.

    Custom comparison and display functions are used for some environment
    variables.  Variables that are known to be colon-delimited lists are
    compared as python sets to display elements that have been added or
    removed.  This has the drawback that if we modify PATH by adding something
    that was already there, it won't show in the report even if PATH was
    modified. 

    Run `env-diff --help` for more information.
"""
comparison_functions = {}
display_functions = {}
ignored_variables = set()
ignored_normal_arrays = set()
ignored_assoc_arrays = set()
colon_lists = set()
space_lists = set()
def get_args():
    global ignored_variables
    global ignored_normal_arrays
    global ignored_assoc_arrays
    global colon_lists
    global space_lists

    if '_env_diff_cmd' in os.environ:
        sys.argv[0] = os.environ['_env_diff_cmd']
    p = argparse.ArgumentParser()
    p.add_argument("--list-diff", action='store_true')
    p.add_argument("--no-ignore", action='store_true')
    p.add_argument("-F", dest="config_file", default=os.path.expanduser("~/.config/env-diff.yml"), help="Select alternate config file")
    p.add_argument("--show-function-bodies", action='store_true', help="Show bodies of new functions")
    p.add_argument("--debug", help="Set log level to debug", action='store_true')
    p.add_argument("initial", help="Initial environment created with env-diff-save")
    p.add_argument("final", help="Final environment created with env-diff-save")
    args = p.parse_args()

    # TODO: As described in main(): Move all this to the __init__() of
    # ShellEnvironmentDiff
    if os.path.isfile(args.config_file) and have_yaml:
        with open(args.config_file) as f:
            config = yaml.safe_load(f)
    else:
        config = {}

    colon_lists = set(config['colon_lists']) if 'colon_lists' in config \
        else set(['PATH'])
    space_lists = set(config['space_lists']) if 'space_lists' in config \
        else set()

    if args.no_ignore:
        ignored_variables = set()
        ignored_normal_arrays = set()
        ignored_assoc_arrays = set()
    else:
        ignored_variables = set(config['ignored_variables']) if 'ignored_variables' in config \
            else set(['BASHPID', 'BASH_SUBSHELL', 'EPOCHREALTIME',
                     'EPOCHSECONDS', 'RANDOM', 'SRANDOM', 'SECONDS'])
        ignored_normal_arrays = set(config['ignored_normal_arrays']) if 'ignored_normal_arrays' in config \
            else set(['BASH_LINENO'])
        ignored_assoc_arrays = set(config['ignored_assoc_arrays']) if 'ignored_assoc_arrays' in config \
            else set()

    return args

args = get_args()


def main():
    """
    Perform the entire set of comparisons
    """
    setup_function_dictionnaries(display_functions, comparison_functions)
    # TODO: Use envdiff.ShellEnvironmentDiff:
    # - Make all these compare_*() functions methods of the class
    # - Give the class's __init__() method a config argument
    #   - The getargs gets the config file path and the __init__()
    #     method of the class sets attributes for the ignored variables
    #     and colon lists and son on
    # - This file would be more like the new env-diff-generate-code.py
    before = envdiff.ShellEnvironmentData(args.initial)
    after = envdiff.ShellEnvironmentData(args.final)
    compare_variables(before.env_vars, after.env_vars, env=True)
    compare_variables(before.shell_vars, after.shell_vars, env=False)
    compare_associative_arrays(before.assoc_arrays, after.assoc_arrays)
    compare_normal_arrays(before.normal_arrays, after.normal_arrays)
    compare_shell_options(before.shopt, after.shopt, from_set=False)
    compare_shell_options(before.shopt_set, after.shopt_set, from_set=True)
    compare_shell_functions(before.functions, after.functions, args.show_function_bodies)
    compare_traps(before.traps, after.traps)

def compare_variables(i: dict,f: dict, env):
    """
    Compare sets of shell or environment variables.
    """
    # TODO: Same for all the other compare_*() functions: base them on
    #       EnvomponentDiff so I don't have to repeat this new, deleted,
    #       common, changed stuff at the top of each of them
    new = set(f.keys()) - set(i.keys())
    deleted = set(i.keys()) - set(f.keys())
    common = set(i.keys()).intersection(set(f.keys())) - set(ignored_variables)
    changed = list(sorted(filter(lambda v: i[v] != f[v], common)))

    if new or deleted or changed:
        if env:
            print("\033[1m================= ENVIRONMENT VARIABLES ================\033[0m")
        else:
            print("\033[1m================= SHELL VARIABLES ================\033[0m")

    if new:
        print('\033[4;32mNew variables\033[0m')
        for var in sorted(new):
            display_single_variable(var, f[var])

    if deleted:
        print('\033[4;31mDeleted variables\033[0m')
        for var in sorted(deleted):
            display_single_variable(var, i[var])

    if changed:
        print('\033[4;33mModified variables\033[0m')
        for var in changed:
            for k in comparison_functions:
                if re.fullmatch(k, var):
                    compare_func = comparison_functions[k]
                    break
            else:
                compare_func = lambda n,i,f: print(f"{n}:\n\tOLD: {i}\n\tNEW: {f}")
            compare_func(var, i[var], f[var])

def compare_associative_arrays(i: dict,f: dict):
    """
    Print differences between the sets of associative arrays before and after
    """
    new = set(f.keys()) - set(i.keys())
    deleted = set(i.keys()) - set(f.keys())
    common = set(i.keys()).intersection(set(f.keys())) - ignored_assoc_arrays
    changed = list(sorted(filter(lambda v: i[v] != f[v], common)))

    if new or deleted or changed:
        print("\033[1m================= ASSOCIATIVE ARRAY VARIABLES ================\033[0m")

    if new:
        print('\033[4;32mNew Associative Arrays\033[0m')
        for var in sorted(new):
            print(f"{var}: {f[var]}")

    if deleted:
        print('\033[4;31mDeleted Associative Arrays\033[0m')
        for var in sorted(deleted):
            print(f"{var}")

    if changed:
        print('\033[4;33mModified Associative Arrays\033[0m')
        for var in changed:
            compare_single_associative_array(var, i[var], f[var])

def compare_single_associative_array(name: str, i: dict, f:dict):
    print(f"\033[33m  {name}\033[0m")
    initial_keys = set(i.keys())
    final_keys = set(f.keys())

    new = final_keys - initial_keys
    deleted = initial_keys - final_keys
    common = initial_keys.intersection(final_keys)
    changed = list(sorted(filter(lambda v: i[v] != f[v], common)))
    if new:
        print(f"\033[33m    New keys\033[0m")
        for k in new:
            print(f"      {k}: {f[k]}")

    if deleted:
        print(f"\033[33m    Deleted keys\033[0m")
        for k in deleted:
            print(f"      {k}: (value was {i[k]})")

    if changed:
        print(f"\033[33m    Keys with changed values\033[0m")
        for k in changed:
            print(f"      {k}:")
            print(f"        OLD: {i[k]}")
            print(f"        NEW: {f[k]}")



def compare_normal_arrays(i: dict, f:dict):
    """
    Print differences between the sets of normal arrays before
    This is the exact same code as the one for associative arrays
    except for the words "Normal" and "Associative" in the prints.
    I'm leaving it like because I intend to display new arrays
    and compare modified ones in in different ways in the future.
    """
    new = set(f.keys()) - set(i.keys())
    deleted = set(i.keys()) - set(f.keys())
    common = set(i.keys()).intersection(set(f.keys())) - ignored_normal_arrays
    # common = {v for v in common if not v.startswith("_env_diff")}
    logging.debug(f"ignored_normal_arrays = '{ignored_normal_arrays}'")
    changed = sorted(filter(lambda v: i[v] != f[v], common))

    if new or deleted or changed:
        print("\033[1m================= NORMAL ARRAY VARIABLES ================\033[0m")

    if new:
        print('\033[4;32mNew Normal Arrays\033[0m')
        for var in sorted(new):
            print(f"{var}: {f[var]}")

    if deleted:
        print('\033[4;31mDeleted Normal Arrays\033[0m')
        for var in sorted(deleted):
            print(f"{var}: {i[var]}")

    if changed:
        print('\033[4;33mModified Normal Arrays\033[0m')
        for var in changed:
            initial = { int(k):v for k,v in i[var].items() }
            final = { int(k):v for k,v in f[var].items() }
            if not is_contiguous_array(initial) or not is_contiguous_array(final):
                print(f"Initial {var}: {as_sparse_array(initial)}")
                print(f"Final   {var}: {as_sparse_array(final)}")
            else:
                print(f"Initial {var}: {as_normal_array(initial)}")
                print(f"Final   {var}: {as_normal_array(final)}")


def compare_shell_options(i: dict, f: dict, from_set=False):
    """
    Print differences between shell options
    """
    if set(i.keys()) != set(f.keys()):
        print(set(i.keys()).difference(set(f.keys())))
    changes = []
    for k in i:
        if i[k] != f[k]:
            changes.append(f"{k}: {i[k]} -> {f[k]}")
    if changes:
        if from_set:
            print("\033[1m================= SHELL OPTIONS (SET) ================\033[0m")
        else:
            print("\033[1m================= SHELL OPTIONS ================\033[0m")
        print('\n'.join(changes))


def compare_shell_functions(i: dict, f: dict, show_new_defs=True):
    """
    Compare sets of shell functions
    """
    new = set(f.keys()) - set(i.keys())
    deleted = set(i.keys()) - set(f.keys())
    common = set(i.keys()).intersection(set(f.keys()))
    changed = sorted(filter(lambda v: i[v] != f[v], common))

    if new or deleted or changed:
        print("\033[1m================= SHELL FUNCTIONS ================\033[0m")

    if new:
        print('\033[4;32mNew functions\033[0m')
        for func in sorted(new):
            if show_new_defs:
                print(f"\033[1m{func}\033[0m()", end='')
                print(highlight('\n'.join(f[func])))
            else:
                print(func)

    if deleted:
        print('\033[4;31mDeleted functions\033[0m')
        for func in sorted(deleted):
            print(f"{func}()")

    if changed:
        print('\033[4;33mModified functions\033[0m')
        for func in changed:
            print(f"\033[1;35m{func}()\033[0m")
            if show_new_defs:
                diff_compare(i[func], f[func])


def compare_traps(i: dict, f: dict):
    """
    Compare sets of shell functions
    """
    new = set(f.keys()) - set(i.keys())
    deleted = set(i.keys()) - set(f.keys())
    common = set(i.keys()).intersection(set(f.keys()))
    changed = sorted(filter(lambda v: i[v] != f[v], common))

    if new or deleted or changed:
        print("\033[1m================= TRAPS ================\033[0m")

    if new:
        print('\033[4;32mNew traps\033[0m')
        for t in sorted(new):
            print(f"{t}: {f[t]}")

    if deleted:
        print('\033[4;31mDeleted traps\033[0m')
        for t in sorted(deleted):
            print(f"{t}")

    if changed:
        print('\033[4;33mModified traps\033[0m')
        for t in changed:
            print(f"\033[1;35mtrap on {t}\033[0m")
            diff_compare(i[t].splitlines(), f[t].splitlines(), indent='    ')

################################################################################
# Display and comparison functions for individual variables, arrays and functions
################################################################################
def display_single_variable(name, value):
    for k in display_functions:
        if re.fullmatch(k, name):
            display_func = display_functions[k]
            break
    else:
        display_func = lambda n,v: print(f"\033[1m{n}\033[0m={v}")
    display_func(name, value)

def compare_colon_lists(name, initial_value, final_value):
    initial_list = initial_value.split(':')
    final_list = final_value.split(':')
    print(f"{name} (colon-separated list", end='')
    return compare_python_lists(name, initial_list, final_list)

def display_colon_list(name, value):
    elements = value.split(':')
    print(f"\033[1m{name}\033[0m (colon delimited list)")
    return display_python_list(name, elements)

def compare_space_lists(name, initial_value, final_value):
    initial_list = initial_value.split(' ')
    final_list = final_value.split(' ')
    print(f"{name} (space-separated list", end='')
    return compare_python_lists(name, initial_list, final_list)

def display_space_list(name, value):
    elements = value.split( )
    print(f"\033[1m{name}\033[0m (space delimited list)")
    return display_python_list(name, elements)

def display_python_list(name, elements):
    for e in elements:
        if e:
            print(f'    {e}')
        else:
            print('    \033[4m(empty)\033[0m (leading, trailing, or consecutive delimiters)')


def color_full_diff(before, after):
    diff_colors = {'+': '\033[32m', ' ': '', '-': '\033[31m', '?': '\033[36m'}
    for l in difflib.unified_diff(before, after, fromfile="before", tofile="after", n=1000):
        if l.startswith('+++') or l.startswith('---') or l.startswith('@@'):
            continue
        color = diff_colors.get(l[0],'')
        yield f"{color}{l.rstrip()}\033[0m"

def compare_python_lists(name, initial_list, final_list, show_kept=False):
    initial_set = set(initial_list)
    final_set = set(final_list)
    new = set(final_list) - set(initial_list)
    deleted = set(initial_list) - set(final_list)
    common = set(initial_list).intersection(set(final_list))
    indent = '        '
    if args.list_diff:
        print(')')
        print('    ' + '\n    '.join(map(str.rstrip, list(color_full_diff(
                [ s if s else "(empty)" for s in initial_list ],
                [ s if s else "(empty)" for s in final_list ]
        )))))
    else:
        print(' using set comparison)')
        if new:
            print('    ADDED:')
            print('\n'.join([f'{indent}{e}' for e in new]))
        if common and show_kept:
            print('    KEPT:')
            print('\n'.join([f'{indent}{e}' for e in common]))
        if deleted:
            print('    REMOVED:')
            print('\n'.join([f'{indent}{e}' for e in deleted]))
        if initial_list != final_list and (initial_set == final_set):
            print('(before and after are the same as sets.  Comparing with diff')
            print('    ' + '\n    '.join(map(str.rstrip, list(color_full_diff(
                    [ s if s else "(empty)" for s in initial_list ],
                    [ s if s else "(empty)" for s in final_list ]
            )))))

def setup_function_dictionnaries(display, comparison):
    comparison_functions['BASH_FUNC_[a-zA-Z_.-]*%%'] = compare_exported_bash_func
    for n in colon_lists:
        comparison[n] = compare_colon_lists
        display[n] = display_colon_list
    for n in space_lists:
        comparison[n] = compare_space_lists
        display[n] = display_space_list

def compare_exported_bash_func(name, before, after):
    print(name)
    diff_compare(before.splitlines(), after.splitlines())

def diff_compare(before, after, indent=''):
    diff_colors = {'+': '\033[32m', ' ': '', '-': '\033[31m', '?': '\033[36m'}
    def diff():
        for l in difflib.unified_diff(before, after, fromfile="before", tofile="after"):
            if l.startswith('+++') or l.startswith('---') or l.startswith('@@'):
                continue
            color = '\033[1;34m' \
                    if l.startswith('+++') or l.startswith('---') or l.startswith('@@') \
                    else diff_colors.get(l[0],'')
            yield f"{color}{l.rstrip()}\033[0m"
    print(indent + ('\n'+indent).join(diff()))

if 'pygments' in sys.modules:
    def get_formatter():
        styles = list(pygments.styles.get_all_styles())
        style = 'default'
        # Solarized light is for light background but I tried it on dark background
        # and it looks great
        potential_styles = ['solarized-light', 'vim', 'monokai', 'arduino',
                            'emacs', 'native', 'lovelace', 'paraiso-dark',
                            'rainbow_dash', 'rrt', 'perldoc', 'solarized-dark',
                            'sas', 'stata-dark', 'dracula', 'colorful']
        for s in potential_styles:
            if s in styles:
                style = s
                break
        return pygments.formatters.Terminal256Formatter(style=style)

    lexer = pygments.lexers.shell.BashLexer()
    fmt = get_formatter()
    def highlight(code):
        return pygments.highlight(code, lexer=lexer, formatter=fmt)
else:
    def highlight(code):
        return code

""" Functions operating on dictionaries with integer keys """
def is_contiguous_array(d):
    """ Check if the bash array represented by d has contiguous indices"""
    keys=d.keys()
    for i in range(len(keys)):
        if i not in keys:
            return False
    return True

def as_normal_array(d):
    """ For contiguous arrays, we reprensent it as a regular python list """
    return [v for k,v in sorted(d.items())]

def as_sparse_array(d):
    """ For sparse arrays, we represent them as a string resembling the output
    of the bash builtin `delcare -p` """
    return '(' + ' '.join([f"[{k}]='{v}'" for k,v in sorted(d.items())]) + ')'

if __name__ == "__main__":
    try:
        main()
    except FileNotFoundError as e:
        sys.exit(1)
        pass
