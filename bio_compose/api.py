import os
import time
import warnings
import zipfile
from typing import *

import requests

from bio_compose.processing_tools import get_job_signature
from bio_compose.runner import SimulationRunner, SimulationResult
from bio_compose.verifier import Verifier, VerificationResult


__all__ = [
    'DEFAULT_SBML_SIMULATORS',
    'DEFAULT_N_STEPS',
    'DEFAULT_START_TIME',
    'DEFAULT_STOP_TIME',
    'get_biomodel_file',
    'get_biomodel_archive',
    'get_output',
    'get_compatible_verification_simulators',
    'verify',
    'run_simulation',
    'run_batch_verification',
    'visualize_observables'
]

API_VERIFIER = Verifier()
API_RUNNER = SimulationRunner()
DEFAULT_SBML_SIMULATORS = ['amici', 'copasi', 'pysces', 'tellurium']
DEFAULT_START_TIME = 0
DEFAULT_STOP_TIME = 10
DEFAULT_N_STEPS = 100


def get_output(job_id: str, download_dest: str = None, filename: str = None) -> Dict:
    """
    Fetch the current state of the job referenced with `job_id`. If the job has not yet been processed, it will return a `status` of `PENDING`. If the job is being processed by the service at the time of return, `status` will read `IN_PROGRESS`. If the job is complete, the job state will be returned, optionally with included result data (either JSON or downloadable file data).

    :param job_id: (`str`) The id of the job submission.
    :param download_dest: (`Optional[str]`) **File download outputs only**. Optional directory where the file will be downloaded if the output is a file. Defaults to the current directory.
    :param filename: (`Optional[str]`) **File download outputs only**. Optional filename to save the downloaded file as if the output is a file. If not provided, the filename will be extracted from the Content-Disposition header.

    :return: If the output is a JSON response, return the parsed JSON as a dictionary. If the output is a file, download the file and return the filepath. If an error occurs, return a RequestError.
    :rtype: `Dict`
    """
    return API_VERIFIER.get_output(job_id)


def get_compatible_verification_simulators(entrypoint_file: str, return_versions: bool = False):
    """
    Get all simulators and optionally their versions for a given file. The File is expected to be either an OMEX/COMBINE archive or SBML file.

    :param entrypoint_file: (`str`) The path of the file to be checked.
    :param return_versions: (`bool`) Whether to return the compatible version of the given compatible simulator. Defaults to `False`.

    :return: A list of compatible simulators and the current compatible version of the given compatible simulator.
    :rtype: `List[Union[Tuple[str, str], str]`
    """
    return API_VERIFIER.get_compatible(entrypoint_file, return_versions)


def verify(*args) -> VerificationResult:
    """Verify and compare the outputs of simulators for a given entrypoint file of either sbml or omex.

    :param args: Positional arguments

    * 1 argument: submit omex verification with no time params. **OMEX verification only**.
    * 2 arguments: omex filepath, simulators to include in the verification. **OMEX verification only**.
    * 4 arguments: sbml filepath, start, stop, steps. **SBML verification only**.
    * 5 arguments: sbml filepath, start, stop, steps, simulators. **SBML verification only**.

    :return: instance of verification results.
    :rtype: bio_compose.verifier.VerificationResult
    """
    verifier = API_VERIFIER

    if len(args) == 0:
        raise ValueError('At least one positional argument defining a file entrypoint is required.')

    if len(args) == 2:
        simulators = args[1]
    elif len(args) == 5:
        simulators = args[4]
    else:
        simulators = DEFAULT_SBML_SIMULATORS

    run_sbml = False
    for arg in args:
        if isinstance(arg, int):
            run_sbml = True
    submission = None

    # parse executor and run
    timeout = 50
    buffer_time = 5
    poll_time = 5
    submission_generator = verifier.verify_sbml if run_sbml else verifier.verify_omex
    print("Submitting verification...", end='\r')
    time.sleep(buffer_time)

    # fetch params
    submission = submission_generator(*args)
    time.sleep(1)
    job_id = submission.get('job_id') if submission else None

    # poll gateway for results
    n_attempts = 0
    output = {}
    if job_id is not None:
        # polling loop
        while True:
            # quit after reaching timeout
            n_attempts += 1
            if n_attempts == timeout:
                print('Timeout reached. Please try to call the function again.')
                break

            # get result after buffering (submission) or refresh if re-iteration
            verification_result = verifier.get_output(job_id=job_id)

            # report job status
            current_status = verifier.get_output(job_id=job_id).get('content', {}).get('status', '')
            print(f'> Status for job ending in {get_job_signature(job_id)}: {current_status} ')

            # finish if job failed or completed, otherwise re-poll
            stop_conditions = ["COMPLETED", "FAILED"]
            job_finished = any([current_status.endswith(condition) for condition in stop_conditions])
            if not job_finished:
                time.sleep(poll_time)
            else:
                output = verifier.get_output(job_id=job_id)
                break
    else:
        return VerificationResult({'content': {'job_id': 'A job ID could not be identified.'}})

    return VerificationResult(data=output)


def run_simulation(*args, **kwargs) -> SimulationResult:
    """Run a simulation with BioCompose.

    :param args: Positional arguments to be unpacked

    * 1 argument: smoldyn simulation configuration in which time parameters (dt, duration) are already defined. **Smoldyn simulation only**.
    * 3 arguments: smoldyn configuration file, smoldyn simulation duration, smoldyn simulation dt. **Smoldyn simulation only**.
    * 5 arguments: sbml filepath, simulation start, simulation end, simulation steps, simulator. **SBML simulation only**.

    :param kwargs: Keyword arguments

    :return: instance of simulation results.
    :rtype: bio_compose.runner.SimulationResult
    """
    # set up submission
    runner = SimulationRunner()
    in_file = args[0]
    n_args = len(args)
    submission = None
    if n_args == 1:
        submission = runner.run_smoldyn_simulation(smoldyn_configuration_filepath=in_file)
    elif n_args == 3:
        dur = args[1]
        dt = args[2]
        submission = runner.run_smoldyn_simulation(smoldyn_configuration_filepath=in_file, duration=dur, dt=dt)
    elif n_args == 5:
        start = args[1]
        end = args[2]
        steps = args[3]
        simulator = args[4]
        submission = runner.run_utc_simulation(sbml_filepath=in_file, start=start, end=end, steps=steps, simulator=simulator)
    # fetch result params
    job_id = submission.get('job_id')
    output = {}
    timeout = kwargs.get('timeout', 100)
    # poll gateway for results
    i = 0
    if job_id is not None:
        print(f'Submission Results for Job ID {job_id}: ')
        while True:
            if i == timeout:
                break
            simulation_result = runner.get_output(job_id=job_id)
            if isinstance(simulation_result, dict):
                status = simulation_result['content']['status']
                last4 = get_job_signature(job_id)
                if not 'COMPLETED' in status:
                    print(f'Status for job ending in {last4}: {status}')
                    i += 1
                    time.sleep(1)
                else:
                    output = simulation_result
                    break
            else:
                i += 1
    return SimulationResult(data=output)


def visualize_observables(job_id: str, save_dest: str = None, hspace: float = 0.25, use_grid: bool = False):
    """
    Visualize simulation output (observables) data, not comparison data, with subplots for each species.

    :param job_id: (`str`) job id for the simulation observable output you wish to visualize.
    :param save_dest: (`str`) path to save the figure. If this value is passed, the figure will be saved in pdf format to this location.
    :param hspace: (`float`) horizontal spacing between subplots. Defaults to 0.25.
    :param use_grid: (`bool`) whether to use a grid for each subplot. Defaults to False.
    
    :return: matplotlib Figure and simulation observables indexed by simulator
    :rtype: `Tuple[matplotlib.Figure, Dict]` 
    """
    return API_VERIFIER.visualize_observables(job_id=job_id, save_dest=save_dest, hspace=hspace, use_grid=use_grid)


def visualize_rmse(job_id: str, save_dest: str = None, fig_dimensions: tuple[int, int] = None, color_mapping: list[str] = None):
    """
    Visualize the root-mean-squared error between simulator verification outputs as a heatmap.

    :param job_id: (`str`) verification job id. This value can be easily derived from either of `Verifier`'s `.verify_...` methods.
    :param save_dest: `(str`) destination at which to save figure. Defaults to `None`.
    :param fig_dimensions: (`Tuple[int, int], optional`) The value to use as the `figsize` parameter for a call to `matplotlib.pyplot.figure()`. If `None` is passed, default to (8, 6).
    :param color_mapping: (`List[str], optional`) list of colors to use for each simulator in the grid. Defaults to None.
    
    :return: matplotlib Figure and simulator RMSE scores
    :rtype: `Tuple[matplotlib.Figure, Dict]`
    """
    return API_VERIFIER.visualize_rmse(job_id=job_id, save_dest=save_dest, fig_dimensions=fig_dimensions, color_mapping=color_mapping)


def get_biomodel_archive(model_id: str, dest_dir: Optional[str] = None) -> str:
    """
    Download all files for a given Biomodel as an OMEX archive from the Biomodels REST API, optionally specifying a download destination. *NOTE*: This file may be opened as a typical zip file.

    :param model_id: (`Union[str, List[str]]`) A single biomodel id as a string or a list of biomodel ids as strings.
    :param dest_dir: (`str`) destination directory at which to save downloaded file. If `None` is passed, downloads to cwd. Defaults to `None`.

    :return: Filepath of the downloaded biomodel OMEX(zip) archive
    :rtype: `str`
    """
    base_url = "https://www.ebi.ac.uk/biomodels/model/download"
    url = f"{base_url}/{model_id}"
    params = {}

    try:
        resp = requests.get(url, params=params, stream=True)

        if resp.status_code == 200:
            dest = dest_dir or os.getcwd()
            fp = os.path.join(dest, f"{model_id}.omex")
            with open(fp, "wb") as file:
                for chunk in resp.iter_content(chunk_size=8192):
                    file.write(chunk)
            print(f"File downloaded successfully and saved as {fp}")

            return fp
        elif resp.status_code == 400:
            warnings.warn("Error 400: File Not Found")
        elif resp.status_code == 404:
            warnings.warn("Error 404: Invalid Model ID Supplied")
        else:
            warnings.warn(f"Unexpected error: {resp.status_code} - {resp.text}")
    except requests.RequestException as e:
        warnings.warn(f"An error occurred: {e}")


def get_biomodel_file(model_query: Union[str, List[str]], dest_dir: Optional[str] = None) -> str:
    """
    Download a model file (SBML) from the Biomodels REST API, optionally specifying a download destination.

    :param model_query: (`Union[str, List[str]]`) A single biomodel id as a string or a list of biomodel ids as strings.
    :param dest_dir: (`str`) destination directory at which to save downloaded file. If `None` is passed, downloads to cwd. Defaults to `None`.

    :return: Filepath of the downloaded biomodel file as a .zip file.
    :rtype: `str`
    """
    url = "https://www.ebi.ac.uk/biomodels/search/download"
    query = ",".join(model_query) if isinstance(model_query, list) else model_query
    params = {"models": query}

    if not os.path.exists(dest_dir):
        os.mkdir(dest_dir)

    try:
        response = requests.get(url, params=params, stream=True)
        if response.status_code == 200:
            file_name = f"{query}.zip" if isinstance(model_query, str) else "multiple.zip"
            dest = dest_dir or os.getcwd()
            zip_fp = os.path.join(dest, file_name)
            with open(zip_fp, "wb") as file:
                for chunk in response.iter_content(chunk_size=8192):
                    file.write(chunk)
            sbml_fp = extract_sbml_from_zip(zip_fp, dest_dir)
            os.remove(zip_fp)

            return sbml_fp
        elif response.status_code == 400:
            warnings.warn("Error 400: File Not Found")
        elif response.status_code == 404:
            warnings.warn("Error 404: Invalid Model ID Supplied")
        else:
            warnings.warn(f"Unexpected error: {response.status_code} - {response.text}")
    except requests.RequestException as e:
        return f"An error occurred: {e}"


def extract_sbml_from_zip(zip_path: str, output_dir: str):
    """
    Extract a single XML(SBML) file from a zip archive retrieved from BioModels to a specified directory.

    :param zip_path: (`str`) Path to the zip file.
    :param output_dir: (`str`) Directory where the extracted file will be saved.
    """
    os.makedirs(output_dir, exist_ok=True)

    with zipfile.ZipFile(zip_path, 'r') as zip_ref:
        for file_name in zip_ref.namelist():
            if file_name.endswith('.xml'):
                zip_ref.extract(file_name, output_dir)
                print(f"Extracted {file_name} to {output_dir}")
                break
            return os.path.join(output_dir, file_name)
        else:
            print("No XML file found in the zip archive.")


def run_batch_sbml_verification(model_files: list[str], start: int, stop: int, steps: int) -> Dict[str, VerificationResult]:
    """
    Run several SBML verifications as a batch job.

    :param model_files: (`list[str]`) A list of biomodel SBML files to verify.
    :param start: (`int`) Simulation start time.
    :param stop: (`int`) Simulation stop time.
    :param steps: (`int`) Number of simulation steps to record.

    :return: Verification results indexed by verification Job ID.
    :rtype: `dict`
    """
    results = {}
    for model_file in model_files:
        verification = verify(model_file, start, stop, steps)
        results[verification.job_id] = verification

    return results


def run_batch_verification(input_files: list[str], *args) -> Dict[str, VerificationResult]:
    """
    Run several verifications as a synchronous batch, returning a dictionary of verification results indexed by verification job ID.

    :param input_files: (`list[str]`) A list of biomodel SBML files to verify.
    :param args: Positional arguments to use as unpacked arguments in `run_batch_verification` related to the verification scope (SBML-only/OMEX): if sbml verifications, start, stop, steps.

    :return: Verification results indexed by verification Job ID.
    :rtype: `dict`
    """
    results = {}
    for input_file in input_files:
        verification = verify(input_file, *args)
        results[verification.job_id] = verification

    return results
