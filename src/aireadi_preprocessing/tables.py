"""Apply standardized names while preserving original measurement values."""
import pandas as pd


def read_table(path, sep=","):
    df = pd.read_csv(path, sep=sep, dtype=str, keep_default_na=False)
    if "person_id" not in df and "participant_id" in df:
        df = df.rename(columns={"participant_id": "person_id"})
    if "person_id" not in df or df.person_id.eq("").any():
        raise ValueError("A nonempty person_id is required")
    return df


def pivot_measurements(df, mapping):
    """Use the first nonmissing value per participant/code, as in the original extractor."""
    required = {"concept_id", "name"}
    if not required.issubset(mapping.columns) or mapping.empty:
        raise ValueError("Mapping requires concept_id,name (optional unit)")
    if mapping.name.eq("").any() or mapping.concept_id.eq("").any() or mapping.name.eq("person_id").any():
        raise ValueError("Invalid mapping name or concept ID")
    if mapping.name.duplicated().any() or mapping.concept_id.duplicated().any():
        raise ValueError("Mapping names and concepts must be unique")
    needed = {"person_id", "measurement_concept_id", "unit_source_value", "value_as_number"}
    if not needed.issubset(df.columns):
        raise ValueError("Measurement table lacks required columns")
    selected = df.merge(mapping, left_on="measurement_concept_id", right_on="concept_id", how="inner", validate="many_to_one")
    if "unit" in mapping and (selected.unit_source_value != selected.unit).any():
        raise ValueError("Measurement unit does not match mapping; no implicit conversion")
    selected["value_as_number"] = pd.to_numeric(selected.value_as_number.replace("", float("nan")), errors="raise")
    result = selected.pivot_table(index="person_id", columns="name", values="value_as_number", aggfunc="first")
    return result.reindex(index=df.person_id.drop_duplicates(), columns=mapping.name).reset_index()


def measurement_mapping(df):
    """Select the bundled standardized names by measurement concept ID."""
    import json
    from importlib.resources import files
    definitions = json.loads(files("aireadi_preprocessing").joinpath("mappings.json").read_text())
    present = set(df.measurement_concept_id)
    rows = []
    for domain, names in definitions.items():
        if domain == "observations":
            continue
        for concept_id, name in names.items():
            if concept_id in present:
                units = sorted(set(df.loc[df.measurement_concept_id.eq(concept_id), "unit_source_value"]))
                rows.append({"concept_id": concept_id, "name": name, "domain": domain, "source_units": json.dumps(units)})
    if not rows:
        raise ValueError("No measurement codes match the bundled mapping; supply a custom mapping")
    return pd.DataFrame(rows)
