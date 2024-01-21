# Complete BASH shell environment comparison tool

```
env-diff [--list-diff] CMD
```

produces a complete summary of what `CMD` has changed in the enivironment.

`CMD` can be any command although running executables will have no effect on the environment so it will be either `source` command or a call to a shell function but it can also be plain shell code.

The command will print a complete report of what changed
- Environment variables
- Shell variables
- Associative arrays
- Normal arrays
- Shell options (shopt and set)
- Functions

# Usage

Sourcing `env-diff-cmd.bash` defines the `env-diff()` shell function which can receive
any BASH code as an argument (calling a shell function, defining variables or other stuff,
sourcing a script)

```
$ env-diff 'f(){ echo "hello" ; }'
================= ENVIRONMENT VARIABLES ==========
New variables
-------------
X=abc
Modified variables
------------------
PATH (colon-separated list using set comparison)
    ADDED:
        adding_a_path
================= SHELL VARIABLES ================
New variables
-------------
A=xyz
================= SHELL FUNCTIONS ================
New functions
-------------
f(){
    echo "hello"
}
```

# Caveats

## Lists

The default way to compare lists like `PATH` is using Python's `set` object
which ignores duplicates and order.  Most of the time this is OK but for
more precision, the argument `--list-diff` will use `difflib.unified_diff`
to give a complete diff.

## Special variables

Some special variables always change.

To avoid distracting in the above examples, the following was manually removed from the output:
```
env-diff 'true'
================= SHELL VARIABLES ================
Modified variables
------------------
BASHPID:
        OLD: 54108
        NEW: 54171
BASH_SUBSHELL:
        OLD: 1
        NEW: 2
EPOCHREALTIME:
        OLD: 1705796267.338518
        NEW: 1705796267.518581
RANDOM:
        OLD: 26340
        NEW: 7561
SRANDOM:
        OLD: 1496122744
        NEW: 150486955
================= NORMAL ARRAY VARIABLES ================
Modified Normal Arrays
----------------------
Initial BASH_LINENO: ['18', '11', '3', '21']
Final   BASH_LINENO: ['18', '23', '3', '21']
```

These are special BASH variables that don't simply store a value but are either changed automatically by BASH like `BASHPID`, `BASH_SUBSHELL`, and `BASH_LINENO` or are more like
a function call like `RANDOM`, `SRANDOM`, and `EPOCHREALTIME`.

## Identifiers related to `env-diff`

There are a few variables beginning with `_env_diff` and a few functions
beginning with `_env-diff`.  If `CMD` changes them it can interfere with the
working of this program.

# Future work

Some things I might like to do in the future are

## Ignoring special variables that always change

They are completely useless, they don't give any information on what the user supplied command does to the environment.

## Better comparison of arrays

Right now I just print them because I wanted to have a complete working program
but ideally I would print something more useful.

Normal arrays could be compared the same way colon-list variables are compared
with the option to use `--list-diff`.

For Associative arrays, I could start by comparing the set of keys and
- for deleted keys, just print that the key was deleted
- for new keys print the new key and the value
- for changed keys, print new and old values.

## Aliases

Since BASH has the array `BASH_ALIASES`, I think that this will be covered
when I improve how associative arrays are compared.

## Executables

Compare ecutables findable through PATH

### Other variables

Shared libraries findable through `LD_LIBRARY_PATH` or `DYLD_LIBRARY_PATH` but
I think it's starting to get a bit nuts.

