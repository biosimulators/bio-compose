import argparse
import os
import sys
from functools import partial


def simulation_run_cli():
    raise NotImplementedError("This feature is currently under development.")


def verification_cli():
    from bio_compose import verify

    parser = argparse.ArgumentParser(
        description='Verify and compare the outputs of simulators for SBML or OMEX models.'
    )
    parser.add_argument("entrypoint", type=str, help="Path to one of either: SBML or OMEX files. ")
    parser.add_argument("--start", type=int, default=None, help="*SBML simulation only: Start time for the simulation")
    parser.add_argument("--stop", type=int, default=None, help="*SBML simulation only: Stop time for the simulation")
    parser.add_argument("--steps", type=int, default=None, help="*SBML simulation only: Number of simulation steps")
    parser.add_argument("--simulators", nargs="*", default=None, help="List of simulators to include")
    parser.add_argument("--timeout", type=int, default=50, help="Timeout for polling results")
    parser.add_argument("--buffer_time", type=float, default=5, help="Initial buffer time for fetching results")
    parser.add_argument("--poll_time", type=float, default=5, help="Poll time for fetching results")
    parser.add_argument("--outputs_dest", default=None, type=str, help="Destination path to working directory in which observables and rmse plots will be saved.")

    # Define mutually exclusive group to handle either SBML or OMEX
    # subparsers = parser.add_subparsers(dest="mode", help="Mode of verification (sbml or omex)")

    # SBML Verification Arguments
    # sbml_parser = subparsers.add_parser("sbml", help="Verify SBML models")
    # sbml_parser.add_argument("entrypoint", type=str, help="Path to the SBML file")
    # sbml_parser.add_argument("start", type=int, help="Start time for the simulation")
    # sbml_parser.add_argument("stop", type=int, help="Stop time for the simulation")
    # sbml_parser.add_argument("steps", type=int, help="Number of simulation steps")
    # sbml_parser.add_argument("--simulators", nargs="*", default=None, help="List of simulators to include")
    # sbml_parser.add_argument("--timeout", type=int, default=50, help="Timeout for polling results")
    # sbml_parser.add_argument("--buffer_time", type=float, default=5, help="Initial buffer time for fetching results")
    # sbml_parser.add_argument("--poll_time", type=float, default=5, help="Poll time for fetching results")

    # Parse arguments
    args = parser.parse_args()
    entry_file = args.entrypoint
    input_args = [entry_file]
    if args.entrypoint.endswith(".xml"):
        list(map(lambda arg: input_args.append(arg), [args.start, args.stop, args.steps]))

    verification = verify(*input_args, simulators=args.simulators)

    output_dest = args.outputs_dest
    if output_dest is not None:
        entry_filename = entry_file.split('/')[-1].split('.')[0]
        obs_path = os.path.join(output_dest, entry_filename + "_observables")
        rmse_path = os.path.join(output_dest, entry_filename + "_rmse")
        verification.observables(save_dest=obs_path)
        verification.rmse(save_dest=rmse_path)

    return verification



