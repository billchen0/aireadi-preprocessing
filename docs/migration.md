# Extraction and migration audit

Reviewed November 9, 2026 against the linked v3 documentation. No participant data was read for this audit.

| Previous behavior | Standalone behavior / reason |
| --- | --- |
| Absolute Linux paths and edit-to-configure scripts | CLI paths, explicit steps, new output directory |
| First CGM JSON only | All participant JSON files, sorted |
| Silent schema skips and invalid-time dropping | Explicit failure |
| Duplicate resolution after coverage, keep last | Collapse exact duplicates before coverage; conflicting values fail |
| `int(288 * .7)` permits 201 readings | Ceiling requires 202 unique usable five-minute slots |
| `> min_full_days` requires eight when set to seven | `>= min_days` requires seven |
| Implicit timezone assumptions | Offset-aware timestamps, UTC normalization, explicit calendar timezone; DST day length accounted for |
| Automatic 401/39 substitution | Censoring preserved; boundary substitution opt-in |
| Global 12-hour gap exclusion | Opt-in, still after day filtering; removed days may create gaps |
| Hard-coded local concept IDs | Preserve long OMOP tables; require reviewed mapping for numeric pivot |
| First value silently chosen by pivot | Reject repeated participant/concept rows |
| Missing A1c could default to normal | No automatic diagnostic labels |
| Race first-match and ethnicity inferred from free text | Excluded from automatic preprocessing |
| Medication text regex classes | Excluded from default package; unvalidated research heuristics require a separately specified extension |
| OCTA substring matches and first duplicate | Explicit feature names; duplicate IDs fail |
| OCTA inner join requires SVC and DVC although only DVC means used | DVC aggregation requires the two DVC eyes only |

## v3 compatibility

The official changelog describes changed standard and local OMOP concepts, merged mapping metadata, and manifest `person_id` renaming. `legacy-concepts.json` is a code-authored historical reference extracted from the old mappings, with **no participant records**; it is deliberately not an active mapping. Its names/units may be outdated. Do not use it as proof that any particular v3 variable is present or mapped correctly.

The generic table path avoids silently reusing those mappings and preserves all clinical columns. Before claiming domain-specific compatibility, reconcile a release-specific concept/unit selection against the official release's mapping metadata, inspect unmapped counts locally, and review operator/categorical fields before numeric pivoting. The documentation's mapping-table page currently exposes no mapping rows in the fetched text, so this reconciliation remains outstanding.

## Historical feature helpers

`research_features.process_lab_tests` computes TG/HDL, TyG and UACR only when its exact expected named columns exist. It preserves old naming, including mg/mL urine labels that conflict with the v2 changelog's mg/dL update. Supply a deliberately normalized table with verified units or do not use it. TyG requires reviewing fasting status; denominator zero and nonpositive log inputs are not automatically repaired.

`process_vision` averages available OD/OS values when one or both eyes are present. Review whether averaging each measure is scientifically appropriate. `process_moca` reproduces the previous custom domain sums, mean log times and total-score/mean-time ratio. These are historical study features, not validated universal cognitive scores; required columns must exist and missing subtests propagate according to the original formulas. These helpers are opt-in and never called by the CLI.

The historical CGM profile intentionally changes cohort accounting by fixing minimum-day and coverage arithmetic and counting duplicates before QC. It is not a byte-identical manuscript reproduction profile. Compare participant retention locally before substituting it into existing analyses.

## Validation still needed before a stable release

- Execute against an authorized v3 installation locally; review aggregate retention and schema coverage without publishing participant outputs.
- Reconcile clinical domain concept/unit mappings for each supported release.
- Validate R/iglu execution and pin its environment; compare metric and exclusion outputs.
- Public development preview: `billchen0/aireadi-preprocessing`, MIT, with a fresh source-only history. Full-release and R validation above remain prerequisites for a stable release.
