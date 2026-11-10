"""Split clinical rows by category and attach standardized variable names."""
import json
from importlib.resources import files
import pandas as pd


def read_table(path, sep=","):
    df = pd.read_csv(path, sep=sep, dtype=str, keep_default_na=False)
    if "person_id" not in df and "participant_id" in df:
        df = df.rename(columns={"participant_id": "person_id"})
    if "person_id" not in df or df.person_id.eq("").any():
        raise ValueError("A nonempty person_id is required")
    return df


def clinical_mappings():
    """Load the bundled category -> concept ID -> standardized name dictionary."""
    return json.loads(files("aireadi_preprocessing").joinpath("mappings.json").read_text())


def split_measurements(df):
    """Preserve every source field and row, including repeats and missing values."""
    if "measurement_concept_id" not in df:
        raise ValueError("measurement_concept_id is required")
    if "variable_name" in df:
        raise ValueError("Input already contains variable_name; refusing to overwrite")
    tables = {}
    seen = set()
    for category, names in clinical_mappings().items():
        if category == "observations":
            continue
        if seen.intersection(names):
            raise ValueError("A measurement code belongs to multiple categories")
        seen.update(names)
        part = df.loc[df.measurement_concept_id.isin(names)].copy()
        part["variable_name"] = part.measurement_concept_id.map(names)
        tables[category] = part.reset_index(drop=True)
    other = df.loc[~df.measurement_concept_id.isin(seen)].copy()
    if not other.empty:
        other["variable_name"] = ""
        tables["unmapped_measurements"] = other.reset_index(drop=True)
    return tables


def name_observations(df):
    if "observation_concept_id" not in df:
        raise ValueError("observation_concept_id is required")
    if "variable_name" in df:
        raise ValueError("Input already contains variable_name; refusing to overwrite")
    result = df.copy()
    result["variable_name"] = result.observation_concept_id.map(clinical_mappings()["observations"]).fillna("")
    return result
