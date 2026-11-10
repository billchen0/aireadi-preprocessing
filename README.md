# AI-READI preprocessing

Convert AI-READI's source formats into tabular data for everyday data science workflows. This toolkit turns nested CGM JSON into a tidy CSV time series and prepares clinical OMOP tables and manifests for use with pandas, R, statistical models and machine learning. With an explicitly reviewed concept mapping, it also creates a wide clinical measurement table with one row per participant and one column per selected feature.

Extracted from Bill Chen's AI-READI analysis pipeline, this is an independent community tool.

**Status:** development preview. Documentation aligned with the public v3.0.0 specification on November 9, 2026; real-release validation is still required. No claim of v4 compatibility. See [migration notes](docs/migration.md) before reproducing historical analyses.

## From source formats to analysis tables

| AI-READI input | Tabular output | Typical use |
| --- | --- | --- |
| Nested CGM JSON, organized by participant | `cgm.csv`: one reading per participant and timestamp | Time-series analysis, plots and CGM features |
| OMOP `measurement.csv` and `observation.csv` | Preserved long CSV tables | Filtering, joins and inspection of values, units and concepts |
| Measurements plus a reviewed concept/unit mapping | `measurement_wide.csv`: one row per participant | Feature matrices for statistics and machine learning |
| Participant and ECG manifests | CSV tables with a consistent `person_id` key | Cohort metadata and joins |

The primary goal is format conversion and practical access. CGM quality filters and historical study features are optional and documented separately. This preview covers the inputs above; other AI-READI modalities still need dedicated adapters.

For example, after conversion:

```python
import pandas as pd

cgm = pd.read_csv("/path/to/local-runs/cgm-001/cgm.csv", dtype={"id": str}, parse_dates=["time"])
features = pd.read_csv("/path/to/local-runs/tables-001/measurement_wide.csv", dtype={"person_id": str})
# `features` is produced when --measurement-mapping is supplied.
```

## Install

Requires Python 3.10 or later. Clone the separate repository and install it:

```sh
git clone https://github.com/billchen0/aireadi-preprocessing.git
cd aireadi-preprocessing
python -m venv .venv
source .venv/bin/activate
python -m pip install .
aireadi-preprocess --help
```

## Prepare CGM

Acquire the dataset independently through AI-READI under its applicable terms. Run locally on equipment authorized for your data access. Choose a **new output directory outside both the source dataset and this repository**:

```sh
aireadi-preprocess --dataset-root /path/to/aireadi-v3 \
  --release 3.0.0 --steps cgm --output /path/to/local-runs/cgm-001
```

Expected input: `wearable_blood_glucose/continuous_glucose_monitoring/dexcom_g6/<person_id>/*.json`, with `body.cgm` observations, offset-aware timestamps and `mg/dL` glucose. All JSON files are loaded. Participant folder names remain strings, preserving leading zeros. Unexpected schemas, invalid values, unknown units and conflicting duplicate readings fail explicitly.

Defaults normalize timestamps to UTC, collapse identical duplicates and retain days with at least one numeric reading, without initial-wear removal or a coverage/gap exclusion. `High`/`Low` become missing numeric values with their censoring status preserved. There is no interpolation, resampling, imputation or clinical classification.

To apply study-style exclusions:

```sh
aireadi-preprocess --dataset-root /path/to/aireadi-v3 \
  --release 3.0.0 --steps cgm \
  --cgm-config examples/study-cgm.json --output /path/to/local-runs/cgm-002
```

This example removes the first 12 hours, removes incomplete edge days, requires at least 70% coverage per day and at least seven qualifying days, maps censored readings to 401/39 mg/dL, and excludes participants with gaps over 12 hours after day selection. These are **research choices**, not AI-READI requirements. Calendar days use UTC unless you configure an IANA timezone. Do not assume abbreviated header timezones identify a unique civil timezone.

`cgm.csv` contains `id,time,gl,glucose_status`. `run.json` records configuration, release, runtime, input fingerprints, output hashes, counts and completion status. Both files belong in your local research environment. A failed run has `status: failed`; discard its partial products and rerun into a new directory.

## Prepare clinical tables and manifests

```sh
aireadi-preprocess --dataset-root /path/to/aireadi-v3 \
  --release 3.0.0 --steps clinical participants ecg \
  --output /path/to/local-runs/tables-001
```

This reads `clinical_data/measurement.csv`, `clinical_data/observation.csv`, `participants.tsv`, and `cardiac_ecg/manifest.tsv`. Only requested steps run; missing requested inputs fail. Outputs preserve long-table values, categorical encodings, units, dates and source fields. `participant_id` is normalized to `person_id` if necessary. Manifest IDs must be unique. No restricted demographics or medication files are read automatically.

For a wide numeric measurement table, supply `--measurement-mapping /path/to/reviewed-mapping.csv`. It must contain `concept_id,name,unit`; concept IDs and output names must each be unique. Review these against the mapping supplied with your release. Units must match exactly; repeated participant/concept rows fail rather than silently selecting or averaging. Unavailable mapped concepts become missing columns for all participants. Long tables retain the full semantics, including operators and categorical values; a numeric wide table does not capture all those semantics.

## Optional research features

Python helpers in `research_features` preserve the prior lab, vision and MoCA computations for explicit use after reviewing names, units and assumptions. `octa.aggregate(directory, features)` averages explicitly named, precomputed DVC features across two included eyes; it does not process OCTA images. See [migration notes](docs/migration.md) for differences and limitations.

Optional R/iglu metrics, installed separately:

```sh
Rscript -e 'install.packages("iglu", repos="https://cloud.r-project.org")'
Rscript scripts/cgm_metrics.R /path/to/cgm.csv /path/to/cgm_metrics.csv
```

The script records `sessionInfo()` and reports skipped participants. It treats iglu warnings as participant failures, following the historical script. Review exclusions before analysis. The R path has not yet been runtime validated in this extraction; pin your validated iglu version for reproducibility.

## Development

```sh
python -m pip install '.[test]'
python -m pytest
```

A GitHub Actions template is included at `docs/github-actions-tests.yml`. To enable CI, place it at `.github/workflows/tests.yml` using an account or token with workflow permissions.

Tests generate fictional records in temporary directories; they do not read AI-READI data. Contributions should include a synthetic regression case and document changes affecting cohort membership. Never attach real participant records or local result files to issues or pull requests.

## Scope and data terms

The toolkit covers the preprocessing represented by the original scripts. It does not provide raw retinal-image segmentation, ECG waveform processing, environment processing, Garmin processing, analysis notebooks or models. Clinical domain mappings from the previous study are reference material, not verified v3 mappings.

Source code is available under the [MIT license](LICENSE). Dataset access and redistribution are governed separately by [AI-READI's data-use terms](https://docs.aireadi.org/docs/3/preliminary/license); a software license does not grant rights to distribute data or derivative tables. No dataset, participant-derived fixtures, credentials, downloaded assets or analysis history is included here.

## Documentation and attribution

- [AI-READI v3 documentation](https://docs.aireadi.org/docs/3/about)
- [Release changelog](https://docs.aireadi.org/docs/3/changelog)
- [CGM format](https://docs.aireadi.org/docs/3/dataset/wearable-glucose-monitor/)
- [Clinical OMOP structure](https://docs.aireadi.org/docs/3/dataset/clinical-data/OMOP-Clinical-Data-Structure/)
- [Dataset citation instructions](https://docs.aireadi.org/docs/3/citation)

Cite the exact dataset release used and relevant methods/software (including iglu when applicable). This package derives from the code in `billchen0/ai-readi-analysis`, `data_preperation/`; it has separate source-only history in this repository.
