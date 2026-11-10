# AI-READI preprocessing

This package converts clinical OMOP tables into CSV files with one row per participant and named measurement columns.

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

The [AI-READI mapping JSON](https://github.com/AI-READI/ai-readi-docs/blob/main/docs/static/json/mappings.json) defines the identifiers. This is an excerpt of its HbA1c entry:

```json
{
  "FIELD_ID": "import_hba1c",
  "SRC_CODE": "4548-4",
  "TARGET_CONCEPT_ID": "3004410",
  "TARGET_CONCEPT_NAME": "Hemoglobin A1c/Hemoglobin.total in Blood",
  "TARGET_DOMAIN_ID": "Measurement"
}
```

- `FIELD_ID` identifies the original collection field.
- `SRC_CODE` is the source terminology code, here the LOINC code for HbA1c.
- `TARGET_CONCEPT_ID` is the OMOP identifier matched to `measurement_concept_id` in the data. For this measurement, use `3004410`, not `4548-4`.
- `TARGET_CONCEPT_NAME` gives the clinical meaning. The [lab dictionary](https://github.com/AI-READI/ai-readi-docs/blob/main/docs/static/json/clinicalLabData.json) also gives the shorter `Name` (HbA1c) and `Units` (%).

The package extracts the working mapping from your downloaded `measurement.csv`:

| Input field | Extracted mapping field | Role |
| --- | --- | --- |
| `measurement_concept_id` | `concept_id` | Identifier used to match rows |
| `measurement_source_value` | `name` | Output column label, such as `HbA1c (%)` |
| `unit_source_value` | `unit` | Unit checked before conversion |

1. Select rows with a numeric value and extract the distinct code/label/unit combinations.
2. Save that dictionary as `clinical_mapping.csv`. The documentation JSON explains the codes; it is not downloaded or parsed during conversion.
3. Match measurement rows to the dictionary by code, then pivot `value_as_number` into columns using `person_id` as the row key.

For example, these fictional input rows:

| person_id | measurement_concept_id | measurement_source_value | unit_source_value | value_as_number |
| --- | --- | --- | --- | --- |
| 0007 | 3004410 | HbA1c (%) | % | 5.5 |
| 0012 | 3004410 | HbA1c (%) | % | 6.0 |

produce:

| person_id | HbA1c (%) |
| --- | --- |
| 0007 | 5.5 |
| 0012 | 6.0 |

To select measurements or change their labels, create a mapping CSV with these columns:

| concept_id | name | unit |
| --- | --- | --- |
| 3004410 | HbA1c (%) | % |

```sh
aireadi-preprocess /path/to/ai-readi /path/to/tables --mapping my_mapping.csv
```

- Units must match the source; the package does not convert them.
- Missing measurements stay empty. Participant IDs stay as text.
- Repeated participant/code pairs or conflicting definitions stop the conversion so you can choose a visit, selection or aggregation.
- Observation values remain in the long table.

## Notebook

[load_data.ipynb](load_data.ipynb) shows how to inspect the mapping, load clinical measurements and save a CSV.

```python
from aireadi_preprocessing import load_clinical

clinical = load_clinical("/path/to/ai-readi")
clinical.head()
```
