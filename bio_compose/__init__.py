import os
import toml

from bio_compose.api import (
    get_output,
    get_compatible_verification_simulators,
    verify,
    run_simulation
)


pyproject_file_path = os.path.join(os.path.dirname(__file__), '..', 'pyproject.toml')
try:
    __version__ = toml.load(pyproject_file_path)['tool']['poetry']['version']
except:
    __version__ = ' '


__all__ = [
    '__version__',
    'get_output',
    'get_compatible_verification_simulators',
    'verify',
    'run_simulation'
]
