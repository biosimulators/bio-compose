import os
import tempfile
from typing import *
from uuid import uuid4
from dataclasses import dataclass, asdict

import numpy as np 
import pandas as pd
import requests
import seaborn as sns
import antimony
from matplotlib import pyplot as plt
from matplotlib.axes import Axes
from matplotlib.backends.backend_pdf import PdfPages
from matplotlib.figure import Figure
from requests import Response
from requests.exceptions import RequestException
from requests_toolbelt.multipart.encoder import MultipartEncoder

from bio_compose.processing_tools import generate_color_gradient
from bio_compose.data_model import Api, RequestError, save_plot


class Verifier(Api):
    """
    API for verifying (running and comparing) the results of multiple simulators for a given SBML model.
    """

    def __init__(self):
        """
        A new instance of the Verifier class. **NOTE**: this may clash with your record keeping in a notebook, so it is highly recommended that users treat instances of this class as quasi-singletons, although not necessary for fundamental interaction.
        """
        super().__init__()

    # -- api calls
    def verify_omex(
            self,
            omex_filepath: str,
            simulators: List[str] = None,
            include_outputs: bool = True,
            comparison_id: str = None,
            expected_results: str = None,
            selection_list: List[str] = None,
            rTol: float = None,
            aTol: float = None,
            _steady_state: bool = False
    ) -> Union[Dict[str, str], RequestError]:
        """
        Submit a new uniform time course comparison job to the service and return confirmation of job submission.

        Args:
            - **omex_filepath**: `str`: The path to the omex file to submit.
            - **simulators**: `List[str]`: The list of simulators to include in comparison. Defaults to all utc simulators (amici, copasi, tellurium)
            - **include_outputs**: `bool, optional`: Whether to include the output data used to calculate comparison in the job results on result fetch. Defaults to True.
            - **comparison_id**: `str, optional`: The unique identifier for the comparison job. Defaults to None. If `None` is passed, a comparison id of `bio_check-request-<UUID>` is generated.
            - **expected_results**: `str, optional`: The path to the ground expected_results report file to include in comparison. Defaults to None.
            - **selection_list**: `List[str], optional`: The list of observables to include in comparison output. Defaults to None (all observables).
            - **rTol**: `float, optional`: The relative tolerance used to determine the relative distance in a pairwise comparison.
            - **aTol**: `float, optional`: The absolute tolerance used to determine the absolute distance in a pairwise comparison.
            - **_steady_state**: `bool, optional`: Whether to include the steady state analysis job. NOTE: This feature will currently throw an error as it is not yet implemented.

        Returns:
            A dictionary containing the job submission results. **Note**: the return status should read `PENDING`.
        """
        if _steady_state is not False:
            raise NotImplementedError("The steady state analysis of model files is not yet implemented and currently under development.")

        endpoint = self._format_endpoint('verify-omex')

        # configure params
        _id = comparison_id or "bio_check-request-" + str(uuid4())
        _omex = (omex_filepath.split('/')[-1], open(omex_filepath, 'rb'), 'application/octet-stream')
        _report = (expected_results.split('/')[-1], open(expected_results, 'rb'), 'application/octet-stream') if expected_results else None
        sims = simulators or ['amici', 'copasi', 'tellurium']

        encoder_fields = {
            'uploaded_file': _omex,
            'expected_results': _report
        }

        query_params = {
            'simulators': sims,
            'include_outputs': str(include_outputs).lower(),
            'comparison_id': _id,
        }

        if selection_list:
            query_params['selection_list'] = ','.join(selection_list)
        if rTol:
            query_params['rTol'] = str(rTol)
        if aTol:
            query_params['aTol'] = str(aTol)

        multidata = MultipartEncoder(fields=encoder_fields)
        headers = {'Content-Type': multidata.content_type}

        try:
            response = requests.post(endpoint, headers=headers, data=multidata, params=query_params)
            response.raise_for_status()
            self._check_response(response)
            output = response.json()
            self.submitted_jobs.append(output)
            return output
        except Exception as e:
            return RequestError(error=str(e))

    def verify_sbml(
            self,
            entrypoint: str,
            start: int = 0,
            end: int = 10,
            steps: int = 10,
            simulators: List[str] = None,
            include_outputs: bool = True,
            comparison_id: str = None,
            expected_results: str = None,
            rTol: float = None,
            aTol: float = None,
            selection_list: List[str] = None,
            _steady_state: bool = False
    ) -> Union[Dict[str, str], RequestError]:
        """
        Submit a new uniform time course comparison job to the service and return confirmation of job submission.

        Args:
            - **entrypoint**: `str`: One of either: a path to a sbml OR an antimony model/string that can be converted to SBML. NOTE: Currently, only SBML is supported as an entrypoint.
            - **start**: `int`: The start time of the time course to include in comparison.
            - **end**: `int`: The end of the comparison job in seconds.
            - **steps**: `int`: The number of steps in the comparison job.
            - **simulators**: `List[str], optional`: The list of simulators to include in comparison. Defaults to all utc simulators (amici, copasi, tellurium)
            - **include_outputs**: `bool, optional`: Whether to include the output data used to calculate comparison in the job results on result fetch. Defaults to True.
            - **comparison_id**: `str, optional`: The unique identifier for the comparison job. Defaults to None. If `None` is passed, a comparison id of `bio_check-request-<UUID>` is generated.
            - **expected_results**: `str, optional`: The path to the ground expected_results report file to include in comparison. Defaults to None.
            - **rTol**: `float, optional`: The relative tolerance used to determine the relative distance in a pairwise comparison.
            - **aTol**: `float, optional`: The absolute tolerance used to determine the absolute distance in a pairwise comparison.
            - **selection_list**: `List[str], optional`: Observables to include in the output. If passed, all observable names NOT in this list will be excluded. Defaults to `None` (all observables).
            - **_steady_state**: `bool, optional`: Whether to include the steady state analysis job. NOTE: This feature will currently throw an error as it is not yet implemented.

        Returns:
            A dictionary containing the job submission results. **Note**: the return status should read `PENDING`.

        """
        if _steady_state is not False:
            raise NotImplementedError("The steady state analysis of model files is not yet implemented and currently under development.")

        endpoint = self._format_endpoint('verify-sbml')

        # TODO: fix and remove this
        # raise NotImplementedError("Submission of jobs with a SBML file is currently under development.")

        # handle entrypoint as antimony
        if not entrypoint.endswith('.xml'):
            dest = tempfile.mkdtemp()
            entrypoint = self._write_antimony_to_sbml(entrypoint, dest)

        sbml_fp = (entrypoint.split('/')[-1], open(entrypoint, 'rb'), 'application/octet-stream')
        _report = (expected_results.split('/')[-1], open(expected_results, 'rb'), 'application/octet-stream') if expected_results else None

        _id = comparison_id or "bio_check-request-" + str(uuid4())
        if simulators is None:
            simulators = ["copasi", "tellurium"]

        # create encoder fields
        encoder_fields = {
            'uploaded_file': sbml_fp,
            'expected_results': _report
        }

        query_params = {
            'simulators': simulators,  # ','.join(simulators),
            'include_outputs': str(include_outputs).lower(),
            'comparison_id': _id,
            'start': str(start),
            'end': str(end),
            'steps': str(steps)
        }

        if selection_list:
            query_params['selection_list'] = ','.join(selection_list)
        if rTol:
            query_params['rTol'] = str(rTol)
        if aTol:
            query_params['aTol'] = str(aTol)

        multidata = MultipartEncoder(fields=encoder_fields)
        # TODO: do we need to change the headers?
        headers = {'Content-Type': multidata.content_type}

        try:
            response = requests.post(url=endpoint, headers=headers, data=multidata, params=query_params)
            response.raise_for_status()
            self._check_response(response)
            output = response.json()
            self.submitted_jobs.append(output)
            return output
        except Exception as e:
            return RequestError(error=str(e))

    def get_rmse(self, job_id: str) -> dict:
        """
        Get root-mean-square error scoring for all simulators involved in the last completed verification job.

        Args:
            - **job_id**: `str`: The unique identifier for the verification job.

        Returns:
            A dictionary mapping of simulator names to their respective root-mean-square error scores.
        """
        try:
            output = self.get_output(job_id=job_id)
            return output['content'].get('results').get('rmse') or {}
        except Exception as e:
            import traceback
            tb_str = traceback.format_exc()
            error_message = (
                f"An unexpected error occurred while processing your request:\n"
                f"Error Type: {type(e).__name__}\n"
                f"Error Details: {str(e)}\n"
                f"Traceback:\n{tb_str}"
            )

            return {'error': error_message}

    def get_compatible(self, file: str, versions: bool = False) -> Union[List[Tuple[Any, ...]], RequestError]:
        """
        Get all simulators and optionally their versions for a given file. The File is expected to be either an OMEX/COMBINE archive or SBML file.

        Args:
            - **file**: `str`: The path to the file to be checked.
            - **versions**: `bool`: Whether to return the compatible version of the given compatible simulator. Defaults to `False`.

        Returns:
            A dictionary of compatible simulators and the referenced file.
        """
        endpoint = self._format_endpoint('get-compatible-for-verification')
        fp = (file.split('/')[-1], open(file, 'rb'), 'application/octet-stream')

        encoder_fields = {'uploaded_file': fp}
        query_params = {'versions': str(versions).lower()}

        multidata = MultipartEncoder(fields=encoder_fields)
        # TODO: do we need to change the headers?
        headers = {'Content-Type': multidata.content_type}

        try:
            response = requests.post(url=endpoint, headers=headers, data=multidata, params=query_params)
            self._check_response(response)
            response = response.json()

            output = []
            for sim_data in response['simulators']:
                name = sim_data['name']
                version = sim_data.get('version')
                if version is not None:
                    data = tuple([name, version])
                    output.append(data)
                else:
                    output.append(name)

            return output
        except Exception as e:
            return RequestError(error=str(e))

    # -- visualizations
    def visualize_outputs(
            self,
            data: Dict,
            simulators: List[str],
            output_start: int,
            output_end: int,
            num_points: int,
            hue: str = 'simulators',
            use_grid: bool = False,
            color_mapping: List[str] = None
    ) -> Figure:
        """
        Visualize simulation output data, not comparison data, with subplots for each species.

        Args:
            - **data**: `dict`: simulation output data
            - **simulators**: `list[str]`: list of simulators
            - **output_start**: `int`: start time of simulation output recording.
            - **output_end**: `int`: end time of simulation output recording.
            - **num_points**: `int`: number of points in simulation output time series.
            - **hue**: `str`: hue upon which the line plot colors are based. Options are: `'simulators'` or `'species'`. Defaults to 'simulators'. If `'simulators'` is passed, each column will be of its own color. If `'species'` is passed, each row will be of its own color.
            - **use_grid**: `bool`: whether to use a grid for each subplot. Defaults to False.
            - **color_mapping**: `list[str]`: list of colors to use for each subplot. Defaults to None.

        Returns:
            `matplotlib.pyplot.Figure` of a plot grid

        """
        # grid plot params
        species_data_content = data['content']['results']
        species_names = list(species_data_content.keys())
        num_species = len(species_names)
        num_simulators = len(simulators)

        # plot data params
        t = np.linspace(output_start, output_end, num_points + 1)  # TODO: extract this dynamically.

        simulator_hue = hue.lower() == 'simulators'
        hue_group = simulators if simulator_hue else species_names

        if color_mapping is not None:
            line_colors = color_mapping
        else:
            line_colors = generate_color_gradient(hue_group)

        # TODO: extract simulator names dynamically as well.

        fig, axes = plt.subplots(nrows=num_species, ncols=num_simulators, figsize=(15, 5 * num_species))

        if num_species == 1:
            axes = [axes]

        # iterate over grid rows
        for i, species_name in enumerate(species_names):
            # iterate over grid cols
            for j, simulator_name in enumerate(simulators):
                ax = axes[i][j]
                species_data = data['content']['results'][species_name]
                output_data = species_data.get('output_data')

                if output_data:
                    # create one plot in each column mapped to each individual simulator output (for clarity :) )
                    simulator_output = output_data[simulator_name]
                    color_index = j if simulator_hue else i
                    sns.lineplot(ax=ax, color=line_colors[color_index], x=t, y=simulator_output, label=f"{simulator_name}")

                    # set row title
                    ax.set_title(f"{species_name} simulation outputs for {simulator_name}")
                    ax.legend()
                    ax.grid(use_grid)

        # TODO: adjust this
        plt.tight_layout()
        plt.show()

        return fig

    @save_plot
    def visualize_observables(self, job_id: str, hspace: float = 0.25, use_grid: bool = False, save_dest: str = None) -> Figure:
        """
        Visualize simulation output (observables) data, not comparison data, with subplots for each species.

        Args:
            - **job_id**: `str`: job id for the simulation observable output you wish to visualize.
            - **hspace**: `float`: horizontal spacing between subplots. Defaults to 0.25.
            - **use_grid**: `bool`: whether to use a grid for each subplot. Defaults to False.
            - **save_dest**: `str`: path to save the figure. If this value is passed, the figure will be saved in pdf format to this location.

         Returns:
            `matplotlib.pyplot.Figure` of a plot grid

        Raises:
            `IOError`: If `job_id` does not contain a 'results' field.
        """
        # grab output from job id
        output = self.get_output(job_id)

        # extract the list of simulators from the `output_data` for one observable
        species_data_content = output['content'].get('results')
        if species_data_content is None:
            raise IOError(f"The job for {job_id} is either not ready or has an error. Please check the output.")
        excluded_observables = ['comparison_id', 'rmse', 'time', 'Time', 'data_generator_time', 'Time (dimensionless)']
        observables = [key for key in species_data_content.keys() if key not in excluded_observables]
        first_observable = species_data_content[observables[0]]
        simulators = list(first_observable['output_data'].keys())
        n_simulators = len(simulators)

        # create subplots
        fig, axes = plt.subplots(nrows=n_simulators, ncols=1, figsize=(15, 5 * n_simulators))

        # if only one simulator, `axes` won't be an array, so make it an array
        if n_simulators == 1:
            axes = [axes]

        # iterate over simulators and plot each observable (by iterating over observables)
        for idx, simulator in enumerate(simulators):
            ax = axes[idx]
            for observable in observables:
                value_data = species_data_content[observable]['output_data'][simulator]
                sns.lineplot(data=value_data, ax=ax, label=observable)

            sim = simulator.replace(simulator[0], simulator[0].upper())
            ax.set_title(f"{sim} Observable Results")
            ax.set_xlabel("Time")
            ax.set_ylabel("Value")
            ax.grid(use_grid)

            # hide the x-axis tick labels
            ax.set_xticks([])

        # adjust layout for better spacing
        plt.tight_layout()
        plt.subplots_adjust(hspace=hspace)
        plt.show()

        return fig

    @save_plot
    def visualize_rmse(self, job_id: str, fig_dimensions: tuple[int, int] = None, color_mapping: list[str] = None, save_dest: str = None) -> Figure:
        """
        Visualize the root-mean-squared error between simulator verification outputs as a heatmap.

        Args:
            - **job_id**: `str`: verification job id. This value can be easily derived from either of `Verifier`'s `.verify_...` methods.
            - **fig_dimensions**: `Tuple[int, int], optional`: The value to use as the `figsize` parameter for a call to `matplotlib.pyplot.figure()`. If `None` is passed, default to (8, 6).
            - **color_mapping**: `List[str], optional`: list of colors to use for each simulator in the grid. Defaults to None.
            - **save_dest**: `str`: destination at which to save figure. Defaults to `None`.

         Returns:
            `matplotlib.pyplot.Figure` of a plot grid
        """
        # extract data
        rmse_matrix = self.get_rmse(job_id)
        if 'error' in rmse_matrix.keys():
            raise IOError(f"The job for {job_id} is either not ready or has an error. Please check the output.")
        simulators = list(rmse_matrix.keys())
        n_simulators = len(simulators)

        # extract rmse data and replace None with np.nan if needed
        rmse_data = []
        for sim_name, scores in rmse_matrix.items():
            if isinstance(scores, dict):
                score_vals = list(scores.values())
                for i, v in enumerate(score_vals):
                    if v is None:
                        score_vals.remove(v)
                        score_vals.insert(i, np.nan)
                rmse_data.append(score_vals)

        if color_mapping is None:
            color_mapping = ['#1E3A8A', '#D97706']

        # set up figure
        dimensions = fig_dimensions or (8, 6)
        fig = plt.figure(figsize=dimensions)
        sns.heatmap(
            data=rmse_data,
            annot=True,
            xticklabels=simulators,
            yticklabels=simulators,
            cmap=color_mapping,
            linewidths=1
        )
        # set up plot annotations
        plt.title('Pairwise Root Mean Square Error Between Simulators')
        plt.tight_layout()
        plt.show()

        return fig

    def visualize_comparison(self, data: Dict, simulators: List[str], comparison_type='proximity', color_mapping: List[str] = None) -> Figure:
        """
        Visualize simulation comparison matrix in the form of a heatmap.

        Args:
            - **data**: `dict`: simulation output data
            - **simulators**: `list[str]`: list of simulators
            - **comparison_type**: `str`: type of comparison. Defaults to `'proximity'`.
            - **color_mapping**: `list[str]`: list of colors to use for True and False responses. Defaults to None.

        Returns:
            `matplotlib.pyplot.Figure` of a plot grid
        """
        species_data_content = data['content']['results']
        species_names = list(species_data_content.keys())
        num_species = len(species_names)

        fig, axes = plt.subplots(nrows=num_species, figsize=(15, 5 * num_species))

        if color_mapping is not None:
            true_color = color_mapping[0]
            false_color = color_mapping[1]
        else:
            true_color = '#1E3A8A'  # dark blue
            false_color = '#D97706'  # dark orange

        if num_species == 1:
            axes = [axes]

        for i, species_name in enumerate(species_names):
            ax = axes[i]
            species_data = species_data_content[species_name]
            comparison_data = [list(col.values()) for col in list(species_data[comparison_type].values())]
            sns.heatmap(
                data=comparison_data,
                ax=ax,
                annot=True,
                xticklabels=simulators,
                yticklabels=simulators,
                cmap=[false_color, true_color],
                linewidths=1
            )
            ax.set_title(f"{species_name} comparison matrix")

        plt.tight_layout()
        plt.show()

        return fig

    def _write_antimony_to_sbml(self, antimony_string: str, dest: str, model_name: str = None) -> str:
        """
        Convert an antimony model to SBML. To be used as an entrypoint validator for `Verifier().verify_sbml()`.

        Args:
            - **antimony_string**: `str`: Antimony model to convert.
            - **dest**: `str`: Destination path to save the SBML file.
            - **model_name**: `str`: Model name to use for the converted model file. Defaults to `None` (a generic `'model.xml'`).

        Returns:
            Path to the written SBML file.
        """
        ant_ret = antimony.loadAntimonyString(antimony_string)
        if ant_ret == -1:
            raise IOError(f"This antimony string cannot be converted to SBML by Antimony: {antimony_string}. Please check the model and try again.")

        filename = model_name or 'model.xml'
        file_path = os.path.join(dest, filename)
        sbml_ret = antimony.writeSBMLFile(filename=file_path)
        if sbml_ret > 0:
            return file_path
        else:
            raise IOError(f"This SBML model: {filename} cannot be written to {file_path}. Please check your paths and try again.")


class VerificationResult(dict):
    def __init__(self, data: dict):
        self.data = data
        self.update({'content': self.data.get('content')})
        self.job_id = self.data.get('content').get('job_id')
        self.verifier = Verifier()

    def rmse(self, *args, **kwargs):
        from functools import partial

        rmse = self.verifier.get_rmse(self.job_id)
        self.verifier.visualize_rmse(self.job_id, **kwargs)
        return rmse

    def observables(self):
        observables = {}
        results = self.data['content']['results']
        for obs in results.keys():
            obs_data = results[obs]
            if 'output_data' == obs_data.keys():
                observables[obs] = obs_data['output_data']

        self.verifier.visualize_observables(job_id=self.job_id)
        return observables


# tests

def test_verifier():
    # TODO: replace this
    verifier = Verifier()
    simulators = ['copasi', 'tellurium']
    sbml_fp = "../model-examples/sbml-core/Elowitz-Nature-2000-Repressilator/BIOMD0000000012_url.xml"
    end = 10
    steps = 100

    sbml_submission = verifier.verify_sbml(entrypoint=sbml_fp, steps=steps, start=0, end=end, simulators=simulators, comparison_id="notebook_test1")
    print(sbml_submission)

