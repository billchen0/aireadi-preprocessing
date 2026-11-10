"""Command-line interface. Outputs must be outside the dataset and package."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import platform
import importlib.metadata
from . import __version__
from .tables import read_table, pivot_measurements, measurement_mapping


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--version", action="version", version=__version__)
    parser.add_argument("dataset", type=Path, nargs="?", help="AI-READI dataset directory")
    parser.add_argument("destination", type=Path, nargs="?", help="New output directory")
    parser.add_argument("--dataset-root", type=Path, help=argparse.SUPPRESS)
    parser.add_argument("--output", type=Path, help=argparse.SUPPRESS)
    parser.add_argument("--release", default="3.0.0", choices=["3.0.0"])
    parser.add_argument("--mapping", "--measurement-mapping", dest="measurement_mapping", type=Path, help="Selected concept_id,name,unit CSV")
    args = parser.parse_args()
    if args.dataset and args.dataset_root or args.destination and args.output:
        parser.error("Specify each path once")
    dataset, destination = args.dataset or args.dataset_root, args.destination or args.output
    if dataset is None or destination is None:
        parser.error("Provide the dataset and output paths")
    root, output = dataset.resolve(), destination.resolve()
    package = Path(__file__).resolve().parents[2]
    if not root.is_dir():
        parser.error("Dataset root does not exist")
    if output == root or root in output.parents or output == package or package in output.parents:
        parser.error("Output must be outside dataset and package")
    if output.exists():
        parser.error("Output directory already exists; choose a new run directory")
    output.mkdir(parents=True)
    report = {"status": "running", "package_version": __version__, "python": platform.python_version(), "dependencies": {name: importlib.metadata.version(name) for name in ["pandas", "numpy"]}, "release": args.release, "steps": ["clinical"], "created_utc": datetime.now(timezone.utc).isoformat(), "outputs": {}, "input_sha256": {}}

    def fingerprint(path, label):
        digest = hashlib.sha256()
        with path.open("rb") as handle:
            for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(chunk)
        report["input_sha256"][label] = digest.hexdigest()

    def save(df, name):
        df.to_csv(output / name, index=False)
        report["outputs"][name] = {"rows": len(df), "sha256": hashlib.sha256((output / name).read_bytes()).hexdigest()}

    try:
        for name in ["measurement", "observation"]:
            path = root / "clinical_data" / f"{name}.csv"
            fingerprint(path, name)
            table = read_table(path)
            save(table, f"{name}_long.csv")
            if name == "measurement":
                if args.measurement_mapping:
                    fingerprint(args.measurement_mapping, "measurement_mapping")
                    mapping = read_mapping(args.measurement_mapping)
                else:
                    mapping = measurement_mapping(table)
                save(mapping, "clinical_mapping.csv")
                save(pivot_measurements(table, mapping), "measurement_wide.csv")
        report["status"] = "complete"
    except Exception:
        report["status"] = "failed"
        raise
    finally:
        (output / "run.json").write_text(json.dumps(report, indent=2) + "\n")


def read_mapping(path):
    import pandas as pd
    return pd.read_csv(path, dtype=str, keep_default_na=False)


if __name__ == "__main__":
    main()
