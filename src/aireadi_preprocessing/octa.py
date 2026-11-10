"""Aggregate existing OCTA feature exports; does not segment retinal images."""
import re
from pathlib import Path
import pandas as pd


def aggregate(directory: Path, features: list[str]):
    """Require explicit feature names and both DVC eyes; retain IDs as strings."""
    frames = []
    for side in ["l", "r"]:
        paths = sorted(directory.glob(f"*dvc_{side}*.csv"))
        if len(paths) != 1:
            raise ValueError("Exactly one CSV per DVC eye is required")
        df = pd.read_csv(paths[0], dtype={"person_id": str})
        if not {"person_id", "include", *features}.issubset(df.columns):
            raise ValueError("OCTA file lacks required columns")
        df = df[df.include.astype(str).str.strip().str.lower().eq("yes")].copy()
        if df.person_id.isna().any() or df.person_id.duplicated().any():
            raise ValueError("OCTA IDs must be nonempty and unique")
        for feature in features:
            df[feature] = pd.to_numeric(df[feature], errors="raise")
        frames.append(df[["person_id", *features]])
    both = frames[0].merge(frames[1], on="person_id", suffixes=("_l", "_r"), validate="one_to_one")
    out = both[["person_id"]].copy()
    for feature in features:
        out[feature] = (both[f"{feature}_l"] + both[f"{feature}_r"]) / 2
    return out
