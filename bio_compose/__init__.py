import os


current_dir = os.path.dirname(__file__)
version_file_path = os.path.join(current_dir, '_VERSION')

with open(version_file_path, 'r') as f:
    __version__ = f.read().strip()


def run_simulation(*args, **kwargs):
    # TODO: implement this
    pass


def verify(*args, **kwargs):
    """
    Verify and compare the outputs of simulators for a given entrypoint file of either sbml or omex.

    Args:
        - **args**: positional arguments passed to the verification.
            - 1 argument(`str`): submit an sbml or omex verification with no time params.
            - 2 arguments(`str`, `list[str]`): omex filepath, simulators to include in the verification.
            - 4 arguments(`str`, `int`, `int`, `int`): sbml filepath, start, stop, steps.
            - 5 arguments(`str`, `int`, `int`, `int`, `list[str]`): sbml filepath, start, stop, steps, simulators.
        - **kwargs**: keyword arguments passed to the verification.

    Returns:
        Verification result instance. See documentation for more details.
    """
    import time
    from bio_compose.verifier import Verifier
    from bio_compose.verifier import VerificationResult

    verifier = Verifier()
    simulators = kwargs.get('simulators')
    run_sbml = False
    for arg in args:
        if isinstance(arg, int):
            run_sbml = True
    submission = None
    if run_sbml:
        submission = verifier.verify_sbml(*args, **kwargs)
    else:
        submission = verifier.verify_omex(*args, **kwargs)
    job_id = submission.get('job_id')
    output = None
    if job_id is not None:
        while True:
            verification_result = verifier.get_output(job_id=job_id)
            status = verification_result['content']['status']
            if not 'COMPLETED' in status:
                time.sleep(1)
            else:
                output = verification_result
                break

    return VerificationResult(data=output)
