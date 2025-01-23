import logging
import shlib

# The config file is not read for code generation.  Only a hardcoded list of
# variables.  We also ignore all _env_diff* variables.  The user has no say
# in this.
special_vars = [
        "EPOCHSECONDS",
        "SECONDS",
        "EPOCHREALTIME",
        "COLUMNS",
        "LINES",
        "RANDOM",
        "HISTCMD",
        "BASHPID",
        "SRANDOM",

        "BASH_SOURCE",
        "BASH_LINENO",
        "BASH_ARGC",
        "BASH_ARGV",
        "BASH_CMDS",
        "FUNCNAME",

        "PS1",

        "BASHOPTS",
        "EUID",
        "PPID",
        "SHELLOPTS",
        "UID",
        "BASH_VERSINFO"
]


class ShCodeGenerator:
    def __init__(self, output):
        self.output = output

    def set_var(self, name: str, value: str):
        if name.startswith("_env_diff_"):
            logging.debug(f"Not unsetting variable {name} starting with '_env_diff_'")
            return
        if name in special_vars:
            return
        self.output.write(f"{name}={shlib.quote_arg(value)}\n")

    def set_env_var(self, name, value):
        if name in special_vars:
            return
        self.output.write(f"export {name}={shlib.quote_arg(value)}\n")

    def unexport_var(self, name):
        self.output.write(f"export -n {name}\n")

    def set_func(self, name, value):
        if name.startswith("_env-diff") or name.startswith("env-diff"):
            logging.debug(f"Not setting env-diff function {name}")
            return
        self.output.write(name + "()")
        self.output.write('\n'.join(value))
        self.output.write('\n')

    def change_array(self, name, i, f):
        """
        Apply modifications to an array
        Doing it this way is important because some variables because some
        variables are special: The documentation says this about BASH_ALIASES:
        'If <var> is unset, it loses its special properties even if it is
        subsequently reset.'

        Instead of unsetting the array and using self.set_assoc_array() to
        delete it and and then setting it to its new value, we have to be more
        precise and generate code to remove deleted keys.

        Also some arrays like BASH_ALIASES are special in another way which is
        that adding keys to the array adds aliases but deleting keys from it
        does not remove the alias or the key
           | $ BASH_ALIASES[x]=y
           | $ unset BASH_ALIASES[x]
           | $ echo ${BASH_ALIASES[x]}
           | y
           | $ alias x
           | y
        only doing 'unalias <key>' removes the key from the alias:
           | $ unalias x
           | $ echo ${BASH_ALIASES[x]}
           | <nothing>
           | $ alias x
           | bash: alias: x: not found
        """
        if name in special_vars:
            logging.debug(f"Array {name} cannot be changed, skipping")
            return
        new = set(f.keys()) - set(i.keys())
        common = set(i.keys()).intersection(set(f.keys()))
        changed = set(filter(lambda v: i[v] != f[v], common))

        for k in new.union(changed):
            self.output.write(f"{name}[{k}]={shlib.quote_arg(f[k])}\n")
        deleted = set(i.keys()) - set(f.keys())
        for k in deleted:
            if name == "BASH_ALIASES":
                self.output.write(f"unalias {k}\n")
            else:
                self.output.write(f"unset {name}[{k}]\n")

    def set_normal_array(self, name, value):
        if name in special_vars:
            logging.debug(f"Not setting special variable {name}")
            return
        self.output.write(f"declare -a {name}\n")
        if isinstance(value, list):
            raise RuntimeError("This shouldn't happen because regular arrays are saved as dictionaries too")
            for i,v in enumerate(value):
                self.output.write(f"{name}[i]={shlib.quote_arg(v)}\n")
        elif isinstance(value, dict):
            for k,v in value.items():
                self.output.write(f"{name}[{k}]={shlib.quote_arg(v)}\n")
        else:
            raise RuntimeError("Normal array value is not list or dict")

    def set_assoc_array(self, name, value):
        # Unset it first since the difference could be that a normal array
        # became an associative array.
        self.unset_var(name)
        self.output.write(f"declare -A {name}\n")
        for k,v in value.items():
            self.output.write(f"{name}[{k}]={shlib.quote_arg(v)}\n")

    def set_shopt_option(self, name, value):
        if value == "on":
            self.output.write(f"shopt -s {name}\n")
        elif value == "off":
            self.output.write(f"shopt -u {name}\n")

    def set_set_option(self, name, value):
        if value == "on":
            self.output.write(f"shopt -so {name}\n")
        elif value == "off":
            self.output.write(f"shopt -uo {name}\n")

    def set_trap(self, name, value):
        self.output.write(f"trap -- {shlib.quote_arg(value)} {name}\n")

    def unset_var(self, name):
        if name.startswith("_env_diff_"):
            logging.debug(f"Not unsetting variable {name} starting with '_env_diff_'")
            return
        if name in special_vars:
            logging.debug(f"Not unsetting special variable {name}")
            return
        self.output.write(f"unset {name}\n")

    def unset_func(self, name):
        if name.startswith("_env-diff") or name.startswith("env-diff"):
            logging.debug(f"Not unsetting env-diff function {name}")
            return
        self.output.write(f"unset -f {name}\n")

    def unset_trap(self, name):
        self.output.write(f"trap - {name}\n")

    def comment(self, comment):
        lines = comment.splitlines()
        for l in lines:
            self.output.write(f"# {l}\n")

    def box(self, comment):
        self.output.write('\n')
        self.output.write(80*"#" + "\n")
        self.comment(comment)
        self.output.write(80*"#" + "\n")


def gencode(diff, output):
    """
    For the purposes of code generation, it is important to consider all
    components together because if the only difference is exporting a variable,
    then the code to generate should be 'export <name>=<value>' but if we do
    not consider the components together, we would generate the code

        # When generating code for the environment variable diff
        export <name>=<value>

        # When generating code for the shell variable diff
        unset name

    so if a variable moves from one component to another, we need to generate
    different code for that situation.  This is why the gencode() function
    uses the *_moved() functions to unset a variable only if it doesn't move
    to another component.  And in the case of an environment variable moving
    to another component, we unexport it.
    """

    logging.debug("Generating code")
    gen = ShCodeGenerator(output)

    gen.comment("Apply environment changes")

    gen.box("ENVIRONMENT VARIABLES")
    gen.comment("Deleted env vars")
    for name in diff.env_vars.deleted:
        if diff.deleted_env_var_moved(name):
            output.write(f"# variable {name} is in another section, don't unset, just unexport\n")
            gen.unexport_var(name)
        else:
            gen.unset_var(name)
    gen.comment("New env vars")
    for name in diff.env_vars.new:
        gen.set_env_var(name, diff.env_vars.final[name])
    gen.comment("Changed env vars")
    for name in diff.env_vars.changed:
        gen.set_env_var(name, diff.env_vars.final[name])

    gen.box("SHELL VARIABLES")
    gen.comment("Deleted variables")
    for name in diff.shell_vars.deleted:
        if not diff.deleted_shell_var_moved(name):
            gen.unset_var(name)
    gen.comment("New variables")
    for name in diff.shell_vars.new:
        gen.set_var(name, diff.shell_vars.final[name])
    gen.comment("Changed variables")
    for name in diff.shell_vars.changed:
        gen.set_var(name, diff.shell_vars.final[name])

    gen.box("NORMAL ARRAYS")
    for name in diff.normal_arrays.deleted:
        if not diff.deleted_normal_array_moved(name):
            logging.debug(f"Unsetting deleted normal array {name}")
            gen.unset_var(name)
    for name in diff.normal_arrays.new:
        logging.debug(f"Setting new normal array {name}")
        gen.set_normal_array(name, diff.normal_arrays.final[name])
    for name in diff.normal_arrays.changed:
        logging.debug(f"Changing normal array {name}")
        gen.change_array(name, diff.normal_arrays.initial[name], diff.normal_arrays.final[name])

    gen.box("ASSOC ARRAYS")
    for name in diff.assoc_arrays.deleted:
        if not diff.deleted_assoc_array_moved(name):
            gen.unset_var(name)
    for name in diff.assoc_arrays.new:
        gen.set_assoc_array(name, diff.assoc_arrays.final[name])
    for name in diff.assoc_arrays.changed:
        gen.change_array(name, diff.assoc_arrays.initial[name], diff.assoc_arrays.final[name])

    gen.box("FUNCTIONS")
    gen.comment("Option expand_aliases must be off for function part")
    gen.comment("in case the name of the function is an alias")
    gen.set_shopt_option("expand_aliases", "off")
    for name in diff.functions.deleted:
        gen.unset_func(name)
    for name in diff.functions.new:
        gen.comment(f"Setting function {name}")
        gen.set_func(name, diff.functions.final[name])
    for name in diff.functions.changed:
        gen.set_func(name, diff.functions.final[name])
    if diff.shopt.final['expand_aliases'] == 'on' and 'expand_aliases' not in diff.shopt.changed:
        gen.set_shopt_option("expand_aliases", "on")

    gen.box("Shopt options")
    for opt in diff.shopt.changed:
        gen.set_shopt_option(opt, diff.shopt.final[opt])

    gen.box("Set options")
    for opt in diff.shopt_set.changed:
        gen.set_set_option(opt, diff.shopt_set.final[opt])

    gen.box("TRAPS")
    for name in diff.traps.changed.union(diff.traps.new):
        gen.set_trap(name, diff.traps.final[name])
