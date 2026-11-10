# AI-READI preprocessing

Extracted from Bill Chen's AI-READI analysis pipeline. This package converts clinical OMOP tables into CSV files with one row per participant and named measurement columns.

| Modality | AI-READI format | Tabular output format |
| --- | --- | --- |
| Clinical measurements | OMOP `measurement.csv`: one measurement per row | `measurement_wide.csv`: one participant per row, one measurement per column |
| Clinical observations | OMOP `observation.csv` | `observation_long.csv`: original fields preserved |

## Run

Requires Python 3.10 or later.

```sh
git clone https://github.com/billchen0/aireadi-preprocessing.git
cd aireadi-preprocessing
pip install .
aireadi-preprocess /path/to/ai-readi /path/to/tables
```

Choose a new output folder outside the dataset and repository. The command also saves `clinical_mapping.csv`, the original long measurement table, and a conversion record in `run.json`.

## How the mapping works

AI-READI's [OMOP mapping table](https://docs.aireadi.org/docs/3/dataset/clinical-data/OMOP-Clinical-Data-Structure/OMOP-Mapping-Table) defines the codes. Its [source JSON](https://github.com/AI-READI/ai-readi-docs/blob/main/docs/static/json/mappings.json) and [lab dictionary](https://github.com/AI-READI/ai-readi-docs/blob/main/docs/static/json/clinicalLabData.json) let you check a measurement:

- Match the documentation's `TARGET_CONCEPT_ID` to the data's `measurement_concept_id`.
- Read `TARGET_CONCEPT_NAME` for the clinical definition. In the lab dictionary, `Name` is the shorter label and `Units` gives the expected unit.
- The package builds its default mapping from your actual file: `measurement_concept_id` → `measurement_source_value` (column label), with `unit_source_value` retained in `clinical_mapping.csv`. It does not match measurements by similar names or download a dictionary at runtime.
- Pivot `value_as_number` into the named columns, using `person_id` as the row key. Only numeric measurements are selected automatically. Observation values remain in the long table.

For example, the documentation identifies `3004410` as HbA1c. These fictional input rows:

```csv
person_id,measurement_concept_id,measurement_source_value,unit_source_value,value_as_number
0007,3004410,HbA1c (%),%,5.5
0012,3004410,HbA1c (%),%,6.0
```

become:

```csv
person_id,HbA1c (%)
0007,5.5
0012,6.0
```

To select measurements or change their labels, supply a mapping CSV:

```csv
concept_id,name,unit
3004410,HbA1c (%),%
```

```sh
aireadi-preprocess /path/to/ai-readi /path/to/tables --mapping my_mapping.csv
```

- Units must match the source; the package does not convert them.
- Missing measurements stay empty. Participant IDs stay as text.
- Repeated participant/code pairs or conflicting code definitions stop the conversion so you can choose a visit, selection or aggregation.

## Notebook

[load_data.ipynb](load_data.ipynb) shows how to inspect the mapping, load clinical measurements and save a CSV.

```python
from aireadi_preprocessing import load_clinical

clinical = load_clinical("/path/to/ai-readi")
clinical.head()
```
