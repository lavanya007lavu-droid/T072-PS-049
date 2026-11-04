
"""Write the three CSV files required by the PS-049 evaluation."""

import csv
from pathlib import Path


CASE_COLUMNS = [
    "return_id",
    "order_id",
    "decision",
    "final_state",
    "grade",
    "score",
    "routing",
    "refund_amount",
    "restocking_fee",
    "pickup_fee",
    "accessory_deduction",
    "refund_mode",
    "refund_date",
    "recovery_amount",
    "loss_amount",
    "loss_bearer",
    "courier_claim",
    "wallet_charge",
]

STATE_COLUMNS = [
    "line_no",
    "return_id",
    "from_state",
    "to_state",
    "status",
    "reason",
]

WEEKLY_COLUMNS = [
    "week_start",
    "week_end",
    "routing",
    "units",
    "price_total",
    "recovery_total",
    "loss_total",
    "courier_claims",
    "seller_recovery",
    "platform_loss",
]


def write_csv(path, columns, rows):
    """Write rows using the exact required column order."""

    path.parent.mkdir(parents=True, exist_ok=True)

    with path.open(
        mode="w",
        encoding="utf-8",
        newline=""
    ) as file:
        writer = csv.DictWriter(
            file,
            fieldnames=columns,
            extrasaction="ignore"
        )

        writer.writeheader()
        writer.writerows(rows)


def write_outputs(engine, output_folder="output"):
    """Generate all three official evaluation CSV files."""

    folder = Path(output_folder)
    folder.mkdir(parents=True, exist_ok=True)

    case_path = folder / "case_files.csv"
    state_path = folder / "state_log.csv"
    weekly_path = folder / "weekly_report.csv"

    write_csv(case_path, CASE_COLUMNS, engine.case_files)
    write_csv(state_path, STATE_COLUMNS, engine.state_log)
    write_csv(weekly_path, WEEKLY_COLUMNS, engine.weekly_rows)

    return {
        "case_files": str(case_path),
        "state_log": str(state_path),
        "weekly_report": str(weekly_path),
    }
