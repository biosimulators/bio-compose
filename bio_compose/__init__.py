import os


current_dir = os.path.dirname(__file__)
version_file_path = os.path.join(current_dir, '_VERSION')

with open(version_file_path, 'r') as f:
    __version__ = f.read().strip()


def run_simulation(*args, **kwargs):
    # TODO: implement this
    pass


def verify(*args, **kwargs):
    import time
    from bio_compose.verifier import Verifier

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
    return output
