from bio_compose.verifier import Verifier
from bio_compose.runner import SimulationRunner
from bio_compose.composer import Composer


def test_run_smoldyn():
    pass 


def test_run_utc():
    pass 


def test_verify_sbml():
    verifier = Verifier()
    assert verifier._test_root() is not None


def test_verify_omex():
    verifier = Verifier()
    assert verifier._test_root() is not None


def test_run_composition():
    pass 
