"""Load documented Open mHealth CGM JSON and apply explicit research QC."""
from __future__ import annotations
from dataclasses import dataclass, asdict
import json
import math
from pathlib import Path
import pandas as pd


@dataclass(frozen=True)
class CGMConfig:
    initial_hours: float = 0
    coverage: float = 0
    min_days: int = 1
    remove_partial_edges: bool = False
    max_gap_hours: float | None = None
    calendar_timezone: str = "UTC"
    censored: str = "missing"

    def __post_init__(self):
        if not math.isfinite(self.initial_hours) or self.initial_hours < 0:
            raise ValueError("initial_hours must be finite and nonnegative")
        if not 0 <= self.coverage <= 1 or self.min_days < 1:
            raise ValueError("coverage must be 0..1 and min_days >= 1")
        if self.max_gap_hours is not None and (not math.isfinite(self.max_gap_hours) or self.max_gap_hours <= 0):
            raise ValueError("max_gap_hours must be finite and positive")
        if self.censored not in {"missing", "boundary"}:
            raise ValueError("censored must be missing or boundary")
        pd.Timestamp("2000-01-01", tz=self.calendar_timezone)


def load_cgm(root: Path):
    rows = []
    files = sorted(root.glob("*/*.json"))
    if not files:
        raise ValueError("No participant JSON files found")
    for path in files:
        payload = json.loads(path.read_text())
        records = payload.get("body", {}).get("cgm")
        if not isinstance(records, list):
            raise ValueError("Expected body.cgm list")
        for record in records:
            try:
                stamp = pd.Timestamp(record["effective_time_frame"]["time_interval"]["start_date_time"])
                if pd.isna(stamp) or stamp.tzinfo is None:
                    raise ValueError("CGM timestamps must include UTC offset")
                glucose = record["blood_glucose"]
                if glucose["unit"] != "mg/dL":
                    raise ValueError("Only mg/dL CGM is supported")
                raw = glucose["value"]
                flag = str(raw).strip().lower()
                if flag in {"high", "low"}:
                    value = float("nan")
                else:
                    value = float(raw)
                    if not math.isfinite(value) or value <= 0:
                        raise ValueError("Invalid CGM value")
                    flag = "numeric"
                rows.append((path.parent.name, stamp.tz_convert("UTC"), value, flag))
            except (KeyError, TypeError, ValueError) as exc:
                raise ValueError("Invalid CGM record; inspect input locally") from exc
    return pd.DataFrame(rows, columns=["id", "time", "gl", "glucose_status"]), len(files)


def preprocess(root: Path, config: CGMConfig):
    df, nfiles = load_cgm(root)
    audit = {"files": nfiles, "input_rows": len(df), "config": asdict(config)}
    # Identical duplicates collapse; disagreeing values require an explicit upstream decision.
    df = df.drop_duplicates(["id", "time", "gl", "glucose_status"])
    if df.duplicated(["id", "time"]).any():
        raise ValueError("Conflicting CGM readings at the same participant/time")
    audit["duplicates_removed"] = audit["input_rows"] - len(df)
    df = df.sort_values(["id", "time"]).reset_index(drop=True)
    audit["censored_rows"] = int(df.glucose_status.isin(["high", "low"]).sum())
    if config.censored == "boundary":
        df.loc[df.glucose_status == "high", "gl"] = 401.0
        df.loc[df.glucose_status == "low", "gl"] = 39.0
    if df.empty:
        audit["output_rows"] = 0
        audit["output_participants"] = 0
        return df, audit
    first = df.groupby("id").time.transform("min")
    df = df[df.time >= first + pd.Timedelta(hours=config.initial_hours)].copy()
    audit["rows_after_initial_wear"] = len(df)
    df["day"] = df.time.dt.tz_convert(config.calendar_timezone).dt.date
    # Unique five-minute slots prevent irregular oversampling inflating coverage.
    df["slot"] = df.time.dt.floor("5min")
    usable = df[df.gl.notna()]
    counts = usable.groupby(["id", "day"]).slot.nunique()
    all_days = df.groupby(["id", "day"]).size().index
    counts = counts.reindex(all_days, fill_value=0)
    valid = set()
    for pid, group in counts.groupby(level=0):
        days = list(group.index.get_level_values("day"))
        for (_, day), count in group.items():
            # UTC day lengths are fixed; civil days may span DST transitions.
            start = pd.Timestamp(day).tz_localize(config.calendar_timezone)
            end = (pd.Timestamp(day) + pd.Timedelta(days=1)).tz_localize(config.calendar_timezone)
            expected = int((end.tz_convert("UTC") - start.tz_convert("UTC")).total_seconds() / 300)
            required = math.ceil(expected * config.coverage)
            edge = config.remove_partial_edges and day in {days[0], days[-1]}
            if count >= max(1, required) and (not edge or count >= expected):
                valid.add((pid, day))
    df = df.loc[pd.Series([key in valid for key in zip(df.id, df.day)], index=df.index, dtype=bool)]
    audit["rows_after_day_coverage"] = len(df)
    days_per_id = df.groupby("id").day.nunique()
    df = df[df.id.isin(days_per_id[days_per_id >= config.min_days].index)]
    audit["rows_after_min_days"] = len(df)
    # Assess gaps on usable observations after day selection, matching legacy ordering.
    excluded = set()
    if config.max_gap_hours is not None:
        usable = df[df.gl.notna()]
        gaps = usable.groupby("id").time.diff()
        excluded = set(usable.loc[gaps > pd.Timedelta(hours=config.max_gap_hours), "id"])
        df = df[~df.id.isin(excluded)]
    audit.update(gap_excluded_participants=len(excluded), output_rows=len(df), output_participants=int(df.id.nunique()))
    return df.drop(columns=["day", "slot"]).reset_index(drop=True), audit
