"""Load categorized long-format clinical tables."""
from pathlib import Path
from .tables import read_table, split_measurements, name_observations


def load_clinical(dataset):
    """Return a dict of category names to long-format pandas DataFrames.

    All source columns, repeated observations and missing values are preserved.
    variable_name is added using the bundled mapping. Unknown measurement codes
    go to unmapped_measurements. observation.csv is included when present.
    """
    clinical = Path(dataset) / "clinical_data"
    tables = split_measurements(read_table(clinical / "measurement.csv"))
    observations = clinical / "observation.csv"
    if observations.exists():
        tables["observations"] = name_observations(read_table(observations))
    return tables
