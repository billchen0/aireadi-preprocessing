# AI-READI preprocessing

Split AI-READI clinical OMOP tables into categorized, long-format CSVs. Each row is a measurement or observation, with its source fields preserved and a readable `variable_name` added.

## Run

Requires Python 3.10 or later.

```sh
git clone https://github.com/billchen0/aireadi-preprocessing.git
cd aireadi-preprocessing
pip install .
aireadi-preprocess /path/to/ai-readi
```

This creates `processed/` beside the dataset. To choose its location:

```sh
aireadi-preprocess /path/to/ai-readi /path/to/processed
```

Use a new folder outside the source dataset.

| Category | AI-READI input | Long-format output |
| --- | --- | --- |
| Laboratory tests | `clinical_data/measurement.csv` | `processed/lab_test.csv` |
| Vision | `clinical_data/measurement.csv` | `processed/vision.csv` |
| Physical assessment | `clinical_data/measurement.csv` | `processed/physical.csv` |
| MoCA | `clinical_data/measurement.csv` | `processed/moca.csv` |
| Monofilament | `clinical_data/measurement.csv` | `processed/monofilament.csv` |
| Observations, when present | `clinical_data/observation.csv` | `processed/observations.csv` |

## How the mapping works

The [official mapping JSON](https://github.com/AI-READI/ai-readi-docs/blob/main/docs/static/json/mappings.json) defines `TARGET_CONCEPT_ID` and `TARGET_CONCEPT_NAME`. Match `TARGET_CONCEPT_ID` to the data’s `measurement_concept_id`; our bundled mapping supplies the standardized name and category.

Variable names are standardized because some source labels are truncated or difficult to find with a column search. The bundled [mappings.json](src/aireadi_preprocessing/mappings.json) maps each identifier to a readable name:

```json
{
  "3004410": "HbA1c (%)",
  "3004501": "Glucose (mg/dL)",
  "2005200344": "MoCA Trail Making Score"
}
```

| Identifier | Source label | Standardized variable name |
| --- | --- | --- |
| 3004410 | `import_hba1c, Hemoglobin A1c/Hemoglobin.total in ` | HbA1c (%) |
| 3004501 | `import_glucose, Glucose [Mass/volume] in Serum or` | Glucose (mg/dL) |
| 2005200344 | `trails_visuospatial_executive` | MoCA Trail Making Score |

- The bundled mapping groups identifiers by category. `measurement_concept_id` determines the output CSV and its standardized `variable_name`.
- Original values, units, source labels, dates and other fields are copied unchanged. Repeated measurements and missing values remain as separate rows; nothing is pivoted or averaged.
- Unknown measurement codes go to `unmapped_measurements.csv`. Unmapped observation names remain empty. Rows are not silently discarded.

For example, `lab_test.csv` contains rows like these (fictional values; only selected columns shown):

| person_id | measurement_concept_id | variable_name | value_as_number | unit_source_value |
| --- | --- | --- | --- | --- |
| 0007 | 3004410 | HbA1c (%) | 5.5 | % |
| 0007 | 3004501 | Glucose (mg/dL) | 95 | mg/dL |
| 0012 | 3004410 | HbA1c (%) | 6.0 | % |

A `run.json` file records output row counts and hashes. All five measurement CSVs are created, even when a category has no rows.

## Notebook

[load_data.ipynb](load_data.ipynb) shows how to load, inspect and save the category tables:

```python
from aireadi_preprocessing import load_clinical

tables = load_clinical("/path/to/ai-readi")
labs = tables["lab_test"]
labs.head()
```
