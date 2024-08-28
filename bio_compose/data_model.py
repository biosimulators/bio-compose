from dataclasses import asdict, dataclass
import os
from typing import Dict, List, Union

import requests


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
            return resp.json()
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
                
                return {'results_file': filepath}

        except Exception as e:
            return RequestError(error=str(e))
        