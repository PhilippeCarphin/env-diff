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
                        lines = func.read().splitlines()[2:]
                        self.functions[name] = lines
            with open(os.path.join(data_dir, f"traps.json")) as f:
                self.traps = json.load(f)
        except FileNotFoundError as e:
            print(f"Could not locate required file in directory '{data_dir}': {e}", file=sys.stderr)
            raise
