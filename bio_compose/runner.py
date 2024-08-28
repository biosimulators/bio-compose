# Runner for interacting with the "execute-simulations" group of endpoints
import os 
import abc
from typing import * 

from requests_toolbelt.multipart.encoder import MultipartEncoder

from bio_compose.data_model import Api


class SimulationRunner(Api):
    endpoint_root: str
    data: Dict
    submitted_jobs: List[Dict]

    def __init__(self):
        """A new instance of the Verifier class. NOTE: this may clash with your record keeping in a notebook, so it is highly recommended that users
            treat instances of this class as quasi-singletons, although not necessary for fundamental interaction.
        """
        super().__init__()

    def run_smoldyn_simulation(self, smoldyn_configuration_filepath: str, duration: int = None, dt: float = None) -> Dict[str, Any]:
        """Run a smoldyn simulation using a standard Smoldyn configuration file. Please see https://www.smoldyn.org/SmoldynManual.pdf for more information on running
            simulations with Smoldyn.

            Args:
                smoldyn_configuration_filepath:`str`: The path to the Smoldyn configuration file for the given model simulation.
                duration:`int`: The duration of the simulation. If `None` is passed, duration inference will be attempted using `time_stop` parameter within the Smoldyn configuration. Defaults to `None`.
                dt:`float`: The timestep to use within the Smoldyn simulation. If `None` is passed, dt inference will be attempted using the `.dt` parameter of the loaded Smoldyn simulation. Defaults to `None`.

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
        
    def run_utc_simulation(self, sbml_filepath: str, start: int, end: int, steps: int, simulator: str) -> Dict[str, Any]:
        """Run a uniform time course simulation of the model specified in `sbml_filepath` with a supported simulator.

            Args:
                sbml_filepath:`str`: The path to a valid SBML file.
                start:`int`: The start time of the simulation.
                end:`int`: The end time of the simulation.
                steps:`int`: The number of steps to record within the ODE.
                simulator:`str`: The simulator to use. Currently, simulator choices include: `'amici'`, `'copasi'`, or `'tellurium'`.

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
    
    def generate_simularium_file(self, smoldyn_output_filepath: str, box_size: float, filename: str = None) -> Dict[str, Any]:
        """Run a Smoldyn simulation and generate a Simularium trajectory from the aforementioned simulation's outputs.

            Args:
                smoldyn_output_filepath:`str`: The path to the Smoldyn output file for the given model simulation.
                box_size:`float`: The box size to use for the Simularium trajectory.
                filename:`str`: The name of the Simularium file that is generated. If `None` is passed, a general `'simulation.simularium'` filename will be used.
                    Defaults to `None`.

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
