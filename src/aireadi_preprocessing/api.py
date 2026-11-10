"""Load AI-READI files into pandas tables."""
from pathlib import Path
from .tables import read_table, pivot_measurements, measurement_mapping


def load_clinical(dataset, mapping=None):
    """Return a participant-by-feature numeric measurement table.

    Default names come from the bundled concept-ID dictionary.
    An optional CSV/DataFrame can select or rename codes (concept_id,name;
    optional unit for exact unit checking). Repeated measurements use the
    first nonmissing value in source-file order.
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
