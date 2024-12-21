from simulation_worker.data_generator2 import generate_omex_output_data
from simulation_worker.utils import printc


def test_generate_omex_outputs():
    # sim = 'vcell'
    # zippath = f'fixtures/verification_request/results/BIOMD0000000399/{sim}/BIOMD0000000399/{sim}/7.7.0.13/results.zip'
    # output_dirpath = f'fixtures/verification_request/results/BIOMD0000000399/{sim}/BIOMD0000000399/{sim}/7.7.0.13'
    # read_simulator_output_data(zippath, output_dirpath)

    # simulators = list(sorted(Simulator.__members__.keys()))
    # simulators = simulators[int(len(simulators) / 2):len(simulators)]  # latter half of list
    simulators = ['vcell']
    buffer = 2
    test_biomodel_id = 'BIOMD0000000013'
    test_biomodel_output_dir = f'./fixtures/verification_request/results/{test_biomodel_id}'

    simulator_outputs = generate_omex_output_data(test_biomodel_id, test_biomodel_output_dir, simulators, buffer)

    printc(simulator_outputs, "The final outputs")


if __name__ == '__main__':
    test_generate_omex_outputs()
