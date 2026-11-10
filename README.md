# AI-READI preprocessing

Turn AI-READI files into CSV tables you can use with pandas, R or a statistical model. Clinical measurements become one row per participant with named columns. CGM JSON files become one table of timestamped readings.

## Install and run

Requires Python 3.10 or later.

```sh
git clone https://github.com/billchen0/aireadi-preprocessing.git
cd aireadi-preprocessing
pip install .
aireadi-preprocess /path/to/ai-readi /path/to/tables
```

The command reads `clinical_data/measurement.csv` and `observation.csv`. It saves `measurement_wide.csv`, the code-to-column dictionary `clinical_mapping.csv`, and copies of the long tables. Use a new output folder outside the dataset and this repository.

For CGM:

```sh
aireadi-preprocess /path/to/ai-readi /path/to/cgm-tables --steps cgm
```

This reads the Dexcom JSON files and writes `cgm.csv` with `id`, `time`, `gl` and `glucose_status`. Times use UTC. `High` and `Low` stay marked as censored readings, with missing numeric values. Both commands save a `run.json` record of the conversion.

## How clinical codes become columns

AI-READI stores clinical measurements in OMOP format: each row has a participant ID, a measurement code and its value. The code identifies the measurement. For example, `3004410` identifies HbA1c.

AI-READI publishes its code definitions in the [OMOP mapping table](https://docs.aireadi.org/docs/3/dataset/clinical-data/OMOP-Clinical-Data-Structure/OMOP-Mapping-Table). The public documentation uses [`mappings.json`](https://github.com/AI-READI/ai-readi-docs/blob/main/docs/static/json/mappings.json); the [lab dictionary](https://github.com/AI-READI/ai-readi-docs/blob/main/docs/static/json/clinicalLabData.json) also lists names and units. These are the sources for checking which code represents a variable.

For conversion, the package reads the dictionary already carried in your release's `measurement.csv`: `measurement_concept_id` supplies the code, `measurement_source_value` supplies the column name, and `unit_source_value` supplies the unit. It matches rows by code and places `value_as_number` under the corresponding column, using `person_id` as the row key. Only concepts with numeric measurements are selected automatically; the long tables retain categorical and other source fields.

You can select measurements or rename columns with a CSV containing `concept_id,name,unit`. For example:

```csv
concept_id,name,unit
3004410,HbA1c (%),%
```

Pass it with `--mapping clinical_mapping.csv`. Units must match the source. Missing values stay empty. Repeated participant/code rows or conflicting code definitions stop the conversion so you can decide how to handle them.

## Use it in a notebook

[load_data.ipynb](load_data.ipynb) walks through loading clinical data, inspecting the mapping, selecting columns and saving a CSV. It also shows how to load CGM.

```python
from aireadi_preprocessing import load_clinical

clinical = load_clinical("/path/to/ai-readi")
clinical.head()
```

The package targets AI-READI v3. Full-release validation is still pending.
