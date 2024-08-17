from dataclasses import asdict, dataclass
from typing import Dict, List, Union

import requests


@dataclass
class RequestError:
    error: str

    def to_dict(self):
        return asdict(self)
    

class Api:
    endpoint_root: str
    data: Dict
    submitted_jobs: List[Dict]

    def __init__(self):
        """Generic base instance which is inherited by any flavor (tag group) of the BioCompose REST API.
            Each the methods of polymorphism of this base class should pertain entirely to the tag group 
            domain with which it is associated (e.g., 'execute-simulations', 'verification', etc.) 
        """
        self.endpoint_root = "https://biochecknet.biosimulations.org"
        root_response = self._test_root()
        print(root_response)

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
        
    def get_output(self, job_id: str) -> Union[Dict[str, Union[str, Dict]], RequestError]:
        """Fetch the current state of the job referenced with `cjob_id`. If the job has not yet been processed, it will return a `status` of `PENDING`. If the job is being processed by
            the service at the time of return, `status` will read `IN_PROGRESS`. If the job is complete, the job state will be returned, optionally with included result data.

            Args:
                job_id:`str`: The id of the ob submission.

            Returns:
                The job state of the task referenced by `comparison_id`. If the job has not yet been processed, it will return a `status` of `PENDING`.
        """
        piece = f'get-output/{job_id}'
        endpoint = self._format_endpoint(piece)

        headers = {'Accept': 'application/json'}

        try:
            response = requests.get(endpoint, headers=headers)
            self._check_response(response)
            data = response.json()
            self.data[job_id] = data
            return data
        except Exception as e:
            return RequestError(error=str(e))
        