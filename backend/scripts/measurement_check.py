"""
Evaluation script to benchmark stored AI crack measurements against ground truth ruler measurements.

Reads CSV format:
image_id,true_length_mm,true_width_mm

Computes absolute and relative errors, and Mean Absolute Error (MAE).
"""

import argparse
import csv
import sys
from pathlib import Path

# Add backend directory to sys.path
backend_dir = Path(__file__).resolve().parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from app.database import SessionLocal
from app.models.analysis import AnalysisRun, CrackMeasurement


def run_measurement_check(csv_path: Path):
    if not csv_path.exists():
        print(f"Error: CSV file not found at '{csv_path}'")
        print("\nTemplate format required:")
        print("image_id,true_length_mm,true_width_mm")
        print("1,120.5,2.4")
        return

    db = SessionLocal()
    rows_evaluated = 0
    length_errors = []
    width_errors = []
    length_rel_errors = []
    width_rel_errors = []

    print("\n" + "=" * 100)
    print("INFRASCAN AI - GROUND TRUTH CRACK MEASUREMENT VERIFICATION REPORT")
    print("=" * 100)
    print(f"Reading ground truth measurements from: {csv_path}\n")

    header_fmt = "{:<8} {:<14} {:<12} {:<14} {:<12} {:<14} {:<12} {:<14} {:<12}"
    print(header_fmt.format(
        "Img ID", "Meas Len(mm)", "True Len(mm)", "Abs Err(mm)", "Rel Err(%)",
        "Meas Wid(mm)", "True Wid(mm)", "Abs Err(mm)", "Rel Err(%)"
    ))
    print("-" * 100)

    try:
        with open(csv_path, mode="r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                img_id_str = row.get("image_id", "").strip()
                true_len_str = row.get("true_length_mm", "").strip()
                true_wid_str = row.get("true_width_mm", "").strip()

                if not (img_id_str and true_len_str and true_wid_str):
                    continue

                img_id = int(img_id_str)
                true_len = float(true_len_str)
                true_wid = float(true_wid_str)

                # Query latest completed analysis run
                run = (
                    db.query(AnalysisRun)
                    .filter(AnalysisRun.image_id == img_id, AnalysisRun.status == "done")
                    .order_by(AnalysisRun.run_id.desc())
                    .first()
                )

                if not run or not run.crack_measurements:
                    print(f"{img_id:<8} [No completed analysis run or crack measurements found]")
                    continue

                meas = run.crack_measurements[0]
                if meas.length_mm is None or meas.avg_width_mm is None:
                    print(f"{img_id:<8} [Image has no scale configured: pixels only ({meas.length_px:.1f} px, {meas.avg_width_px:.1f} px)]")
                    continue

                meas_len = float(meas.length_mm)
                meas_wid = float(meas.avg_width_mm)

                err_len = abs(meas_len - true_len)
                rel_len = (err_len / true_len * 100.0) if true_len > 0 else 0.0

                err_wid = abs(meas_wid - true_wid)
                rel_wid = (err_wid / true_wid * 100.0) if true_wid > 0 else 0.0

                length_errors.append(err_len)
                width_errors.append(err_wid)
                length_rel_errors.append(rel_len)
                width_rel_errors.append(rel_wid)
                rows_evaluated += 1

                print(header_fmt.format(
                    img_id,
                    f"{meas_len:.2f}",
                    f"{true_len:.2f}",
                    f"{err_len:.2f}",
                    f"{rel_len:.1f}%",
                    f"{meas_wid:.2f}",
                    f"{true_wid:.2f}",
                    f"{err_wid:.2f}",
                    f"{rel_wid:.1f}%",
                ))

        print("-" * 100)
        if rows_evaluated > 0:
            mae_len = sum(length_errors) / rows_evaluated
            mre_len = sum(length_rel_errors) / rows_evaluated
            mae_wid = sum(width_errors) / rows_evaluated
            mre_wid = sum(width_rel_errors) / rows_evaluated

            print(f"\nSummary across {rows_evaluated} scaled images:")
            print(f"  * Length Mean Absolute Error (MAE): {mae_len:.3f} mm (Mean Relative: {mre_len:.2f}%)")
            print(f"  * Width Mean Absolute Error (MAE):  {mae_wid:.3f} mm (Mean Relative: {mre_wid:.2f}%)")
        else:
            print("\nNo scaled images evaluated. Ensure images have a scale configured via PUT /images/{id}/scale.")

    finally:
        db.close()
    print("=" * 100 + "\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Check crack measurements against ground truth CSV")
    parser.add_argument(
        "csv_file",
        nargs="?",
        default=str(backend_dir / "data" / "measurement_ground_truth.csv"),
        help="Path to ground truth CSV (columns: image_id, true_length_mm, true_width_mm)",
    )
    args = parser.parse_args()
    run_measurement_check(Path(args.csv_file))

