import os
import json
import sys
import logging
import envdifflogging

class EnvDiffError(Exception):
    def __init__(self, directory, filename):
        self.directory = directory
        self.filename = filename
    def __str__(self):
        return f"The directory {self.directory} is missing {self.filename}"


class ShellEnvironmentData:
    """
    Class ShellEnvironmentData holds the all the data saved into the temp files
    """
    def __init__(self, data_dir):
        if not os.path.isdir(data_dir):
            raise FileNotFoundError(2, "No such directory", data_dir)

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
                    with open(os.path.join(data_dir, f"functions", f"BASH_FUNC_{name}.bash"), 'rb') as func:
                        lines = func.read().splitlines()[1:]
                        self.functions[name] = [l.decode('utf-8', 'backslashreplace') for l in lines]
            with open(os.path.join(data_dir, f"traps.json")) as f:
                self.traps = json.load(f)
        except FileNotFoundError as e:
            raise EnvDiffError(data_dir, e.filename)

class EnvComponentDiff:
    """
    Differences between two components of the shell environment
    """
    def __init__(self, i: dict, f: dict):
        # TODO:  Deal with ignored variables
        # (we don't care about colon lists here because that's just for how
        # we display variable differences)
        # TODO: Here we could remove from new, deleted, changed, the names that
        # - special_variables
        # - begin with _env_diff, env-diff, or _env-diff
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
