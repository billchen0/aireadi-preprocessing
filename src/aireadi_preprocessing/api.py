"""Load AI-READI files into pandas tables."""
from pathlib import Path
from .tables import read_table, pivot_measurements, measurement_mapping


def load_clinical(dataset, mapping=None):
    """Return a participant-by-feature numeric measurement table.

    Without a mapping, use code/label/unit pairs embedded in measurement.csv.
    Supply a DataFrame or CSV path with concept_id,name,unit to select features.
    Repeated participant/concept measurements require an explicit aggregation
    upstream; this function does not choose an observation silently.
    """
    import pandas as pd
    table = read_table(Path(dataset) / "clinical_data" / "measurement.csv")
    if mapping is None:
        mapping = measurement_mapping(table)
    elif isinstance(mapping, (str, Path)):
        mapping = pd.read_csv(mapping, dtype=str, keep_default_na=False)
    else:
        mapping = mapping.copy().astype(str)
    return pivot_measurements(table, mapping)
