from dataclasses import asdict, dataclass
import os
from functools import wraps
from typing import Dict, List, Union

import pandas as pd
import requests
from matplotlib import pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages
from matplotlib.figure import Figure


@dataclass
class RequestError:
    error: str

    def to_dict(self):
        return asdict(self)
    

class Api(object):
    """
    Base class inherited by the domain-specific polymorphisms native to this package: ``verifier.Verifier``, ``composer.Composer``, and ``runner.SimulationRunner``.

    Params:
        - **endpoint_root**: `str`: default base endpoint used by this packaging.
        - **data**: `dict`: default historical collection of data fetched by the given instance of this class.
        - **submitted_jobs**: `list[dict]`: default list of jobs submitted by the given instance.
    """

    def __init__(self):
        """
        Generic base instance which is inherited by any flavor (tag group) of the BioCompose REST API. Polymorphism of this base class should pertain entirely to the tag group domain with which it is associated (e.g., 'execute-simulations', 'verification', etc.)
        """
        self.endpoint_root = "https://biochecknet.biosimulations.org"
        self._test_root()

        self.data: Dict = {}
        self.submitted_jobs: List[Dict] = []
        self._output = {}
    
    def _format_endpoint(self, path_piece: str) -> str:
        return f'{self.endpoint_root}/{path_piece}'
    
    def _execute_request(self, endpoint, headers, multidata, query_params):
        try:
            # submit request
            response = requests.post(url=endpoint, headers=headers, data=multidata, params=query_params)
            response.raise_for_status()
            
            # check/handle output
            self._check_response(response)
            output = response.json()
            self.submitted_jobs.append(output)

            return output
        except Exception as e:
            return RequestError(error=str(e))

    def _check_response(self, resp: requests.Response) -> None:
        if resp.status_code != 200:
            raise Exception(f"Request failed:\n{resp.status_code}\n{resp.text}\n")
    
    def _test_root(self) -> Dict:
        try:
            resp = requests.get(self.endpoint_root)
            resp.raise_for_status()
        except requests.RequestException as e:
            return {'bio-check-error': f"A connection to that endpoint could not be established: {e}"}
        
    def get_output(self, job_id: str, download_dest: str = None, filename: str = None) -> Union[Dict[str, Union[str, Dict]], RequestError]:
        """
        Fetch the current state of the job referenced with `job_id`. If the job has not yet been processed, it will return a `status` of `PENDING`. If the job is being processed by the service at the time of return, `status` will read `IN_PROGRESS`. If the job is complete, the job state will be returned, optionally with included result data (either JSON or downloadable file data).

        Args:
            - **job_id**: `str`: The id of the job submission.
            - **download_dest**: `Optional[str]`: Optional directory where the file will be downloaded if the output is a file. Defaults to the current directory.
            - **filename**: `Optional[str]`: Optional filename to save the downloaded file as if the output is a file. If not provided, the filename will be extracted from the Content-Disposition header.

        Returns:
            If the output is a JSON response, return the parsed JSON as a dictionary. If the output is a file, download the file and return the filepath. If an error occurs, return a RequestError.
        """
        piece = f'get-output/{job_id}'
        endpoint = self._format_endpoint(piece)

        headers = {'Accept': 'application/json'}

        try:
            response = requests.get(endpoint, headers=headers)
            self._check_response(response)
            
            # Check the content type of the response
            content_type = response.headers.get('Content-Type')
            
            # case: response is raw data
            if 'application/json' in content_type:
                data = response.json()
                self._output = data
                self.data[job_id] = data
                return data
            # otherwise: response is downloadable file
            else:
                content_disposition = response.headers.get('Content-Disposition')
                
                # extract the filename from the Content-Disposition header
                if not filename and content_disposition:
                    filename = content_disposition.split('filename=')[-1].strip('"')
                # fallback to a default filename if none is provided or extracted
                elif not filename:
                    filename = f'{job_id}_output'

                # ensure the download directory exists
                # os.makedirs(download_dest, exist_ok=True)
                
                filepath = os.path.join(download_dest, filename)

                # Save the file
                with open(filepath, 'wb') as f:
                    f.write(response.content)
                
                data = {'results_file': filepath}
                self._output = data

                return data
        except Exception as e:
            import traceback
            tb_str = traceback.format_exc()
            error_message = (
                f"An unexpected error occurred while processing your request:\n"
                f"Error Type: {type(e).__name__}\n"
                f"Error Details: {str(e)}\n"
                f"Traceback:\n{tb_str}"
            )

            return RequestError(error=error_message)

    def get_job_status(self, job_id: str):
        output = self.get_output(job_id=job_id)
        return output.get('content').get('status')

    # -- csv and observables
    def get_observables(self, data: Dict) -> pd.DataFrame:
        """
        Get the observables passed within `data` as a flattened dataframe in which each column is: `<SPECIES NAME>_<SIMULATOR>` for each species name and simulator involved within the comparison.

        Args:
            - **data**: `Dict`: simulation output data generated from `Verifier.get_verify_output()`. This method assumes a resulting job status from the aforementioned `get` method as being `'COMPLETED'`. Tip: if the `data` does not yet have a completed status, try again.
            - **simulators**: `List[str]`: list of simulators to include in the dataframe.

        Returns:
            pd.DataFrame of observables.
        """
        dataframe = {}
        species_data_content = data['content']['results']
        species_names = list(species_data_content.keys())
        num_species = len(species_names)

        for i, species_name in enumerate(species_names):
            # for j, simulator_name in enumerate(simulators):
            species_data = data['content']['results'][species_name]
            if not isinstance(species_data, str):
                output_data = species_data.get('output_data')
                if output_data is not None:
                    for simulator_name in output_data.keys():
                        simulator_output = output_data[simulator_name]
                        colname = f"{species_name}_{simulator_name}"
                        dataframe[colname] = simulator_output

        return pd.DataFrame(dataframe)

    def export_plot(self, fig: Figure, save_dest: str) -> None:
        """
        Save a `matplotlib.pyplot.Figure` instance generated from one of this class' `visualize_` methods, as a PDF file.

        Args:
            - **fig**: `matplotlib.pyplot.Figure`: Figure instance generated from either `Verifier.visualize_comparison()` or `Verifier.visualize_outputs()`.
            - **save_dest**: `str`: Destination path to save the plot to.
        """
        with PdfPages(save_dest) as pdf:
            pdf.savefig(fig)

    def export_csv(self, data: Dict, save_dest: str):
        """
        Export the content passed in `data` as a CSV file.

        Args:
            - **data**: `Dict`: simulation output data generated from `Verifier.get_verify_output()`.
            - **save_dest**: `str`: Destination path to save the CSV file.
        """
        return self.get_observables(data).to_csv(save_dest, index=False)

    def read_observables(self, csv_path: str) -> pd.DataFrame:
        """
        Read in a dataframe generated from `Verifier.export_csv()`.
        """
        return pd.read_csv(csv_path)

    # -- tools
    def select_observables(self, observables: List[str], data: Dict) -> Dict:
        """
        Select data from the input data that is passed which should be formatted such that the data has mappings of observable names to dicts in which the keys are the simulator names and the values are arrays. The data must have content accessible at: `data['content']['results']`.
        """
        outputs = data.copy()
        result = {}
        for name, obs_data in data['content']['results'].items():
            if name in observables:
                result[name] = obs_data
        outputs['content']['results'] = result

        return outputs


def save_plot(func):
    """
    Decorator for `Api().visualize_` methods.

    Args:
        - **func**: `Callable`: Decorated `Api().visualize_` method. Currently only implemented in `Verifier()`.
    """
    @wraps(func)
    def wrapper(self, *args, **kwargs):
        fig = func(self, *args, **kwargs)
        save_dest = kwargs.get('save_dest', None)
        if save_dest is not None:
            dest = save_dest + '.pdf'
            self.export_plot(fig=fig, save_dest=dest)
    return wrapper
