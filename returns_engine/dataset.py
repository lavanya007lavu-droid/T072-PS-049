
"""Build indexed master data from the official PS-049 sample pack."""

from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal, InvalidOperation

from .data_loader import load_sample_pack


@dataclass
class MasterData:
    categories: dict
    products: dict
    accessories_by_sku: dict
    sellers: dict
    customers: dict
    orders: dict
    prior_returns_by_customer: dict
    receipts_by_return: dict
    grading_by_return: dict
    holidays: set
    commands: list


def index_unique(rows, key, table_name):
    """Create an index and reject duplicate IDs."""

    result = {}

    for row in rows:
        value = row.get(key, "").strip()

        if not value:
            raise ValueError(
                f"{table_name}: missing {key}"
            )

        if value in result:
            raise ValueError(
                f"{table_name}: duplicate {key} {value}"
            )

        result[value] = row

    return result


def validate_decimal(row, field, table_name):
    """Validate a non-negative money value."""

    try:
        value = Decimal(row[field])
    except (InvalidOperation, KeyError) as exc:
        raise ValueError(
            f"{table_name}: invalid {field}"
        ) from exc

    if not value.is_finite() or value < 0:
        raise ValueError(
            f"{table_name}: {field} cannot be negative"
        )


def validate_date(value, description):
    try:
        date.fromisoformat(value)
    except ValueError as exc:
        raise ValueError(
            f"Invalid date in {description}: {value}"
        ) from exc


def validate_timestamp(value, description):
    """Validate the teacher's local IST timestamp format."""

    try:
        datetime.strptime(value, "%Y-%m-%d %H:%M:%S")
    except ValueError as exc:
        raise ValueError(
            f"Invalid timestamp in {description}: {value}"
        ) from exc


def load_master_data(folder_path):
    """Load, index and cross-check all official master data."""

    pack = load_sample_pack(folder_path)
    tables = pack["tables"]

    categories = index_unique(
        tables["categories"], "category", "categories.csv"
    )

    products = index_unique(
        tables["products"], "sku", "products.csv"
    )

    sellers = index_unique(
        tables["sellers"], "seller_id", "sellers.csv"
    )

    customers = index_unique(
        tables["customers"], "customer_id", "customers.csv"
    )

    orders = index_unique(
        tables["orders"], "order_id", "orders.csv"
    )

    receipts = index_unique(
        tables["warehouse_receipts"], "return_id",
        "warehouse_receipts.csv"
    )

    grading = index_unique(
        tables["grading"], "return_id", "grading.csv"
    )

    accessories_by_sku = {}

    for row in tables["accessories"]:
        sku = row["sku"]

        accessories_by_sku.setdefault(sku, []).append(row)

        validate_decimal(
            row, "master_price", "accessories.csv"
        )

    prior_returns_by_customer = {}

    for row in tables["prior_returns"]:
        customer_id = row["customer_id"]

        prior_returns_by_customer.setdefault(
            customer_id, []
        ).append(row)

        validate_date(
            row["request_date"], "prior_returns.csv"
        )

    holidays = set()

    for row in tables["holidays"]:
        validate_date(
            row["holiday_date"], "holidays.csv"
        )
        holidays.add(date.fromisoformat(row["holiday_date"]))

    # Check product-to-category relationships.
    for sku, product in products.items():
        if product["category"] not in categories:
            raise ValueError(
                f"Product {sku} refers to an unknown category"
            )

        validate_decimal(
            product, "list_price", "products.csv"
        )

    # Check accessory-to-product relationships.
    for sku in accessories_by_sku:
        if sku not in products:
            raise ValueError(
                f"Accessories refer to unknown SKU: {sku}"
            )

    # Check order-to-customer, product and seller relationships.
    for order_id, order in orders.items():
        if order["customer_id"] not in customers:
            raise ValueError(
                f"Order {order_id} has an unknown customer"
            )

        if order["sku"] not in products:
            raise ValueError(
                f"Order {order_id} has an unknown SKU"
            )

        if order["seller_id"] not in sellers:
            raise ValueError(
                f"Order {order_id} has an unknown seller"
            )

        if order["payment_mode"] not in {"PREPAID", "COD"}:
            raise ValueError(
                f"Order {order_id} has an invalid payment mode"
            )

        validate_decimal(
            order, "price_paid", "orders.csv"
        )

        validate_date(
            order["order_date"], "orders.csv"
        )

        validate_timestamp(
            order["delivered_ts"], "orders.csv"
        )

    for category in categories.values():
        int(category["return_window_days"])
        int(category["doa_window_days"])

    for customer in customers.values():
        validate_decimal(
            customer, "wallet_balance", "customers.csv"
        )

    for row in tables["warehouse_receipts"]:
        validate_timestamp(
            row["received_ts"], "warehouse_receipts.csv"
        )

    for row in tables["grading"]:
        validate_timestamp(
            row["graded_ts"], "grading.csv"
        )

        scratches = int(row["cosmetic_scratches"])

        if scratches < 0:
            raise ValueError(
                "Grading scratches cannot be negative"
            )

    for customer_id in prior_returns_by_customer:
        if customer_id not in customers:
            raise ValueError(
                f"Prior return has unknown customer: {customer_id}"
            )

    return MasterData(
        categories=categories,
        products=products,
        accessories_by_sku=accessories_by_sku,
        sellers=sellers,
        customers=customers,
        orders=orders,
        prior_returns_by_customer=prior_returns_by_customer,
        receipts_by_return=receipts,
        grading_by_return=grading,
        holidays=holidays,
        commands=pack["commands"],
    )
