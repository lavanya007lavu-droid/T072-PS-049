# T072 – PS-049: Returns and Reverse Logistics Grading Engine

**Project:** Returns and Reverse Logistics Grading Engine (Refurb, Restock, Scrap)  
**Team:** T072 – Lavanya V and Likith U  
**Language:** Python 3.10+  
**Application Type:** Command-file-driven backend; no graphical user interface

## 1. Project Overview

This project processes product-return requests and manages the reverse-logistics workflow. It checks return eligibility, records pickup attempts, verifies returned products at the warehouse, grades product condition, selects a disposition route, calculates refunds and recoveries, and produces evaluation reports.

The implementation supports two input paths:

1. **Legacy JSON development path:** `sample_data/commands.json`, processed by `returns_engine.cli`.
2. **Official teacher sample-data path:** CSV master files and `commands.txt` in `sample_data/teacher_pack/`, processed by `returns_engine.official_cli`.

The official teacher sample-data path is the primary path for processing the supplied capstone sample pack.

## 2. Project Structure

```text
T072-PS-049/
├── docs/                         # Design and decision documents
├── returns_engine/               # Python application modules
│   ├── cli.py                    # Legacy JSON command runner
│   ├── data_loader.py            # Reads teacher CSV files and commands.txt
│   ├── dataset.py                # Indexes and validates master data
│   ├── command_parser.py          # Parses pipe-separated commands
│   ├── official_cli.py           # Official sample-pack entry point
│   ├── official_engine.py        # Official command-processing workflow
│   ├── output_writer.py          # Writes the three evaluation CSV files
│   └── ...                       # Other domain, validation and rule modules
├── sample_data/
│   ├── commands.json             # Legacy JSON development input
│   └── teacher_pack/             # Official teacher sample-data pack
│       ├── accessories.csv
│       ├── categories.csv
│       ├── commands.txt
│       ├── customers.csv
│       ├── grading.csv
│       ├── holidays.csv
│       ├── orders.csv
│       ├── prior_returns.csv
│       ├── products.csv
│       ├── sellers.csv
│       ├── warehouse_receipts.csv
│       └── README.md
├── tests/
│   ├── test_engine.py
│   └── test_official_pack.py
├── output/                       # Generated evaluation CSV files
├── README.md
├── requirements.txt
└── create_design_pdf.py
```

## 3. Official Input Data

The official sample pack is stored in `sample_data/teacher_pack/`.

It contains ten CSV data files:

- `categories.csv` – Category class and return/DOA windows.
- `products.csv` – SKU, product name, category and list price.
- `accessories.csv` – Bundled accessory IDs and master prices.
- `sellers.csv` – Seller master data.
- `holidays.csv` – Non-business dates for settlement calculations.
- `customers.csv` – Customer details and opening wallet balances.
- `orders.csv` – Delivered orders, serial numbers, price paid, payment mode and seller.
- `prior_returns.csv` – Earlier customer returns used for the 90-day abuse rule.
- `warehouse_receipts.csv` – Receipt timestamp, scanned serial, missing accessories and defect confirmation.
- `grading.csv` – Timestamps and product-condition grading inputs.

`commands.txt` contains pipe-separated commands. The processor ignores blank lines and comment lines beginning with `#`, and processes executable commands in file order.

The command types in the sample pack are:

- `RETURN_REQUEST`
- `SCHEDULE_PICKUP`
- `PICKUP_ATTEMPT`
- `REOPEN`
- `RECEIVE`
- `GRADE`
- `APPROVE`
- `REFURB_QC`
- `WEEKLY_REPORT`
- `PRINT_CASE`

The supplied sample pack contains 401 executable command lines (403 physical lines, including comments and blank lines).

## 4. Main Workflow and Business Rules

The application implements these main stages:

1. Read and validate order and master data.
2. Evaluate a return request and decide whether it is accepted or rejected.
3. Schedule pickup and record up to two pickup attempts on consecutive days.
4. Allow one reopening within three days after the second failed pickup.
5. Receive the returned unit and compare the scanned serial number with the order serial number. A mismatch moves the case to `FRAUD_REVIEW` and blocks a refund.
6. Grade the unit using the grading record and apply the disposition route.
7. Process refurbishment QC separately for Grade B.
8. Calculate refund, deductions, recovery and loss allocation.
9. Process manager approvals for eligible Grade C/D refund cases.
10. Write case-file, state-log and weekly-report CSV files.

### Grading and Disposition

- Score = 100 − min(10 × scratches, 30) − 40 (functional fault) − 10 (box missing) − 15 (seal broken) − 20 (usage detected).
- Grade A: score ≥ 90.
- Grade B: score 70–89.
- Grade C: score 50–69.
- Grade D: score < 50.
- Grade A: 100% price recovery; route `RESTOCK`.
- Grade B: 85% resale value; if refurbishment QC passes, refurbishment cost is ₹500 + 5% of price. If QC fails, liquidate at 50% of price.
- Grade C: liquidate at 50% of price.
- Grade D: ₹0 recovery and ₹50 disposal cost; route `SCRAP`.
- Missing-accessory deduction is capped at 30% of the gross refund.

### Refund and Loss Rules

- `WRONG_ITEM` and `DAMAGED_IN_TRANSIT`: Full refund, subject to warehouse and serial checks.
- `CHANGED_MIND`: 10% restocking fee, minimum ₹100, plus ₹99 pickup fee.
- A qualifying repeat-return abuse case uses a 20% restocking fee and no free pickup, except for `DAMAGED_IN_TRANSIT`.
- A `DEFECTIVE` case requires warehouse defect confirmation. If no defect is confirmed, it is treated as `CHANGED_MIND`.
- Grade A/B refunds are initiated on receipt; Grade C/D refunds require manager approval.
- COD refunds are credited to the customer wallet; prepaid refunds are settled to the source within five business days, excluding Sundays and listed holidays.
- Courier claim rule in the brief: `min(price_paid − recovery_value, declared_value, ₹5,000)`.
- Seller, courier and platform loss allocation follows the project brief and decision log.
- Same-SKU exchange skips the normal refund. For Grade C/D exchange units, the wallet charge is based on full refund value minus recovery; a negative wallet balance is permitted by the brief.

## 5. Running the Project

Run commands from the repository root folder (`T072-PS-049`). Python 3.10 or later is required. No third-party packages are required for the current implementation.

### Check Python Syntax

```powershell
python -m compileall -q returns_engine
```

### Run All Automated Tests

```powershell
python -m unittest discover -s tests -v
```

### Process the Official Teacher Sample Pack

```powershell
python -m returns_engine.official_cli
```

The official processor reads the data from `sample_data/teacher_pack/` and writes the following files under `output/`:

- `output/case_files.csv`
- `output/state_log.csv`
- `output/weekly_report.csv`

### Run the Legacy JSON Development Path

```powershell
python -m returns_engine.cli sample_data/commands.json
```

This legacy path writes `output/report.json`. It is retained for the earlier development tests. Use the official command above for the teacher's supplied sample pack.

## 6. Evaluation Output Formats

### `case_files.csv`

```text
return_id,order_id,decision,final_state,grade,score,routing,refund_amount,restocking_fee,pickup_fee,accessory_deduction,refund_mode,refund_date,recovery_amount,loss_amount,loss_bearer,courier_claim,wallet_charge
```

One row is produced per `PRINT_CASE` command, in command-file order.

### `state_log.csv`

```text
line_no,return_id,from_state,to_state,status,reason
```

One row is produced per state transition or rejected command, in command-file order. `status` is `OK` for a successful transition and `ERROR` for a rejected or illegal command.

### `weekly_report.csv`

```text
week_start,week_end,routing,units,price_total,recovery_total,loss_total,courier_claims,seller_recovery,platform_loss
```

One row is produced per routing per `WEEKLY_REPORT` command, as specified by the teacher's README.

## 7. Current Sample-Pack Verification Checkpoint

The latest recorded local run against the supplied teacher sample pack produced:

- 401 executable commands parsed.
- 60 return cases created.
- 60 rows in `case_files.csv`.
- 371 rows in `state_log.csv`.
- 8 rows in `weekly_report.csv`.
- 6 commands recorded with `ERROR` status.
- 34 automated tests passed (20 existing tests and 14 official sample-pack tests).

The six errors correspond to rejected commands in the supplied sample data:

- Line 79: Pickup scheduling for a rejected non-returnable item.
- Line 121: Grading after a serial mismatch moved the case to `FRAUD_REVIEW`.
- Lines 151, 152 and 304: Manager refund approval attempted for exchange cases.
- Line 244: Reopening attempted outside the permitted three-day period.

These are expected rejected commands in the supplied sample data. They do not prove that every hidden evaluation case has passed. Re-run the syntax check, tests and official processor after code changes. The teacher's brief says the final evaluation uses a separate hidden input set and compares output fields.

## 8. Decisions and Assumptions Pending Organiser Confirmation

See `docs/DECISION_LOG.md` and the official sample-pack README. Do not silently treat unresolved assumptions as confirmed organiser policy.

1. **Courier declared value:** The supplied `orders.csv` does not include a `declared_value` column, although the brief's courier-claim formula refers to declared value. The current implementation uses `price_paid` as a provisional available value for this part of the calculation. Ask the organiser to confirm the intended source or value.
2. **Loss accounting:** Confirm the intended output meaning of `loss_amount` and the treatment of refurbishment cost (₹500 + 5% for Grade B QC pass) and Grade D disposal cost (₹50) if the brief does not explicitly define how these costs are included in loss totals.
3. **Exchange decision/output convention:** Confirm any output-field convention for exchange cases if the organiser provides an explicit expected-output example.

For questions about a sample-data file or column, reply on the original capstone email thread, as instructed by the organiser.

## 9. Viva Preparation

Be prepared to explain:

1. Why three scratches plus a broken seal gives a score of 55 and therefore Grade C.
2. Why a serial mismatch moves the case to `FRAUD_REVIEW` and prevents a refund.
3. Why Grade C/D refunds wait for manager approval.
4. Why `RECEIVE` and `GRADE` are separate commands.
5. Why Grade B refurbishment QC is a separate command and can result in `RESOLD` or `LIQUIDATED`.
6. How the parser preserves the order of the 401 executable command lines.
7. How CSV files are linked using identifiers such as `order_id`, `sku`, `customer_id` and `return_id`.
8. The difference between customer refund, product recovery, seller recovery, courier claim and platform loss.

## 10. Final Submission Checklist

Check the organiser's latest submission instructions. The required final submission items are:

- GitHub repository named `T072-PS-049`.
- Updated `README.md`.
- Design document PDF.
- Automated test suite.
- Decision log (`docs/DECISION_LOG.md`).
- Five-minute demo video link.

The project repository is available at:

[GitHub Repository – T072-PS-049](https://github.com/lavanya007lavu-droid/T072-PS-049)

Before final submission, check the Git working tree, commit all pending changes and push them to the GitHub repository.

The supplied sample pack is a development test set. It does not include expected output files, so an exact comparison with official expected outputs has not been performed. The organiser's separate hidden evaluation input remains the final correctness test.

For project-related queries, reply to the organiser on the same email thread, as instructed.