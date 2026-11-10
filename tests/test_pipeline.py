import json
from pathlib import Path
import subprocess
import sys
import pandas as pd
import pytest
from aireadi_preprocessing.cgm import CGMConfig, preprocess
from aireadi_preprocessing.tables import pivot_measurements
from aireadi_preprocessing.octa import aggregate


def record(time, value=100, unit="mg/dL"):
    return {"effective_time_frame": {"time_interval": {"start_date_time": str(time)}}, "blood_glucose": {"value": value, "unit": unit}}


def write(root, records, filename="a.json"):
    directory = root / "0007"
    directory.mkdir(parents=True, exist_ok=True)
    (directory / filename).write_text(json.dumps({"body": {"cgm": records}}))


def test_load_all_files_and_censoring(tmp_path):
    write(tmp_path, [record("2026-01-01T00:00:00Z"), record("2026-01-01T00:05:00Z", "High")])
    write(tmp_path, [record("2026-01-01T00:00:00Z"), record("2026-01-01T00:10:00Z", "Low")], "b.json")
    frame, audit = preprocess(tmp_path, CGMConfig())
    assert len(frame) == 3 and frame.id.unique().tolist() == ["0007"]
    assert frame.gl.isna().sum() == 2
    assert audit["files"] == 2 and audit["duplicates_removed"] == 1


def test_conflicting_duplicate_fails(tmp_path):
    write(tmp_path, [record("2026-01-01T00:00:00Z", 100), record("2026-01-01T00:00:00Z", 101)])
    with pytest.raises(ValueError, match="Conflicting"):
        preprocess(tmp_path, CGMConfig())


@pytest.mark.parametrize("time,value,unit", [("2026-01-01T00:00:00",100,"mg/dL"),("bad",100,"mg/dL"),("2026-01-01T00:00:00Z",100,"mmol/L"),("2026-01-01T00:00:00Z","oops","mg/dL")])
def test_invalid_records_fail(tmp_path, time, value, unit):
    write(tmp_path, [record(time,value,unit)])
    with pytest.raises(ValueError):
        preprocess(tmp_path, CGMConfig())


def test_exactly_seven_days_retained(tmp_path):
    times = pd.date_range("2026-01-01", periods=7*288, freq="5min", tz="UTC")
    write(tmp_path, [record(t) for t in times])
    frame, _ = preprocess(tmp_path, CGMConfig(coverage=.7,min_days=7,remove_partial_edges=True))
    assert len(frame) == 7*288


def test_coverage_rounds_up_and_duplicates_do_not_count(tmp_path):
    times = pd.date_range("2026-01-01", periods=201, freq="5min", tz="UTC")
    write(tmp_path, [record(t) for t in times] * 2)
    frame, _ = preprocess(tmp_path, CGMConfig(coverage=.7))
    assert frame.empty


def test_gap_and_initial_exclusions(tmp_path):
    write(tmp_path, [record("2026-01-01T00:00:00Z"),record("2026-01-01T13:00:00Z")])
    frame, audit = preprocess(tmp_path, CGMConfig(max_gap_hours=12))
    assert frame.empty and audit["gap_excluded_participants"] == 1
    frame, _ = preprocess(tmp_path, CGMConfig(initial_hours=12))
    assert len(frame) == 1


def test_dst_day_coverage(tmp_path):
    times = pd.date_range("2026-03-08T05:00:00Z", periods=23*12, freq="5min")
    write(tmp_path, [record(t) for t in times])
    frame, _ = preprocess(tmp_path, CGMConfig(coverage=1,calendar_timezone="America/New_York",remove_partial_edges=True))
    assert len(frame) == 276


def test_empty_and_fully_excluded(tmp_path):
    write(tmp_path, [])
    frame, _ = preprocess(tmp_path, CGMConfig())
    assert frame.empty
    write(tmp_path, [record("2026-01-01T00:00:00Z")])
    frame, _ = preprocess(tmp_path, CGMConfig(initial_hours=12))
    assert frame.empty


def measurement():
    return pd.DataFrame({"person_id":["0007"],"measurement_concept_id":["123"],"value_as_number":["2.5"],"unit_source_value":["mg/dL"]})


def test_pivot_missing_concept_and_unit_safety():
    mapping = pd.DataFrame({"concept_id":["123","456"],"name":["known","missing"],"unit":["mg/dL","mg/dL"]})
    frame = pivot_measurements(measurement(),mapping)
    assert frame.person_id.iloc[0] == "0007" and pd.isna(frame.missing.iloc[0])
    bad = measurement(); bad.loc[0,"unit_source_value"] = "mmol/L"
    with pytest.raises(ValueError,match="unit"):
        pivot_measurements(bad,mapping)
    with pytest.raises(ValueError,match="Repeated"):
        pivot_measurements(pd.concat([measurement()]*2),mapping)


def test_octa_requires_both_eyes(tmp_path):
    for side, value in [("l",2),("r",4)]:
        pd.DataFrame({"person_id":["0007"],"include":["yes"],"vld":[value]}).to_csv(tmp_path/f"dvc_{side}.csv",index=False)
    frame = aggregate(tmp_path,["vld"])
    assert frame.person_id.iloc[0] == "0007" and frame.vld.iloc[0] == 3


def test_cli_full_run_and_no_overwrite(tmp_path):
    root = tmp_path/"source"
    write(root/"wearable_blood_glucose/continuous_glucose_monitoring/dexcom_g6",[record("2026-01-01T00:00:00Z")])
    clinical = root/"clinical_data"; clinical.mkdir()
    measurement().to_csv(clinical/"measurement.csv",index=False)
    pd.DataFrame({"person_id":["0007"],"value_as_string":["category"]}).to_csv(clinical/"observation.csv",index=False)
    output = tmp_path/"result"
    command = [sys.executable,"-m","aireadi_preprocessing.cli","--dataset-root",str(root),"--release","3.0.0","--steps","cgm","clinical","--output",str(output)]
    subprocess.run(command,check=True)
    report = json.loads((output/"run.json").read_text())
    assert report["status"] == "complete" and len(report["input_sha256"]) == 3
    assert subprocess.run(command,capture_output=True).returncode != 0
    command[-1] = str(root/"output")
    assert subprocess.run(command,capture_output=True).returncode != 0
