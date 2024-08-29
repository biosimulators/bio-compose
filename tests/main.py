from bio_compose.verifier import Verifier
from bio_compose.runner import SimulationRunner
from bio_compose.composer import Composer


DEFAULT_START = 0
DEFAULT_DURATION = 10
DEFAULT_NSTEPS = 100
DEFAULT_SBML_SIMULATORS = ['amici', 'copasi', 'tellurium']

test_runner = SimulationRunner()
test_verifier = Verifier()


def test_run_smoldyn():
    assert test_runner._test_root() is not None


def test_run_utc():
    pass 


def test_verify_sbml():
    model_fp = "/Users/alexanderpatrie/Downloads/BIOMD0000000001_url.xml"
    submission = test_verifier.verify_sbml(entrypoint=model_fp, start=DEFAULT_START, end=DEFAULT_DURATION, steps=DEFAULT_NSTEPS, simulators=DEFAULT_SBML_SIMULATORS)
    print(submission)
    return submission


def test_get_verify_output(id=None):
    job_id = id or 'verification-bio_check-request-5dc81721-9c0e-481e-aa71-14c4e58a37f4-9e1cd4ab-9079-4b8e-960b-c61faa264c1c'
    output = test_verifier.get_output(job_id=job_id)
    print(output)


def test_verify_omex():
    assert test_verifier._test_root()


def test_run_composition():
    pass 


if __name__ == "__main__":
    sub = test_verify_sbml()
    test_get_verify_output(sub['job_id'])
