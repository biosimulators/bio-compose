# Runner for interacting with the "execute-simulations" group of endpoints
import os 
import abc
from typing import * 

from requests_toolbelt.multipart.encoder import MultipartEncoder

from bio_compose.data_model import Api, save_plot


class SimulationRunner(Api):
    """
    API which handles all aspects of running either UTC or Smoldyn (Brownian Motion) simulations using the REST API.
    """

    def __init__(self):
        """
        A new instance of the SimulationRunner class. NOTE: this may clash with your record keeping in a notebook, so it is highly recommended that users treat instances of this class as quasi-singletons, although not necessary for fundamental interaction.
        """
        super().__init__()

    def run_smoldyn_simulation(self, smoldyn_configuration_filepath: str, duration: int = None, dt: float = None) -> Dict:
        """
        Run a smoldyn simulation using a standard Smoldyn configuration file. Please see https://www.smoldyn.org/SmoldynManual.pdf for more information on running simulations with Smoldyn.

        Args:
            - **smoldyn_configuration_filepath**: `str`: The path to the Smoldyn configuration file for the given model simulation.
            - **duration**: `int`: The duration of the simulation. If `None` is passed, duration inference will be attempted using `time_stop` parameter within the Smoldyn configuration. Defaults to `None`.
            - **dt**: `float`: The timestep to use within the Smoldyn simulation. If `None` is passed, dt inference will be attempted using the `.dt` parameter of the loaded Smoldyn simulation. Defaults to `None`.

        Returns:
            The response for the Smoldyn simulation submission request.

        """
        endpoint = self._format_endpoint(f'run-smoldyn')
        
        # multipart
        input_fp = (smoldyn_configuration_filepath.split('/')[-1], open(smoldyn_configuration_filepath, 'rb'), 'application/octet-stream')
        encoder_fields = {'uploaded_file': input_fp}
        multidata = MultipartEncoder(fields=encoder_fields)

        # query and headers
        query_params = {}
        query_args = [('duration', duration), ('dt', dt)]
        for arg in query_args:
            if arg[1] is not None:
                query_params[arg[0]] = str(arg[1])

        headers = {'Content-Type': multidata.content_type}

        return self._execute_request(endpoint=endpoint, headers=headers, multidata=multidata, query_params=query_params)
        
    def run_utc_simulation(self, sbml_filepath: str, start: int, end: int, steps: int, simulator: str) -> Dict:
        """
        Run a uniform time course simulation of the model specified in `sbml_filepath` with a supported simulator.

        Args:
            - **sbml_filepath**: `str`: The path to a valid SBML file.
            - **start**: `int`: The start time of the simulation.
            - **end**: `int`: The end time of the simulation.
            - **steps**: `int`: The number of steps to record within the ODE.
            - **simulator**: `str`: The simulator to use. Currently, simulator choices include: `'amici'`, `'copasi'`, or `'tellurium'`.

        Returns:
            The response for the UTC simulation submission request.
        """
        endpoint = self._format_endpoint(f'run-utc')

        # multipart 
        input_fp = (sbml_filepath.split('/')[-1], open(sbml_filepath, 'rb'), 'application/octet-stream')
        encoder_fields = {'uploaded_file': input_fp}
        multidata = MultipartEncoder(fields=encoder_fields)

        # query and headers
        query_params = {
            'start': str(start), 
            'end': str(end),
            'steps': str(steps),
            'simulator': simulator
        }
        headers = {'Content-Type': multidata.content_type}

        return self._execute_request(endpoint=endpoint, headers=headers, multidata=multidata, query_params=query_params)
    
    def generate_simularium_file(self, smoldyn_output_filepath: str, box_size: float, filename: str = None) -> Dict:
        """
        Run a Smoldyn simulation and generate a Simularium trajectory from the aforementioned simulation's outputs.

        Args:
            - **smoldyn_output_filepath**: `str`: The path to the Smoldyn output file for the given model simulation.
            - **box_size**: `float`: The box size to use for the Simularium trajectory.
            - **filename**: `str`: The name of the Simularium file that is generated. If `None` is passed, a general `'simulation.simularium'` filename will be used. Defaults to `None`.

        Returns:
            The response for the Simularium submission request.
        """
        endpoint = self._format_endpoint(f'generate-simularium-file')

        # multipart 
        input_fp = (smoldyn_output_filepath.split('/')[-1], open(smoldyn_output_filepath, 'rb'), 'application/octet-stream')
        encoder_fields = {'uploaded_file': input_fp}
        multidata = MultipartEncoder(fields=encoder_fields)

        # query
        query_params = {'box_size': str(box_size)}
        if filename is not None:
            query_params['filename'] = filename

        # headers 
        headers = {'Content-Type': multidata.content_type}

        return self._execute_request(endpoint=endpoint, headers=headers, multidata=multidata, query_params=query_params)

    @save_plot
    def visualize_observables(self, job_id: str, hspace: float = 0.25, use_grid: bool = False, save_dest: str = None):
        """
        Visualize simulation output (observables) data.
        Args:
            - **job_id**: `str`: job id for the simulation observables output you wish to visualize.
            - **hspace**: `float`: horizontal spacing between subplots. Defaults to 0.25.
            - **use_grid**: `bool`: whether to use a grid for each subplot. Defaults to False.
            - **save_dest**: `str`: path to save the figure. If this value is passed, the figure will be saved in pdf format to this location.
         Returns:
            `Tuple[matplotlib.Figure, Dict]` of matplotlib Figure and simulation observables.
        Raises:
            `IOError`: If `job_id` does not contain a 'results' field.
        """
        import matplotlib.pyplot as plt 
        import seaborn as sns
        
        # grab output from job id
        output = self.get_output(job_id)
        fig = plt.figure()
        species_data_content = output['content'].get('results')
        sns.lineplot(data=species_data_content)

        # adjust layout for better spacing
        plt.tight_layout()
        plt.subplots_adjust(hspace=hspace)
        plt.show()

        species_data_content['source'] = output['content'].get('source')

        return fig, species_data_content


class SimulationResult(dict):
    def __init__(self, data: dict):
        self.data = data
        self.update({'content': self.data.get('content')})
        self.job_id = self.data.get('content').get('job_id')
        self.runner = SimulationRunner()

    def visualize(self, **kwargs):
        return self.runner.visualize_observables(job_id=self.job_id, **kwargs)