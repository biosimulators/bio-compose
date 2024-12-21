import asyncio
import os
import pprint
import time
import urllib
import warnings
import zipfile
from pathlib import Path
from tarfile import AbsolutePathError
from typing import *

import h5py
import numpy as np
from dotenv import load_dotenv

import typer

from biosimulations_runutils.biosim_pipeline.biosim_api import run_project, check_run_status
from biosimulations_runutils.biosim_pipeline.data_manager import DataManager
from biosimulations_runutils.biosim_pipeline.datamodels import Simulator, SimulationRun

from bio_compose import get_biomodel_archive
from biosimulations_runutils.common.api_utils import download_file
from tests.utils import read_report_outputs, BiosimulationsRunOutputData, explore_hdf5_data, read_report_outputs_with_labels

load_dotenv('.env')


SKY_BLUE = "\033[38;5;117m"  # Sky blue color
LIGHT_PURPLE = "\033[38;5;183m"
ERROR_RED = "\033[31m"
RESET = "\033[0m"


def printc(msg: Any, alert: str = '', error=False):
    print(f"> {SKY_BLUE if not error else ERROR_RED}{alert if not error else 'AN ERROR OCCURRED'}:{RESET} {LIGHT_PURPLE if not error else ERROR_RED}{pprint.pformat(msg)}{RESET}\n")


def generate_omex_outputs(
        biomodel_entrypoint: str | os.PathLike[str],
        out_dir: str | Path,
        simulators: list[str | tuple[str, str]],
        fetch_buffer: int = 2
) -> BiosimulationsRunOutputData | dict[str, dict[str, np.ndarray | list[float]]]:
    os.mkdir(out_dir) if not os.path.exists(out_dir) else None

    # submit run
    output_dirpaths, omex_src_dirpath = submit_omex_simulations(
        entrypoint=biomodel_entrypoint,
        dest_dir=out_dir,
        simulators=simulators,
        buffer=fetch_buffer,
    )

    # refresh status for each output
    printc(f"> Waiting {fetch_buffer} seconds before refreshing status...\n")
    time.sleep(fetch_buffer)

    return fetch_simulator_output(output_dirpaths, omex_src_dirpath, fetch_buffer)


def download_runs(
        omex_src_dir: Annotated[Union[Path, None], typer.Option(help="defaults env.OMEX_SOURCE_DIR")] = None,
        out_dir: Annotated[Union[Path, None], typer.Option(help="defaults to env.OMEX_OUTPUT_DIR")] = None,
        project_id: Annotated[Union[str, None], typer.Option(help="filter by project_id")] = None,
        simulator: Annotated[Union[Simulator, None], typer.Option(help="filter by simulator")] = None,
) -> Path:
    data_manager = DataManager(omex_src_dir=omex_src_dir, out_dir=out_dir)
    api_base_url = os.environ.get('API_BASE_URL')
    runs: list[SimulationRun] = data_manager.read_run_requests()

    for run in runs:
        # refresh status
        refresh_status(omex_src_dir=omex_src_dir, out_dir=out_dir)

        if project_id and project_id != run.project_id:
            continue
        if simulator and simulator != run.simulator:
            continue
        if run.status is not None and run.status.lower() != "succeeded":
            continue

        printc(alert="> Retrieving simulation run: ", msg=run.model_dump_json())

        simdir = data_manager.get_run_output_dir(run)
        if os.path.exists(simdir / "results.zip"):
            continue

        try:
            out_filepath = Path(simdir / "results.zip")
            download_file(url=f"{api_base_url}/results/" + run.simulation_id + "/download",
                          out_file=out_filepath)

            return out_filepath
        except urllib.error.HTTPError as e:
            printc(alert="Failure:", msg=e, error=True)


STATUS_SCHEMA = {
    "$run_id(str)": {
        "status": "str",
        "out_dir": "PathLike[str]",
        "simulator": "Simulator"
    }
}


def refresh_status(
        omex_src_dir: Path,
        out_dir: Path,
        return_status: bool = False,
) -> dict[str, dict[str, Path | str | None | Simulator]]:
    statuses = {}
    data_manager = DataManager(omex_src_dir=omex_src_dir, out_dir=out_dir)
    runs: list[SimulationRun] = data_manager.read_run_requests()
    for run in runs:
        if run.status is not None and (run.status.lower() == "succeeded" or run.status.lower() == "failed"):
            continue
        run.status = check_run_status(run)
        statuses[run.simulation_id] = {'status': run.status, 'out_dir': out_dir, 'simulator': run.simulator}
    data_manager.write_runs(runs)

    if return_status:
        return statuses


def upload_omex(
        simulator: Annotated[Simulator, typer.Option(help="simulator to run")] = Simulator.vcell,
        simulator_version: Annotated[str, typer.Option(help="simulator version to run - defaults to 'latest'")] = "latest",
        project_id: Annotated[Union[str, None], typer.Option(help="filter by project_id")] = None,
        omex_src_dir: Path = None,
        out_dir: Path = None
) -> None:
    data_manager = DataManager(omex_src_dir=omex_src_dir, out_dir=out_dir)

    projects = data_manager.read_projects()

    for source_omex in data_manager.get_source_omex_archives():
        if source_omex.project_id in projects:
            printc(f"> project {source_omex.project_id} is already validated and published")
            continue
        if project_id is not None and source_omex.project_id != project_id:
            continue
        printc(source_omex.project_id, "Project ID: ")
        run_project(source_omex=source_omex, simulator=simulator, simulator_version=simulator_version, data_manager=data_manager)


def read_simulator_output_data(simulator_output_zippath: os.PathLike[str], output_dirpath: os.PathLike[str]) -> BiosimulationsRunOutputData | dict[str, str]:
    # unzip and extract output files
    with zipfile.ZipFile(simulator_output_zippath, 'r') as zip_ref:
        zip_ref.extractall(output_dirpath)

    # find report and get data
    for filepath in os.listdir(output_dirpath):
        if "output" in filepath:
            for outfile in os.listdir(os.path.join(output_dirpath, filepath)):
                if outfile.endswith(".h5"):
                    # call io method here
                    report_path = os.path.join(str(output_dirpath), filepath, outfile)
                    # simulator_outputs = read_report_outputs(report_file_path=report_path)
                    data = explore_hdf5_data(report_path)
                    dataset_keys = data.keys()
                    dataset_path = list(data.keys()).pop() if len(dataset_keys) == 1 else list(data.keys())[0]
                    labeled_data = read_report_outputs_with_labels(report_file_path=report_path, dataset_path=dataset_path)

                    return labeled_data


def submit_omex_simulations(
        entrypoint: str | os.PathLike[str],
        dest_dir: str | Path,
        simulators: List[Union[Tuple[str, str], str]],
        buffer: int = 2
) -> tuple[list[Path], Path]:
    fp = get_biomodel_archive(entrypoint, dest_dir)  # if not entrypoint.endswith('.omex') else entrypoint
    omex_src_dir = Path(os.path.dirname(fp))

    # submit a simulation for each simulator specified
    output_filepaths = []
    for simulator in simulators:

        # parse simulator version
        version = "latest"
        if isinstance(simulator, tuple):
            if len(simulator) == 2:
                version = simulator[1]

        # create dedicated output dir for each simulator
        output_dest = os.path.join(dest_dir, simulator)
        if not os.path.exists(output_dest):
            os.mkdir(output_dest)
        sim_output_dest_path = Path(output_dest)

        # run the simulation
        printc(f"> Submitting simulation of {entrypoint} with {simulator}...\n")
        upload_omex(
            simulator=Simulator[f'{simulator}'],
            simulator_version=version,
            omex_src_dir=omex_src_dir,
            out_dir=sim_output_dest_path,
        )
        printc(f"> Simulation submitted for {simulator}. Waiting for {buffer} seconds...\n")

        # wait and then refresh status
        time.sleep(buffer)
        printc("> Refreshing status...\n")
        refresh_status(omex_src_dir=omex_src_dir, out_dir=sim_output_dest_path)

        # record output filepath
        output_filepaths.append(sim_output_dest_path)
        printc(f'> Simulation submission completed for {simulator}.\n')

    return output_filepaths, omex_src_dir


def fetch_simulator_output(output_dirpaths: list[Path], omex_src_dirpath: Path, buffer: int = 2) -> dict[str, BiosimulationsRunOutputData | dict[str, str] | dict]:
    output_data = {}
    for output_dirpath in output_dirpaths:
        status_updates = refresh_status(omex_src_dir=omex_src_dirpath, out_dir=output_dirpath, return_status=True)

        # iterate over each simulation in the status updates
        for sim_id in status_updates:
            print(f'Simulation status update: {sim_id}')
            status_data = status_updates[sim_id]
            terminal_statuses = ['succeeded', 'failed']
            simulator = status_data['simulator']

            while status_data['status'].lower() not in terminal_statuses:
                # status not ready, wait and re-fetch status
                print(
                    f"...{SKY_BLUE}{simulator}:{RESET} {LIGHT_PURPLE}{status_data['status']}{RESET}. Attempting another refresh..."
                )

                for n in range(buffer):
                    print(n)
                    time.sleep(1)

                status_updates = refresh_status(omex_src_dir=omex_src_dirpath, out_dir=output_dirpath, return_status=True)
                status_data = status_updates.get(sim_id, status_data)

            # status check is complete
            final_simulation_status = status_data['status'].lower()
            printc(alert=f"> Status check complete for {simulator}:", msg=f"{LIGHT_PURPLE}{final_simulation_status}{RESET}.\n")

            # download files and get data
            sim_data = {}
            if 'failed' not in final_simulation_status:
                print(f"> Run for {SKY_BLUE}{simulator}:{RESET} was successful! Now downloading simulation files...\n")
                simulator_output_zippath = download_runs(omex_src_dir=omex_src_dirpath, out_dir=output_dirpath)
                print(f"> Downloaded files for {SKY_BLUE}{simulator}{RESET} at {LIGHT_PURPLE}{simulator_output_zippath}{RESET}")
                # get the simulators output data
                sim_data = read_simulator_output_data(simulator_output_zippath, output_dirpath)
            else:
                printc(final_simulation_status, alert="AN ERROR OCCURRED: ", error=True)

            # assign simulator data
            output_data[simulator] = sim_data

        return output_data


# sim = 'vcell'
# zippath = f'fixtures/verification_request/results/BIOMD0000000399/{sim}/BIOMD0000000399/{sim}/7.7.0.13/results.zip'
# output_dirpath = f'fixtures/verification_request/results/BIOMD0000000399/{sim}/BIOMD0000000399/{sim}/7.7.0.13'
# read_simulator_output_data(zippath, output_dirpath)

# simulators = list(sorted(Simulator.__members__.keys()))
# simulators = simulators[int(len(simulators) / 2):len(simulators)]  # latter half of list
simulators = ['vcell']
buffer = 2
test_biomodel_id = 'BIOMD0000000013'
test_biomodel_output_dir = f'./fixtures/verification_request/results/{test_biomodel_id}'

simulator_outputs = generate_omex_outputs()

printc(simulator_outputs, "The final outputs")




