"""
Generate shell code (BASH only) to take apply the difference between two
environments saved with env-diff-save
"""

import envdiff
import argparse
import shutil
import shlib
import pathlib
import sys

def get_args():
    p = argparse.ArgumentParser(description=__doc__)
    # TODO: Load config file
    # - Maybe it could have the path to a reference environment so that if we
    #   only give one environment on the command line, then the initial one
    #   will be taken from the config file.
    p.add_argument("initial", nargs=1, help="Initial environment directory from env-diff-save")
    p.add_argument("final", nargs=1, help="Final environment directory from env-diff-save")
    p.add_argument("--output", "-o", type=pathlib.Path)
    args = p.parse_args()

    args.initial = args.initial[0]
    args.final = args.final[0]

    return args

def main():
    args = get_args()

    if args.output is None:
        output = sys.stdout
    else:
        output = open(args.output, 'w')

    ed = envdiff.ShellEnvironmentDiff(args.initial, args.final)
    ed.gencode(output)

if __name__ == "__main__":
    sys.exit(main())
