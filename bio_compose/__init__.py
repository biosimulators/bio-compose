import os
import toml

from bio_compose.api import *


pyproject_file_path = os.path.join(os.path.dirname(__file__), '..', 'pyproject.toml')
try:
    __version__ = toml.load(pyproject_file_path)['tool']['poetry']['version']
except:
    __version__ = ' '
