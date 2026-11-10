"""Historical study features: opt-in, requiring reviewed names and units.

Not clinical diagnoses or validated general-purpose cognitive scores.
Verify input units before use; these helpers preserve historical study formulas.
Urine features expect mg/mL; normalize verified units first. Custom MoCA
aggregates are study features, not validated universal cognitive scores.
"""
import pandas as pd
import numpy as np

def process_vision(pivot_df):
    df = pivot_df.copy()

    od_cols = [c for c in df.columns if c.startswith("OD ")]
    os_cols = [c for c in df.columns if c.startswith("OS ")]

    os_map = {c.replace("OS ", ""): c for c in os_cols}

    agg_df = pd.DataFrame()
    agg_df["person_id"] = df["person_id"]

    for od_col in od_cols:
        base_name = od_col.replace("OD ", "")
        if base_name in os_map:
            os_col = os_map[base_name]
            # Mean across eyes (no requirement both present)
            agg_df[base_name] = df[[od_col, os_col]].mean(axis=1, skipna=True)

    return agg_df

def process_moca(pivot_df):
    df = pivot_df.copy()
    agg_df = pd.DataFrame()
    agg_df["person_id"] = df["person_id"]

    # 1. Global Cognition
    agg_df["moca_total"] = df["MoCA Total Score"]

    # 2. Visuospatial / Executive
    agg_df["moca_visuospatial_executive"] = (
        df["MoCA Trail Making Score"] +
        df["MoCA Cube Score"] +
        df["MoCA Clock Score"]
    )

    # 3. Attention / Working Memory
    agg_df["moca_attention"] = (
        df["MoCA Digit Span Score"] +
        df["MoCA Letter Tapping Score"] +
        df["MoCA Serial 7 Score"]
    )

    # 4. Language
    agg_df["moca_language"] = (
        df["MoCA Naming Score"] +
        df["MoCA Sentence Repetition Score"] +
        df["MoCA Fluency Score"]
    )

    # 5. Memory
    agg_df["moca_memory"] = df["MoCA Combined MIS Score"]

    # 6. Orientation
    agg_df["moca_orientation"] = df["MoCA Orientation Score"]

    # 7. Processing Speed
    speed_cols = [
        "MoCA Trail Making Time (sec)",
        "MoCA Cube Time (sec)",
        "MoCA Serial 7 Time (sec)",
        "MoCA Abstraction Time (sec)",
        "MoCA Orientation Time (sec)"
    ]

    speed_raw = df[speed_cols]
    speed_raw = speed_raw.where(speed_raw > 0)

    speed_log = np.log(speed_raw)

    agg_df["moca_processing_speed"] = speed_log.mean(axis=1)

    # 8. Efficiency (points per second)
    mean_time = speed_raw.mean(axis=1)
    agg_df["moca_efficiency"] = df["MoCA Total Score"] / mean_time

    return agg_df

def process_lab_tests(pivot_df):
    df = pivot_df.copy()
    agg_df = df.copy()

    # 1. TG/HDL Ratio
    if {"Triglycerides (mg/dL)", "HDL Cholesterol (mg/dL)"}.issubset(agg_df.columns):
        agg_df["TG/HDL"] = (
            agg_df["Triglycerides (mg/dL)"] /
            agg_df["HDL Cholesterol (mg/dL)"]
        )

    # 2. TyG Index
    if {"Triglycerides (mg/dL)", "Glucose (mg/dL)"}.issubset(agg_df.columns):
        agg_df["TyG"] = np.log(
            (agg_df["Triglycerides (mg/dL)"] *
             agg_df["Glucose (mg/dL)"]) / 2
        )

    # 3. UACR
    if {"Urine Albumin (mg/mL)", "Urine creatinine (mg/mL)"}.issubset(agg_df.columns):
        agg_df["UACR (mg/g)"] = (
            agg_df["Urine Albumin (mg/mL)"] /
            agg_df["Urine creatinine (mg/mL)"]
        ) * 1000

    return agg_df
