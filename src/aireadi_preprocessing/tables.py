"""Preserve OMOP long tables; pivot only with an explicit concept/unit selection."""
import pandas as pd


def read_table(path, sep=","):
    df = pd.read_csv(path, sep=sep, dtype=str, keep_default_na=False)
    if "person_id" not in df and "participant_id" in df:
        df = df.rename(columns={"participant_id": "person_id"})
    if "person_id" not in df or df.person_id.eq("").any():
        raise ValueError("A nonempty person_id is required")
    return df


def pivot_measurements(df, mapping):
    """mapping CSV: concept_id,name,unit. Reject ambiguous participant features."""
    required = {"concept_id", "name", "unit"}
    if not required.issubset(mapping.columns) or mapping.empty:
        raise ValueError("Mapping requires concept_id,name,unit")
    if mapping.name.eq("").any() or mapping.concept_id.eq("").any() or mapping.name.eq("person_id").any():
        raise ValueError("Invalid mapping name or concept ID")
    if mapping.name.duplicated().any() or mapping.concept_id.duplicated().any():
        raise ValueError("Mapping names and concepts must be unique")
    needed = {"person_id", "measurement_concept_id", "unit_source_value", "value_as_number"}
    if not needed.issubset(df.columns):
        raise ValueError("Measurement table lacks required columns")
    selected = df.merge(mapping, left_on="measurement_concept_id", right_on="concept_id", how="inner", validate="many_to_one")
    if (selected.unit_source_value != selected.unit).any():
        raise ValueError("Measurement unit does not match mapping; no implicit conversion")
    if selected.duplicated(["person_id", "name"]).any():
        raise ValueError("Repeated participant/concept values require a study-specific aggregation")
    selected["value_as_number"] = pd.to_numeric(selected.value_as_number.replace("", float("nan")), errors="raise")
    result = selected.pivot(index="person_id", columns="name", values="value_as_number")
    return result.reindex(index=df.person_id.drop_duplicates(), columns=mapping.name).reset_index()
