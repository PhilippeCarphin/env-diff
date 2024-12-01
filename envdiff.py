import os
import json
import shlib
import sys

class ShellEnvironmentData:
    """
    Class ShellEnvironmentData holds the all the data saved into the temp files
    """
    def __init__(self, data_dir):
        try:
            with open(os.path.join(data_dir, f"env_vars.json")) as f:
                self.env_vars = json.load(f)
            with open(os.path.join(data_dir, f"shell_vars.json")) as f:
                self.shell_vars = json.load(f)
            with open(os.path.join(data_dir, f"assoc_arrays.json")) as f:
                self.assoc_arrays = json.load(f)
            with open(os.path.join(data_dir, f"normal_arrays.json")) as f:
                self.normal_arrays = json.load(f)
            self.shopt = {}
            with open(os.path.join(data_dir, f"shopt.txt")) as f:
                for line in f:
                    opt, val = line.split()
                    self.shopt[opt] = val
            self.functions = {}
            self.shopt_set = {}
            with open(os.path.join(data_dir, f"shopt_set.txt")) as f:
                for line in f:
                    opt, val = line.split()
                    self.shopt_set[opt] = val
            with open(os.path.join(data_dir, f"func_names.txt")) as f:
                for name in f.read().splitlines():
                    with open(os.path.join(data_dir, f"functions", f"BASH_FUNC_{name}.bash")) as func:
                        lines = func.read().splitlines()[1:]
                        self.functions[name] = lines
            with open(os.path.join(data_dir, f"traps.json")) as f:
                self.traps = json.load(f)
        except FileNotFoundError as e:
            print(f"Could not locate required file in directory '{data_dir}': {e}", file=sys.stderr)
            raise

class ShCodeGenerator:
    def __init__(self, output):
        self.output = output

    def set_var(self, name: str, value: str):
        readonly_vars = ['BASHOPTS', 'EUID', 'PPID', 'SHELLOPTS', 'UID', 'BASH_VERSINFO']
        if name in readonly_vars:
            return
        self.output.write(f"{name}={shlib.quote_arg(value)}\n")

    def set_env_var(self, name, value):
        readonly_vars = ['BASHOPTS', 'EUID', 'PPID', 'SHELLOPTS', 'UID', 'BASH_VERSINFO']
        if name in readonly_vars:
            return
        self.output.write(f"export {name}={shlib.quote_arg(value)}\n")

    def unexport_var(self, name):
        self.output.write(f"export -n {name}\n")

    def set_func(self, name, value):
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
        if name in ['BASH_ARGC', 'BASH_ARGV', 'BASH_LINENO']:
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
        # TODO: Maybe this is not the right place for this
        if name in ['BASH_ARGC', 'BASH_ARGV', 'BASH_LINENO']:
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
        self.output.write(f"unset {name}\n")

    def unset_func(self, name):
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

class EnvComponentDiff:
    """
    Differences between two components of the shell environment
    """
    def __init__(self, i: dict, f: dict):
        # TODO:  Deal with ignored variables
        # (we don't care about colon lists here because that's just for how
        # we display variable differences)
        self.initial = i
        self.final = f
        self.new = set(f.keys()) - set(i.keys())
        self.deleted = set(i.keys()) - set(f.keys())
        self.common = set(i.keys()).intersection(set(f.keys()))
        self.changed = set(filter(lambda v: i[v] != f[v], self.common))

class ShellEnvironmentDiff:
    """
    Complete set of differences between all components of the shell environment
    """
    def __init__(self, before, after):
        before = before if isinstance(before, ShellEnvironmentData) else ShellEnvironmentData(before)
        after = after if isinstance(after, ShellEnvironmentData) else ShellEnvironmentData(after)

        self.env_vars = EnvComponentDiff(before.env_vars, after.env_vars)
        self.shell_vars = EnvComponentDiff(before.shell_vars, after.shell_vars)
        self.functions = EnvComponentDiff(before.functions, after.functions)
        self.shopt_set = EnvComponentDiff(before.shopt_set, after.shopt_set)
        self.shopt = EnvComponentDiff(before.shopt, after.shopt)
        self.assoc_arrays = EnvComponentDiff(before.assoc_arrays, after.assoc_arrays)
        self.normal_arrays = EnvComponentDiff(before.normal_arrays, after.normal_arrays)
        self.traps = EnvComponentDiff(before.traps, after.traps)

    def deleted_env_var_moved(self, name):
        return name in self.shell_vars.new or name in self.normal_arrays.new or name in self.assoc_arrays.new
    def deleted_shell_var_moved(self, name):
        return  name in self.env_vars.new or name in self.normal_arrays.new or name in self.assoc_arrays.new
    def deleted_normal_array_moved(self, name):
        return name in self.env_vars.new or name in self.shell_vars.new or name in self.assoc_arrays.new
    def deleted_assoc_array_moved(self, name):
        return  name in self.env_vars.new or name in self.shell_vars.new or name in self.normal_arrays.new

    def gencode(self, output):
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
        gen = ShCodeGenerator(output)

        gen.comment("Apply environment changes")

        gen.box("ENVIRONMENT VARIABLES")
        gen.comment("Deleted env vars")
        for name in self.env_vars.deleted:
            if self.deleted_env_var_moved(name):
                output.write(f"# variable {name} is in another section, don't unset, just unexport\n")
                gen.unexport_var(name)
            else:
                gen.unset_var(name)
        gen.comment("New env vars")
        for name in self.env_vars.new:
            gen.set_env_var(name, self.env_vars.final[name])
        gen.comment("Changed env vars")
        for name in self.env_vars.changed:
            gen.set_env_var(name, self.env_vars.final[name])

        gen.box("SHELL VARIABLES")
        gen.comment("Deleted variables")
        for name in self.shell_vars.deleted:
            if not self.deleted_shell_var_moved(name):
                gen.unset_var(name)
        gen.comment("New variables")
        for name in self.shell_vars.new:
            gen.set_var(name, self.shell_vars.final[name])
        gen.comment("Changed variables")
        for name in self.shell_vars.changed:
            gen.set_var(name, self.shell_vars.final[name])

        gen.box("NORMAL ARRAYS")
        for name in self.normal_arrays.deleted:
            if not self.deleted_normal_array_moved(name):
                gen.unset_var(name)
        for name in self.normal_arrays.new:
            gen.set_normal_array(name, self.normal_arrays.final[name])
        for name in self.normal_arrays.changed:
            gen.change_array(name, self.normal_arrays.initial[name], self.normal_arrays.final[name])
            # gen.set_normal_array(name, self.normal_arrays.final[name])

        gen.box("ASSOC ARRAYS")
        for name in self.assoc_arrays.deleted:
            if not self.deleted_assoc_array_moved(name):
                gen.unset_var(name)
        for name in self.assoc_arrays.new:
            gen.set_assoc_array(name, self.assoc_arrays.final[name])
        for name in self.assoc_arrays.changed:
            gen.change_array(name, self.assoc_arrays.initial[name], self.assoc_arrays.final[name])
            # gen.set_assoc_array(name, self.assoc_arrays.final[name])

        gen.comment("Option expand_aliases must be off for function part")
        gen.comment("in case the name of the function is an alias")
        gen.set_shopt_option("expand_aliases", "off")
        for name in self.functions.deleted:
            gen.unset_func(name)
        for name in self.functions.new:
            gen.comment(f"Setting function {name}")
            gen.set_func(name, self.functions.final[name])
        for name in self.functions.changed:
            gen.set_func(name, self.functions.final[name])
        if self.shopt.final['expand_aliases'] == 'on' and 'expand_aliases' not in self.shopt.changed:
            gen.set_shopt_option("expand_aliases", "on")

        gen.box("Shopt options")
        for opt in self.shopt.changed:
            gen.set_shopt_option(opt, self.shopt.final[opt])

        gen.box("Set options")
        for opt in self.shopt_set.changed:
            gen.set_set_option(opt, self.shopt_set.final[opt])

        gen.box("TRAPS")
        for name in self.traps.changed.union(self.traps.new):
            gen.set_trap(name, self.traps.final[name])
