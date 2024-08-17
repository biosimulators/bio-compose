from bio_compose.verifier import Verifier
from bio_compose.runner import SimulationRunner
from bio_compose.composer import Composer


DEFAULT_DURATION = 5

test_runner = SimulationRunner()
test_verifier = Verifier()


def test_run_smoldyn():
    assert test_runner._test_root() is not None


def test_run_utc():
    pass 


def test_verify_sbml():
    assert test_verifier._test_root() is not None


def test_verify_omex():
    assert test_verifier._test_root() is not None


def test_run_composition():
    pass 
