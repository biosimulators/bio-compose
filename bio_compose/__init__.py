import os

import toml

from bio_compose.api import *


current_dir = os.path.dirname(__file__)
repo_root = os.path.abspath(os.path.join(current_dir, '..'))
pyproject_file_path = os.path.join(repo_root, 'pyproject.toml')

__version__ = toml.load('pyproject.toml')['tool']['poetry']['version']
