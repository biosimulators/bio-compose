import traceback
import unicodedata
import re
from os import PathLike

import chardet
from dataclasses import dataclass, asdict
from typing import *
from pprint import pformat, pp
import pprint

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


class ReportDataSet(dict):
    pass


class ReportDataSetPath(str):
    pass


class SbmlSpeciesMapping(dict):
    pass


SKY_BLUE = "\033[38;5;117m"  # Sky blue color
LIGHT_PURPLE = "\033[38;5;183m"
ERROR_RED = "\033[31m"
RESET = "\033[0m"


def printc(msg: Any, alert: str = '', error=False):
    prefix = f"> {SKY_BLUE if not error else ERROR_RED}{alert if not error else 'AN ERROR OCCURRED'}:{RESET}"
    message = f"{LIGHT_PURPLE if not error else ERROR_RED}{msg}{RESET}\n"
    print(f"> {prefix if alert else None} {message}")


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


def read_report_outputs_with_labels(
        report_file_path: str,
        # dataset_path: str,
        return_as_dict: bool = True,
        dataset_label_id: str = 'sedmlDataSetLabels'
) -> dict[str, np.ndarray] | BiosimulationsRunOutputData:
    with h5py.File(report_file_path, 'r') as sedml_group:
        # get the dataset path for reports within sedml group
        dataset_path = get_report_dataset_path(report_file_path)
        dataset = sedml_group[dataset_path]

        if return_as_dict:
            # check if dataset has attributes for labels
            if dataset_label_id in dataset.attrs:
                labels = [label.decode('utf-8') for label in dataset.attrs[dataset_label_id]]
            else:
                raise ValueError(f"No dataset labels found in the attributes with the name '{dataset_label_id}'.")

            data = dataset[()]
            return {label: data[idx] for idx, label in enumerate(labels)}
        else:
            outputs = []
            ds_labels = [label.decode('utf-8') for label in dataset.attrs[dataset_label_id]]
            for label in ds_labels:
                dataset_index = list(ds_labels).index(label)
                data = dataset[()]
                specific_data = data[dataset_index]
                output = BiosimulationsReportOutput(dataset_label=label, data=specific_data)
                outputs.append(output)

            return BiosimulationsRunOutputData(report_path=report_file_path, data=outputs)


def find_datasets(group: h5py.File | h5py.Group, group_path="") -> dict[str, np.ndarray]:
    matching_datasets = {}
    for name, obj in group.items():
        full_path = f"{group_path}/{name}" if group_path else name
        if "report" in full_path:
            matching_datasets[full_path] = obj[()]
        else:
            if isinstance(obj, h5py.Group):
                matching_datasets.update(find_datasets(obj, full_path))

    return matching_datasets


def get_report_dataset_path(report_file_path: str, keyword: str = "report") -> ReportDataSetPath:
    with h5py.File(report_file_path, 'r') as f:
        report_ds = find_datasets(f)
        ds_paths = list(report_ds.keys())
        report_ds_path = ds_paths.pop() if len(ds_paths) < 2 else list(sorted(ds_paths))[0]   # TODO: make this better

        return ReportDataSetPath(report_ds_path)


def detect_encoding(file_path: PathLike[str]):
    with open(file_path, 'rb') as f:
        raw_data = f.read()
        result = chardet.detect(raw_data)
        return result


def handle_sbml_exception() -> str:
    tb_str = traceback.format_exc()
    error_message = pformat(f"time-course-simulation-error:\n{tb_str}")
    return error_message


def get_sbml_species_mapping(sbml_fp: str) -> dict | SbmlSpeciesMapping:
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

    return SbmlSpeciesMapping(zip(names, species_ids))


def fix_non_ascii_characters(file_path: PathLike[str], output_file: PathLike[str]):
    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()

    non_ascii_chars = set(re.findall(r'[^\x00-\x7F]', content))
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

