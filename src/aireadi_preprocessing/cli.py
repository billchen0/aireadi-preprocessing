"""Write categorized long-format clinical CSVs to a processed folder."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
from . import __version__
from .api import load_clinical


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--version", action="version", version=__version__)
    parser.add_argument("dataset", type=Path, help="AI-READI dataset directory")
    parser.add_argument("output", type=Path, nargs="?", help="New folder; default: processed beside the dataset")
    args = parser.parse_args()
    root = args.dataset.resolve()
    output = (args.output or root.parent / "processed").resolve()
    if not root.is_dir():
        parser.error("Dataset directory does not exist")
    if root == output or root in output.parents:
        parser.error("Choose an output folder outside the source dataset")
    if output.exists():
        parser.error("Output folder already exists; choose a new folder")
    # Load before creating outputs, so invalid inputs leave no partial folder.
    tables = load_clinical(root)
    output.mkdir(parents=True)
    report = {"status": "running", "package_version": __version__, "created_utc": datetime.now(timezone.utc).isoformat(), "outputs": {}}
    try:
        for category, frame in tables.items():
            path = output / f"{category}.csv"
            frame.to_csv(path, index=False)
            report["outputs"][path.name] = {"rows": len(frame), "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}
        report["status"] = "complete"
    except Exception:
        report["status"] = "failed"
        raise
    finally:
        (output / "run.json").write_text(json.dumps(report, indent=2) + "\n")


if __name__ == "__main__":
    main()
