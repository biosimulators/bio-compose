import traceback
import unicodedata
import re
import chardet
from dataclasses import dataclass, asdict
from typing import *
from pprint import pformat

import numpy as np
import h5py
import libsbml


@dataclass
class BaseClass:
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class BiosimulationsReportOutput(BaseClass):
    dataset_label: str
    data: np.ndarray


@dataclass
class BiosimulationsRunOutputData(BaseClass):
    report_path: str
    data: List[BiosimulationsReportOutput]


def read_report_outputs(report_file_path: str, dataset_label: str = None) -> Union[BiosimulationsRunOutputData, dict[str, str]]:
    outputs = []
    with h5py.File(report_file_path, 'r') as f:
        k = list(f.keys())
        group_path = k[0] + '/report'
        if group_path in f:
            group = f[group_path]
            label = dataset_label or 'sedmlDataSetLabels'
            dataset_labels = group.attrs[label]
            for label in dataset_labels:
                dataset_index = list(dataset_labels).index(label)
                data = group[()]
                specific_data = data[dataset_index]
                output = BiosimulationsReportOutput(dataset_label=label, data=specific_data)
                outputs.append(output)
            return BiosimulationsRunOutputData(report_path=report_file_path, data=outputs)
        else:
            return {'report_path': report_file_path, 'data': f"Group '{group_path}' not found in the file."}


def detect_encoding(file_path):
    with open(file_path, 'rb') as f:
        raw_data = f.read()
        result = chardet.detect(raw_data)
        return result


def handle_sbml_exception() -> str:
    tb_str = traceback.format_exc()
    error_message = pformat(f"time-course-simulation-error:\n{tb_str}")
    return error_message


def get_sbml_species_mapping(sbml_fp: str) -> dict:
    """

    Args:
        - sbml_fp: `str`: path to the SBML model file.

    Returns:
        Dictionary mapping of {sbml_species_names(usually the actual observable name): sbml_species_ids(ids used in the solver)}
    """
    # read file
    sbml_reader = libsbml.SBMLReader()
    sbml_doc = sbml_reader.readSBML(sbml_fp)
    sbml_model_object = sbml_doc.getModel()

    # parse and handle names/ids
    sbml_species_ids = []
    for spec in sbml_model_object.getListOfSpecies():
        spec_name = spec.name
        if not spec_name:
            spec.name = spec.getId()
        if not spec.name == "":
            sbml_species_ids.append(spec)
    names = list(map(lambda s: s.name, sbml_species_ids))
    species_ids = [spec.getId() for spec in sbml_species_ids]

    return dict(zip(names, species_ids))


def fix_non_ascii_characters(file_path, output_file):
    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()

    non_ascii_chars = set(re.findall(r'[^\x00-\x7F]', content))
    print(f"Found non-ASCII characters: {non_ascii_chars}")

    replacements = {}
    for char in non_ascii_chars:
        ascii_name = unicodedata.name(char, None)
        if ascii_name:
            ascii_equivalent = ascii_name.lower().replace(" ", "_")
            replacements[char] = ascii_equivalent
        else:
            replacements[char] = ""

    for original, replacement in replacements.items():
        content = content.replace(original, replacement)

    with open(output_file, "w", encoding="utf-8") as f:
        f.write(content)

    print(f"Fixed file saved to {output_file}")