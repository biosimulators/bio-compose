from datagen import printc, DataGenerator

data_generator = DataGenerator()


def test_generate_omex_outputs():
    # sim = 'vcell'
    # zippath = f'fixtures/verification_request/results/BIOMD0000000399/{sim}/BIOMD0000000399/{sim}/7.7.0.13/results.zip'
    # output_dirpath = f'fixtures/verification_request/results/BIOMD0000000399/{sim}/BIOMD0000000399/{sim}/7.7.0.13'
    # read_simulator_output_data(zippath, output_dirpath)

    # simulators = list(sorted(Simulator.__members__.keys()))
    # simulators = simulators[int(len(simulators) / 2):len(simulators)]  # latter half of list
    simulators = ['vcell']
    buffer = 7
    test_biomodel_id = 'BIOMD0000000013'
    test_biomodel_output_dir = f'./verification_request/results/{test_biomodel_id}'

    simulator_outputs = data_generator.generate_omex_output_data(test_biomodel_id, test_biomodel_output_dir, simulators, buffer)

    # printc(simulator_outputs, "The final outputs")
    printc(simulator_outputs.keys(), "The final output keys")
    import json
    with open(f'./verification_request/results/{test_biomodel_id}-outputs.json', 'w') as json_file:
        json.dump(simulator_outputs, json_file, indent=4)


if __name__ == '__main__':
    test_generate_omex_outputs()
