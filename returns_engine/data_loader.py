
"""Load and validate the official PS-049 teacher sample-data pack."""

import csv
from pathlib import Path


REQUIRED_COLUMNS = {
    "categories.csv": [
        "category", "category_class",
        "return_window_days", "doa_window_days"
    ],
    "products.csv": [
        "sku", "product_name", "category", "list_price"
    ],
    "accessories.csv": [
        "sku", "accessory_id", "accessory_name", "master_price"
    ],
    "sellers.csv": [
        "seller_id", "seller_name"
    ],
    "holidays.csv": [
        "holiday_date", "name"
    ],
    "customers.csv": [
        "customer_id", "customer_name", "city",
        "mobile", "wallet_balance"
    ],
    "orders.csv": [
        "order_id", "customer_id", "sku", "serial_number",
        "price_paid", "payment_mode", "order_date",
        "delivered_ts", "seller_id"
    ],
    "prior_returns.csv": [
        "prior_return_id", "customer_id",
        "request_date", "reason_code"
    ],
    "warehouse_receipts.csv": [
        "return_id", "received_ts", "serial_scanned",
        "accessories_missing", "defect_confirmed"
    ],
    "grading.csv": [
        "return_id", "graded_ts", "cosmetic_scratches",
        "functional_fault", "original_box_missing",
        "seal_broken", "usage_detected"
    ],
}


def read_csv_file(folder: Path, filename: str) -> list[dict]:
    """Read a CSV file and check its required columns."""

    file_path = folder / filename

    if not file_path.is_file():
        raise FileNotFoundError(
            f"Required sample-data file not found: {file_path}"
        )

    with file_path.open(
        mode="r",
        encoding="utf-8-sig",
        newline=""
    ) as file:
        reader = csv.DictReader(file)

        if not reader.fieldnames:
            raise ValueError(f"{filename} is empty or has no header.")

        reader.fieldnames = [
            name.strip() if name else name
            for name in reader.fieldnames
        ]

        required = REQUIRED_COLUMNS[filename]
        missing = [
            column for column in required
            if column not in reader.fieldnames
        ]

        if missing:
            raise ValueError(
                f"{filename} is missing columns: {missing}"
            )

        rows = []

        for row_number, row in enumerate(reader, start=2):
            if None in row:
                raise ValueError(
                    f"{filename}, row {row_number}: "
                    "unexpected extra CSV values."
                )

            clean_row = {
                key: value.strip() if value is not None else ""
                for key, value in row.items()
            }

            rows.append(clean_row)

        return rows


def load_sample_pack(folder_path: str) -> dict:
    """Load all ten CSV files and the official commands.txt."""

    folder = Path(folder_path)

    if not folder.is_dir():
        raise NotADirectoryError(
            f"Sample-data folder not found: {folder}"
        )

    tables = {}

    for filename in REQUIRED_COLUMNS:
        table_name = filename.removesuffix(".csv")
        tables[table_name] = read_csv_file(folder, filename)

    commands_path = folder / "commands.txt"

    if not commands_path.is_file():
        raise FileNotFoundError(
            f"Required command file not found: {commands_path}"
        )

    commands = commands_path.read_text(
        encoding="utf-8-sig"
    ).splitlines()

    return {
        "tables": tables,
        "commands": commands,
        "folder": folder
    }
