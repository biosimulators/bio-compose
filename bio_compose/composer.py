import os 
import abc
from typing import * 

from requests_toolbelt.multipart.encoder import MultipartEncoder

from bio_compose.data_model import Api


class Composer(Api):
    endpoint_root: str
    data: Dict
    submitted_jobs: List[Dict]

    def __init__(self):
        """A new instance of the Verifier class. NOTE: this may clash with your record keeping in a notebook, so it is highly recommended that users
            treat instances of this class as quasi-singletons, although not necessary for fundamental interaction.
        """
        super().__init__()

    def run_composition(self, duration: int, doc: Dict):
        # TODO: finish this
        pass