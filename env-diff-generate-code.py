"""
Generate shell code (BASH only) to take apply the difference between two
environments saved with env-diff-save
"""

import envdiff
import argparse
import pathlib
import sys
import envdifflogging
import logging
import os

def get_args():
    if '_env_diff_cmd' in os.environ:
        sys.argv[0] = os.environ['_env_diff_cmd']
    p = argparse.ArgumentParser(description=__doc__)
    # TODO: Load config file
    # - Maybe it could have the path to a reference environment so that if we
    #   only give one environment on the command line, then the initial one
    #   will be taken from the config file.
    p.add_argument("initial", help="Initial environment directory from env-diff-save")
    p.add_argument("final", help="Final environment directory from env-diff-save")
    p.add_argument("--output", "-o", type=pathlib.Path)
    p.add_argument("--debug", action='store_true', help="Set log level to DEBUG")
    args = p.parse_args()

    return args

def main():
    args = get_args()
    envdifflogging.configureLogging(level=(logging.INFO if not args.debug else logging.DEBUG))

    try:
        import codegen
    except ModuleNotFoundError as e:
        if e.name == 'shlib':
            logging.error("Could not import 'shlib'.  This package is required for 'env-diff-gencode'")
            return 1
        else:
            raise

    if args.output is None:
        output = sys.stdout
    else:
        output = open(args.output, 'w')

    try:
        ed = envdiff.ShellEnvironmentDiff(args.initial, args.final)
    except FileNotFoundError as e:
        logging.error(f"No saved environment at '{e.filename}': {e}")
        return 1
    except envdiff.EnvDiffError as e:
        logging.error(f"The directory '{e.directory}' does not appear to be a saved environment created with env-diff-save: missing '{e.filename}'")
        return 1
    codegen.gencode(ed, output)

if __name__ == "__main__":
    sys.exit(main())
