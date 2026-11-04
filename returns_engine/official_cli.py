
"""Entry point for processing the official PS-049 sample pack."""

import argparse

from .dataset import load_master_data
from .official_engine import OfficialEngine
from .output_writer import write_outputs


def main():
    parser = argparse.ArgumentParser(
        description="PS-049 official sample-data processor"
    )

    parser.add_argument(
        "--data",
        default="sample_data/teacher_pack",
        help="Folder containing the teacher's sample data"
    )

    parser.add_argument(
        "--output",
        default="output",
        help="Folder for generated CSV reports"
    )

    args = parser.parse_args()

    print("Loading teacher's sample data...")

    data = load_master_data(args.data)

    print("Loading successful.")
    print(f"Orders: {len(data.orders)}")
    print(f"Commands: {sum(1 for line in data.commands if line.strip() and not line.lstrip().startswith('#'))}")

    print("\nProcessing return commands...")

    engine = OfficialEngine(data)
    engine.process()

    print("\nWriting output files...")

    paths = write_outputs(engine, args.output)

    errors = [
        row for row in engine.state_log
        if row["status"] == "ERROR"
    ]

    print("\nProcessing summary")
    print("------------------")
    print(f"Return cases created: {len(engine.cases)}")
    print(f"Case-file rows: {len(engine.case_files)}")
    print(f"State-log rows: {len(engine.state_log)}")
    print(f"Weekly-report rows: {len(engine.weekly_rows)}")
    print(f"Command errors: {len(errors)}")

    print("\nGenerated files:")

    for name, path in paths.items():
        print(f"{name}: {path}")

    if errors:
        print("\nFirst 10 command errors:")

        for error in errors[:10]:
            print(
                f"Line {error['line_no']}: "
                f"{error['return_id']} - {error['reason']}"
            )


if __name__ == "__main__":
    main()
