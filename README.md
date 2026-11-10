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

Variable names are standardized because some source labels are truncated or difficult to find with a column search. The bundled [mappings.json](src/aireadi_preprocessing/mappings.json) maps each identifier to a readable name:

```json
{
  "3004410": "HbA1c (%)",
  "3004501": "Glucose (mg/dL)",
  "2005200344": "MoCA Trail Making Score"
}
```

| Identifier | Source label | Standardized column name |
| --- | --- | --- |
| 3004410 | `import_hba1c, Hemoglobin A1c/Hemoglobin.total in ` | HbA1c (%) |
| 3004501 | `import_glucose, Glucose [Mass/volume] in Serum or` | Glucose (mg/dL) |
| 2005200344 | `trails_visuospatial_executive` | MoCA Trail Making Score |

- Match `measurement_concept_id` to the bundled identifier; use its standardized name as the column header.
- Put `value_as_number` in that column, with one row per `person_id`. For repeated participant/code pairs, take the first nonmissing value in file order, matching the original extraction rule.
- Save the selected dictionary and observed source units as `clinical_mapping.csv`. Naming does not convert units or change numerical values. The original long table retains all source fields.
- The dictionary groups measurements by lab, vision, physical assessment, MoCA and monofilament. It also retains observation names for reference; observation output remains in long format.

For example, these fictional input rows:

| person_id | measurement_concept_id | measurement_source_value | unit_source_value | value_as_number |
| --- | --- | --- | --- | --- |
| 0007 | 3004410 | import_hba1c, Hemoglobin A1c/Hemoglobin.total in | % | 5.5 |
| 0012 | 3004410 | import_hba1c, Hemoglobin A1c/Hemoglobin.total in | % | 6.0 |

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

- In a custom mapping, `unit` is optional. When supplied, it must match the source exactly. No unit conversion is performed.
- Missing measurements stay empty. Participant IDs stay as text.
- Renaming preserves raw measurement values; it does not add calculated indices or combine measurements across eyes.
- Observation values remain in the long table.

## Notebook

[load_data.ipynb](load_data.ipynb) shows how to inspect the mapping, load clinical measurements and save a CSV.

```python
from aireadi_preprocessing import load_clinical

clinical = load_clinical("/path/to/ai-readi")
clinical.head()
```
