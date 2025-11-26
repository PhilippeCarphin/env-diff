# Complete BASH shell environment comparison tool

```
env-diff [options] [--] CMD

Produce a complete summary of what `CMD` has changed in the environment.
```

```
env-diff-save DIRECTORY

Create a directory DIRECTORY containing all the information about the current
shell environment.
```

```
env-diff-compare [options] BEFORE AFTER

Compare directories created with env-diff-save.
```

```
env-diff-gencode [options] BEFORE AFTER

Generate BASH code to go from BEFORE to AFTER
```

```
env-diff-load [options] DIRECTORY

Load the environment from DIRECTORY created with env-diff-save
```

Run `CMD --help` to see the manpage for each command

All commands save and compare these aspects of the shell environment:
- Environment variables
- Shell variables
- Associative arrays
- Normal arrays
- Shell options (shopt and set)
- Functions
- Traps

`CMD` can be any command although running executables will have no effect on
the environment so it will be either `source` command or a call to a shell
function but it can also be plain shell code.

# Installing

Clone this repository and source `env-diff-cmd.bash` from the repo in your
`~/.bashrc`.

You can also copy the `dot-config-env-diff.yml` to `$HOME/.config/env-diff.yml`
or make your own using the file as a template.

# Usage

## Basic usage

Sourcing `env-diff-cmd.bash` defines the `env-diff()` shell function which can receive
any BASH code as an argument (calling a shell function, defining variables or other stuff,
sourcing a script)

```sh
env-diff 'f(){ echo "HELLO" ; }
    PATH=new-thing/bin:${PATH}
    A=B
    set -o pipefail
    shopt -s extdebug
    g(){ echo "This is new g" ; }
    unset HOSTNAME
    export -n USER'
```

![example](example.png)

## Saving environments to compare

This will show the same output as above but may be more convenient to compare
environments from different shells.

```sh
env-diff-save INITIAL

# Change things about our shell environment
f(){ echo "HELLO" ; }
PATH=new-thing/bin:${PATH}
A=B
set -o pipefail
shopt -s extdebug
g(){ echo "This is new g" ; }
unset HOSTNAME
export -n USER

env-diff-save FINAL

env-diff-compare INITIAL FINAL
```

## Loading a saved environment

The command `env-diff-gencode INITIAL FINAL` will procuce shell code to go
from `INITIAL` to `FINAL`:

```sh
env-diff-save INITIAL

# Change things about our shell environment
f(){ echo "HELLO" ; }
PATH=new-thing/bin:${PATH}
A=B
set -o pipefail
shopt -s extdebug
g(){ echo "This is new g" ; }
unset HOSTNAME
export -n USER

env-diff-save FINAL

env-diff-gencode INITIAL FINAL > to_source
```

Now in a new shell, we can do
```sh
source to_source
env-diff-save NEW_FINAL
env-diff-compare FINAL NEW_FINAL
```
and see that sourcing the file made our environment `NEW_FINAL` identical to
the `FINAL` we had created earlier.

### Convenience function

The `env-diff-load TO_LOAD` command is a convenience function that combines
the steps above to generate and evaluate code to go from the current shell
environment to the one saved in `TO_LOAD`.  It is roughly equivalent to
```sh
env-diff-load(){
    env-diff-save current
    eval "$(env-diff-gencode current $1)"
}
```


# Details

- [env-diff manpage](manpages/env-diff.org)
- [env-diff-save manpage](manpages/env-diff-save.org)
- [env-diff-gencode manpage](manpages/env-diff-gencode.org)
- [env-diff-load manpage](manpages/env-diff-load.org)

# Dependencies

- `jq`
- standard UNIX tools (`sort`, `comm`, `cut`, `cat`, `mkdir`, `mktemp`)
- `python3`
  - `pyyaml` is optional but required to read config files
  - `pygments` is optional.  If it is present it will be used to color function
    bodies.
  - `shlib` is required to use `env-diff-gencode` and `env-diff-load` to quote
    values of shell variables.
- For the autocomplete, a recent enough version of `bash-completion`
