import os

from bio_compose.api import *


current_dir = os.path.dirname(__file__)
version_file_path = os.path.join(current_dir, '_VERSION')


with open(version_file_path, 'r') as f:
    __version__ = f.read().strip()
    

# def run_simulation(*args, **kwargs) -> SimulationResult:
#     """Run a simulation with BioCompose.
#
#     :param args: Positional arguments
#
#     * 1 argument: smoldyn simulation configuration in which time parameters (dt, duration) are already defined. **Smoldyn simulation only**.
#     * 3 arguments: smoldyn configuration file, smoldyn simulation duration, smoldyn simulation dt. **Smoldyn simulation only**.
#     * 5 arguments: sbml filepath, simulation start, simulation end, simulation steps, simulator. **SBML simulation only**.
#
#     :param kwargs: Keyword arguments
#
#     :return: instance of simulation results.
#     :rtype: bio_compose.runner.SimulationResult
#     """
#     # set up submission
#     runner = SimulationRunner()
#     in_file = args[0]
#     n_args = len(args)
#     submission = None
#
#     if n_args == 1:
#         submission = runner.run_smoldyn_simulation(smoldyn_configuration_filepath=in_file)
#     elif n_args == 3:
#         dur = args[1]
#         dt = args[2]
#         submission = runner.run_smoldyn_simulation(smoldyn_configuration_filepath=in_file, duration=dur, dt=dt)
#     elif n_args == 5:
#         start = args[1]
#         end = args[2]
#         steps = args[3]
#         simulator = args[4]
#         submission = runner.run_utc_simulation(sbml_filepath=in_file, start=start, end=end, steps=steps, simulator=simulator)
#
#     # fetch result params
#     job_id = submission.get('job_id')
#     output = {}
#     timeout = kwargs.get('timeout', 100)
#
#     # poll gateway for results
#     i = 0
#     if job_id is not None:
#         print(f'Submission Results for Job ID {job_id}: ')
#         while True:
#             if i == timeout:
#                 break
#             simulation_result = runner.get_output(job_id=job_id)
#             if isinstance(simulation_result, dict):
#                 status = simulation_result['content']['status']
#                 last4 = get_job_signature(job_id)
#                 if not 'COMPLETED' in status:
#                     print(f'Status for job ending in {last4}: {status}')
#                     i += 1
#                     time.sleep(1)
#                 else:
#                     output = simulation_result
#                     break
#             else:
#                 i += 1
#
#     return SimulationResult(data=output)
#
#
# def verify(*args, **kwargs) -> VerificationResult:
#     """Verify and compare the outputs of simulators for a given entrypoint file of either sbml or omex.
#
#     :param args: Positional arguments
#
#     * 1 argument: submit omex verification with no time params. **OMEX verification only**.
#     * 2 arguments: omex filepath, simulators to include in the verification. **OMEX verification only**.
#     * 4 arguments: sbml filepath, start, stop, steps. **SBML verification only**.
#     * 5 arguments: sbml filepath, start, stop, steps, simulators. **SBML verification only**.
#
#     :param kwargs: keyword arguments passed to the verification.
#
#     * keyword arguments either of the `bio_compose.verifier.Verifier.verify_...` methods. See verifier module documentation for more details.
#     * timeout: (`int`) number of iterations to perform polling before function halts. Defaults to 50
#     * buffer_time: (`Union[int, float]`) initial buffer time of data-fetching. Defaults to 5
#     * poll_time: (`Union[int, float]`) poll time of data-fetching which is applied if the result is not yet ready.
#     * verbose: (`bool`) whether to print status updates to stdout. Defaults to True.
#
#     :return: instance of verification results.
#     :rtype: bio_compose.runner.VerificationResult
#     """
#     verifier = Verifier()
#     if len(args) == 2:
#         simulators = args[1]
#     else:
#         simulators = kwargs.get('simulators')
#     run_sbml = False
#     for arg in args:
#         if isinstance(arg, int):
#             run_sbml = True
#     submission = None
#
#     # parse executor
#     if run_sbml:
#         submission = verifier.verify_sbml(*args, **kwargs)
#     else:
#         submission = verifier.verify_omex(*args, **kwargs)
#
#     # fetch params
#     job_id = submission.get('job_id')
#     timeout = kwargs.get('timeout', 50)
#     buffer_time = kwargs.get('buffer_time', 5)
#     poll_time = kwargs.get('poll_time', 5)
#     verbose = kwargs.get('verbose', True)
#
#     # poll gateway for results
#     n_attempts = 0
#     output = {}
#     if job_id is not None:
#         # submit request and buffer
#         verification_result = verifier.get_output(job_id=job_id)
#         msg = ''
#         for _ in range(buffer_time):
#             msg += '='
#             print("Submitting verification " + msg + ">", end='\r') if verbose else None
#             time.sleep(0.2)
#
#         # confirm submission
#         complete = "".join(["=" for _ in range(buffer_time)])
#         time.sleep(0.2)
#         initial_status = verification_result.get('content', {}).get('status', '')
#         if initial_status.startswith("SUBMITTED"):
#             print("Submitting verification " + complete + ">" + f" verification submitted!\n") if verbose else None
#             print(f"VERIFICATION JOB ID:\n{job_id}\n") if verbose else None
#             time.sleep(0.5)
#
#         # set output data from result data if it is ready, otherwise sleep and reiterate
#         current_status = verifier.get_output(job_id=job_id).get('content', {}).get('status', '')
#         # polling loop
#         while True:
#             # dynamic message render
#             status_message = f'Status for job ending in {get_job_signature(job_id)}: {current_status} '
#             message = ''
#             if not "COMPLETED" in current_status or "FAILED" in current_status:
#                 for _ in range(poll_time * 4):
#                     print("".join([" " for _ in message]), end='\r') if verbose else None
#                     message += '='
#                     print("Running verification " + message + ">", end='\r') if verbose else None
#                     time.sleep(0.1)
#                 message += ">"
#                 print(f'Running verification {message} {status_message}') if verbose else None
#             else:
#                 print(f'\nVerification complete!') if verbose else None
#                 output = verifier.get_output(job_id=job_id)
#                 break
#
#             if 'FAILED' in current_status:
#                 output = {}
#                 break
#
#             if not 'COMPLETED' in current_status:
#                 # quit iteration if timeout is reached
#                 if n_attempts == timeout:
#                     break
#                 # iteration
#                 n_attempts += 1
#                 current_status = verifier.get_output(job_id=job_id).get('content', {}).get('status', '')
#             else:
#                 output = verifier.get_output(job_id=job_id)
#                 break
#
#     return VerificationResult(data=output)
