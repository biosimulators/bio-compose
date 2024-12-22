import time
import os
from typing import *
from pathlib import Path

import numpy as np
from dotenv import load_dotenv

from biosimulations_runutils.biosim_pipeline.datamodels import Simulator
from bio_compose import get_biomodel_archive

from datagen.utils import *
from datagen.data_model import *


__all__ = [
    "DataGenerator",
]


load_dotenv('../tests/.env')


class DataGenerator:
    def __init__(self,
                 out_dir: Optional[str | Path | os.PathLike[str]] = None):
        """Singleton-like data generator used to generate time-series data for verification."""
        self.out_dir = out_dir

    def generate_omex_output_data(
            self,
            biomodel_entrypoint: str | os.PathLike[str],
            out_dir: str | Path,
            simulators: list[str | tuple[str, str]],
            fetch_buffer: int = 2
    ) -> BiosimulationsRunOutputData | dict[str, dict[str, np.ndarray | list[float]]]:
        os.makedirs(out_dir) if not os.path.exists(out_dir) else None

        # submit run
        output_dirpaths, omex_src_dirpath = self._submit_omex_simulations(
            entrypoint=biomodel_entrypoint,
            dest_dir=out_dir,
            simulators=simulators,
            buffer=fetch_buffer,
        )

        # refresh status for each output
        printc(f"> Waiting {fetch_buffer} seconds before refreshing status...\n")
        time.sleep(fetch_buffer)

        return self._fetch_simulator_outputs(output_dirpaths, omex_src_dirpath, fetch_buffer)

    def generate_sbml_output_data(
            self,
            sbml_entrypoint: str | os.PathLike[str],
            start: int,
            stop: int,
            num_steps: int,
            simulators: list[str | tuple[str, str]],
    ):
        pass

    def _submit_omex_simulations(
            self,
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
                os.makedirs(output_dest)
            sim_output_dest_path = Path(output_dest)

            # run the simulation
            printc(f"> Submitting simulation of {entrypoint} with {simulator}...\n")
            RunUtilsIO.upload_omex(
                simulator=Simulator[f'{simulator}'],
                simulator_version=version,
                omex_src_dir=omex_src_dir,
                out_dir=sim_output_dest_path,
            )
            printc(f"> Simulation submitted for {simulator}. Waiting for {buffer} seconds...\n")

            # wait and then refresh status
            time.sleep(buffer)
            printc("> Refreshing status...\n")
            RunUtilsIO.refresh_status(omex_src_dir=omex_src_dir, out_dir=sim_output_dest_path)

            # record output filepath
            output_filepaths.append(sim_output_dest_path)
            printc(f'> Simulation submission completed for {simulator}.\n')

        return output_filepaths, omex_src_dir

    def _fetch_simulator_outputs(
            self,
            output_dirpaths: list[Path],
            omex_src_dirpath: Path,
            buffer: int = 2
    ) -> dict[str, BiosimulationsRunOutputData | dict[str, str] | dict]:
        output_data = {}
        for output_dirpath in output_dirpaths:
            printc(output_dirpath, "Fetching data for output dirpath: ")
            status_updates = RunUtilsIO.refresh_status(omex_src_dir=omex_src_dirpath, out_dir=output_dirpath, return_status=True)

            # iterate over each simulation in the status updates
            for sim_id in status_updates:
                print(f'Simulation status update: {sim_id}')
                status_data = status_updates[sim_id]
                terminal_statuses = ['succeeded', 'failed']
                simulator = status_data['simulator']

                while status_data['status'].lower() not in terminal_statuses:
                    # status not ready, wait and re-fetch status
                    # printc(f"\033[5m{status_data.get('status').upper()} Attempting another refresh...\033[0m\n", f'\033[5m{simulator}\033[0m')
                    time.sleep(buffer)

                    status_updates = RunUtilsIO.refresh_status(omex_src_dir=omex_src_dirpath, out_dir=output_dirpath, return_status=True)
                    status_data = status_updates.get(sim_id, status_data)

                # status check is complete
                final_simulation_status = status_data['status'].lower()
                printc(alert=f"> Status check complete for {simulator}:", msg=final_simulation_status)

                # download files and get data
                sim_data = {}
                # run is successful
                if 'failed' not in final_simulation_status:
                    printc("Run was successful! Now downloading simulation files...", simulator)
                    simulator_output_zippath = RunUtilsIO.download_runs(omex_src_dir=omex_src_dirpath, out_dir=output_dirpath)
                    if simulator_output_zippath is not None:
                        printc(f"Downloaded files to {simulator_output_zippath}", simulator)

                        # get the simulators output data from zip file
                        if os.path.exists(simulator_output_zippath):
                            sim_data = RunUtilsIO.extract_simulator_report_outputs(simulator_output_zippath, output_dirpath)
                        else:
                            # somehow path is misconfigured
                            printc(f"{simulator_output_zippath} does not exist.", simulator, error=True)
                # run failed
                else:
                    printc(final_simulation_status, "WARNING: ")

                # assign simulator data
                output_data[str(simulator)] = sim_data

            return output_data


