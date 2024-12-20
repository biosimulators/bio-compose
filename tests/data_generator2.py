import os
import time
import urllib
import zipfile
from pathlib import Path
from tarfile import AbsolutePathError
from typing import *
from dotenv import load_dotenv

import typer

from biosimulations_runutils.biosim_pipeline.biosim_api import run_project, check_run_status
from biosimulations_runutils.biosim_pipeline.data_manager import DataManager
from biosimulations_runutils.biosim_pipeline.datamodels import Simulator, SimulationRun

from bio_compose import get_biomodel_archive
from biosimulations_runutils.common.api_utils import download_file


load_dotenv('.env')


SKY_BLUE = "\033[38;5;117m"  # Sky blue color
LIGHT_PURPLE = "\033[38;5;183m"
RESET = "\033[0m"


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

        print("> Retrieving", run.model_dump_json())

        simdir = data_manager.get_run_output_dir(run)
        if os.path.exists(simdir / "results.zip"):
            continue

        try:
            out_filepath = Path(simdir / "results.zip")
            download_file(url=f"{api_base_url}/results/" + run.simulation_id + "/download",
                          out_file=out_filepath)

            return out_filepath
        except urllib.error.HTTPError as e:
            print("Failure:", e)


def refresh_status(
        omex_src_dir: Path,
        out_dir: Path,
        return_status: bool = False,
) -> None | dict[str, str]:
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
            print(f"> project {source_omex.project_id} is already validated and published")
            continue
        if project_id is not None and source_omex.project_id != project_id:
            continue
        print(source_omex.project_id)
        run_project(source_omex=source_omex, simulator=simulator, simulator_version=simulator_version, data_manager=data_manager)


def generate_omex_outputs(entrypoint: str, dest_dir: str | Path, simulators: List[Union[Tuple[str, str], str]], buffer: int = 2):
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
        print(f"> Submitting simulation of {entrypoint} with {simulator}...\n")
        upload_omex(
            simulator=Simulator[f'{simulator}'],
            simulator_version=version,
            omex_src_dir=omex_src_dir,
            out_dir=sim_output_dest_path,
        )
        print(f"Simulation submitted for {simulator}. Waiting for {buffer} seconds...\n")

        # wait and then refresh status
        time.sleep(buffer)
        print("> Refreshing status...\n")
        refresh_status(omex_src_dir=omex_src_dir, out_dir=sim_output_dest_path)

        # record output filepath
        output_filepaths.append(sim_output_dest_path)
        print(f'> Simulation submission completed for {simulator}.\n')

    return output_filepaths, omex_src_dir


def test_generate_omex_outputs():
    test_biomodel_id = 'BIOMD0000000399'
    test_biomodel_output_dir = f'./fixtures/verification_request/results/{test_biomodel_id}'
    # simulators = list(Simulator.__members__.keys())
    simulators = ['vcell']
    buffer = 7

    os.mkdir(test_biomodel_output_dir) if not os.path.exists(test_biomodel_output_dir) else None

    # submit run
    output_dirpaths, omex_src_dirpath = generate_omex_outputs(
        entrypoint=test_biomodel_id,
        dest_dir=test_biomodel_output_dir,
        simulators=simulators,
        buffer=buffer,
    )

    # refresh status for each output
    print(f"> Waiting {buffer} seconds before refreshing status...\n")
    time.sleep(buffer)

    output_data = {}
    for output_dirpath in output_dirpaths:
        status_updates = refresh_status(omex_src_dir=omex_src_dirpath, out_dir=output_dirpath, return_status=True)

        # iterate over each simulation in the status updates
        for sim_id in status_updates:
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
            print(f"> Status check complete for {SKY_BLUE}{simulator}:{RESET} {LIGHT_PURPLE}{status_data.get('status')}{RESET}.\n")

            # download files
            simulator_output_zippath = download_runs(omex_src_dir=omex_src_dirpath, out_dir=output_dirpath)
            print(f"> Downloaded files for {simulator} at {simulator_output_zippath}")

            # unzip output files
            with zipfile.ZipFile(simulator_output_zippath, 'r') as zip_ref:
                zip_ref.extractall(output_dirpath)

            # read report.h5
            for filepath in os.listdir(output_dirpath):
                if filepath.endswith(".h5"):
                    # call io method here
                    print(f"Report File: {filepath}")


test_generate_omex_outputs()




