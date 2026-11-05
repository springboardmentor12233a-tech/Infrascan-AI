from __future__ import annotations

import argparse
import json
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser(description="Compare Milestone 2 evaluation reports.")
    parser.add_argument("reports", type=Path, nargs="+")
    parser.add_argument("--output", type=Path, default=Path("ml/artifacts/model-comparison.json"))
    args = parser.parse_args()
    entries = []
    for report_path in args.reports:
        report = json.loads(report_path.read_text(encoding="utf-8"))
        metrics = report.get("metrics", report.get("classification_report", {}).get("weighted avg", {}))
        score = metrics.get("dice", metrics.get("f1-score", metrics.get("accuracy", 0.0)))
        entries.append({"report": str(report_path), "task": report.get("task"), "score": score})
    entries.sort(key=lambda item: item["score"], reverse=True)
    comparison = {"reports": entries, "selected": entries[0] if entries else None}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(comparison, indent=2), encoding="utf-8")
    print(json.dumps(comparison, indent=2))


if __name__ == "__main__":
    main()
