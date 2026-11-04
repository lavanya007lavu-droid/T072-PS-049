# PS-049 – Returns and Reverse Logistics Grading Engine (Refurb, Restock, Scrap) — Sample Data Pack

Prepared by 10 SECONDS for Team T072.

## Files

| File | What it holds | Row count |
|---|---|---|
| `categories.csv` | Category classes and return / DOA windows | 11 data rows |
| `products.csv` | 22 SKUs with category and list price | 22 data rows |
| `accessories.csv` | Bundled accessories per SKU with master price | 18 data rows |
| `sellers.csv` | 5 sellers | 5 data rows |
| `holidays.csv` | Non-business days for refund timing | 3 data rows |
| `customers.csv` | Customers with wallet balance | 90 data rows |
| `orders.csv` | 150 delivered orders with serial number, price paid and delivery timestamp | 150 data rows |
| `prior_returns.csv` | Customers' returns before this pack (for the 90-day abuse rule) | 8 data rows |
| `warehouse_receipts.csv` | Condition check at warehouse receipt | 56 data rows |
| `grading.csv` | Grading inputs per received unit | 56 data rows |
| `commands.txt` | 60 return requests, pickups, receipts, grading, approvals, QC, 2 reopens, 5 exchanges, reports | 401 command lines (excluding comments) |

Row numbers quoted below are 1-based data-row numbers (the header is row 0). Line numbers for `commands.txt` are physical line numbers including comment lines.

## Column reference

Conventions: dates `YYYY-MM-DD`; timestamps `YYYY-MM-DD HH:MM:SS` (24h, IST, no timezone suffix); money in Rs as plain decimals with 2 places (no commas, no symbol); percentages as plain numbers (12.5 means 12.5%); booleans `true`/`false`; IDs uppercase with a fixed prefix.

### `categories.csv`

| Column | Type | Units / format | Allowed values | Notes |
|---|---|---|---|---|
| `category` | string | — | — | — |
| `category_class` | enum | — | ELECTRONICS, ACCESSORY, NO_RETURN | NO_RETURN always REJECTED |
| `return_window_days` | int | days from delivery | — | — |
| `doa_window_days` | int | days from delivery | — | applies to reason DEFECTIVE |

### `products.csv`

| Column | Type | Units / format | Allowed values | Notes |
|---|---|---|---|---|
| `sku` | string | SKU-xnn | — | — |
| `product_name` | string | — | — | — |
| `category` | string | — | categories.csv | — |
| `list_price` | decimal | Rs | — | — |

### `accessories.csv`

| Column | Type | Units / format | Allowed values | Notes |
|---|---|---|---|---|
| `sku` | string | — | products.csv | — |
| `accessory_id` | string | ACC-nn | — | — |
| `accessory_name` | string | — | — | — |
| `master_price` | decimal | Rs | — | deducted if missing (cap 30% of refund) |

### `sellers.csv`

| Column | Type | Units / format | Allowed values | Notes |
|---|---|---|---|---|
| `seller_id` | string | SEL-nn | — | — |
| `seller_name` | string | — | — | — |

### `holidays.csv`

| Column | Type | Units / format | Allowed values | Notes |
|---|---|---|---|---|
| `holiday_date` | date | — | — | Sundays are also non-business days |
| `name` | string | — | — | — |

### `customers.csv`

| Column | Type | Units / format | Allowed values | Notes |
|---|---|---|---|---|
| `customer_id` | string | CUST-nnnn | — | — |
| `customer_name` | string | — | — | — |
| `city` | string | — | — | — |
| `mobile` | string | 10 digits | — | — |
| `wallet_balance` | decimal | Rs | — | opening balance; may go negative after exchange charges |

### `orders.csv`

| Column | Type | Units / format | Allowed values | Notes |
|---|---|---|---|---|
| `order_id` | string | ORD-nnnn | — | — |
| `customer_id` | string | — | customers.csv | — |
| `sku` | string | — | products.csv | — |
| `serial_number` | string | SN + 10 chars | — | must match serial_scanned at receipt |
| `price_paid` | decimal | Rs | — | refund base |
| `payment_mode` | enum | — | PREPAID, COD | — |
| `order_date` | date | — | — | — |
| `delivered_ts` | timestamp | — | — | window day 1 = the day after delivery |
| `seller_id` | string | — | sellers.csv | — |

### `prior_returns.csv`

| Column | Type | Units / format | Allowed values | Notes |
|---|---|---|---|---|
| `prior_return_id` | string | PRR-nnn | — | — |
| `customer_id` | string | — | customers.csv | — |
| `request_date` | date | — | — | — |
| `reason_code` | enum | — | WRONG_ITEM, DAMAGED_IN_TRANSIT, CHANGED_MIND, DEFECTIVE | — |

### `warehouse_receipts.csv`

| Column | Type | Units / format | Allowed values | Notes |
|---|---|---|---|---|
| `return_id` | string | RR-nnnn | — | one row per RECEIVE command |
| `received_ts` | timestamp | — | — | equals the RECEIVE command time |
| `serial_scanned` | string | — | — | mismatch -> FRAUD_REVIEW |
| `accessories_missing` | string | accessory ids separated by ; | accessories.csv | may be blank |
| `defect_confirmed` | bool | — | — | DEFECTIVE cases only; may be blank |

### `grading.csv`

| Column | Type | Units / format | Allowed values | Notes |
|---|---|---|---|---|
| `return_id` | string | — | — | one row per GRADE command |
| `graded_ts` | timestamp | — | — | equals the GRADE command time |
| `cosmetic_scratches` | int | count | — | -10 each, max -30 |
| `functional_fault` | bool | — | — | -40 |
| `original_box_missing` | bool | — | — | -10 |
| `seal_broken` | bool | — | — | -15 |
| `usage_detected` | bool | — | — | -20 |

## Command file format

`commands.txt` holds one command per line in the form `COMMAND_NAME|arg1|arg2|...`. Commands must be processed strictly in file order. Lines starting with `#` are comments and blank lines are ignored. Empty optional arguments are written as nothing between the pipes. Every command used in this pack:

| Command | Arguments (in order) | Meaning |
|---|---|---|
| `RETURN_REQUEST` | `timestamp|return_id|order_id|reason_code|request_type|evidence_provided` | request_type REFUND or EXCHANGE; decide ACCEPT / REJECT / ACCEPT_WITH_DEDUCTION |
| `SCHEDULE_PICKUP` | `timestamp|return_id|pickup_date` | Book pickup attempt 1 on pickup_date (attempt 2, if any, the next day) |
| `PICKUP_ATTEMPT` | `timestamp|return_id|attempt_no|result` | result SUCCESS or FAILED; second failure closes CUSTOMER_UNAVAILABLE |
| `REOPEN` | `timestamp|return_id` | Customer reopens a CUSTOMER_UNAVAILABLE case (once, within 3 days) |
| `RECEIVE` | `timestamp|return_id` | Warehouse receipt; read the warehouse_receipts.csv row |
| `GRADE` | `timestamp|return_id` | Grade using the grading.csv row and route |
| `APPROVE` | `timestamp|return_id|manager_id` | Manager approval releasing refunds for grades C and D |
| `REFURB_QC` | `timestamp|return_id|result` | PASS -> RESOLD at 85%; FAIL -> LIQUIDATED at 50% |
| `WEEKLY_REPORT` | `timestamp|week_start|week_end` | Disposition and loss report for that week |
| `PRINT_CASE` | `timestamp|return_id` | Print the case file |

## Planted scenarios

Every edge case in the brief, mapped to the exact record where it occurs, followed by extra traps.

- **EC-01 Return requested on day 7 at 23:59 of delivery**
  - RR-0023 on ORD-0070 (MOBILE, delivered 2026-10-03 14:00:00): RETURN_REQUEST at 2026-10-10 23:59:00 = day 7 — inside the 7-day window — `commands.txt line 78`
- **EC-02 DEFECTIVE claim where the warehouse finds no fault**
  - RR-0014: DEFECTIVE claim; warehouse_receipts.csv defect_confirmed=false -> refund as CHANGED_MIND (10% restocking, min Rs 100, Rs 99 pickup fee); seller does not bear the loss — `commands.txt line 49; warehouse_receipts.csv RR-0014 (row 13)`
- **EC-03 Three cosmetic scratches plus a broken seal (score exactly 70)**
  - RR-0015: grading row with cosmetic_scratches=3 and seal_broken=true (rule 5 arithmetic: 100 - 30 - 15 = 55, grade C — the brief's 'exactly 70' does not follow from rule 5); RR-0019: 2 scratches + missing box = exactly 70 -> grade B boundary — `grading.csv RR-0015 (row 18); grading.csv RR-0019 (row 20)`
- **EC-04 Missing accessories worth more than 30% of refund**
  - RR-0025 on ORD-0101 (price 3499.00): received without ACC-18 (master price 3299.00 > 30% of refund) — cap the deduction at 30% of the refund — `warehouse_receipts.csv RR-0025 (row 23)`
- **EC-05 Second pickup attempt failing on a Sunday**
  - RR-0037: pickup attempt 1 fails Sat 2026-10-17, attempt 2 fails Sun 2026-10-18 (consecutive days) -> CUSTOMER_UNAVAILABLE, no refund — `commands.txt line 234`
- **EC-06 Courier claim where loss exceeds Rs 5,000 cap**
  - RR-0007 on ORD-0078 (LAPTOP, Rs 61390.00): DAMAGED_IN_TRANSIT, grades D (scrap, Rs 0 recovery) -> loss far above Rs 5,000; courier claim capped at 5,000, rest borne per rule 8 — `commands.txt line 18; grading.csv RR-0007 (row 9)`
- **EC-07 Customer's third CHANGED_MIND return exactly 90 days after the first**
  - CUST-0008: prior CHANGED_MIND returns on 2026-07-18 and 2026-09-05; third CHANGED_MIND RR-0045 on 2026-10-16 = exactly 90 days after the first -> 20% restocking fee, no free pickup — `commands.txt line 186; prior_returns.csv rows 3, 8 for CUST-0008`
- **EC-08 Exchange unit grading D after replacement shipped**
  - RR-0020: EXCHANGE request; replacement ships on PICKED; unit then grades D (score 100-20-40-20 = 20) -> charge (full refund - recovery) to the customer's wallet, negative balance allowed — `commands.txt line 68; commands.txt line 92; grading.csv RR-0020 (row 16)`
- **Extra traps (not in the brief, but realistic):**
  - RR-0016: scanned serial differs from the order's serial -> FRAUD_REVIEW, no refund; the later GRADE command for it is an illegal transition — `warehouse_receipts.csv RR-0016 (row 14); commands.txt line 121`
  - RR-0021: IN_EAR_EARPHONES is NO_RETURN (hygiene) -> REJECTED; a SCHEDULE_PICKUP is still sent for it and must error — `commands.txt line 79`
  - RR-0018: CHANGED_MIND request on day 8 for a LAPTOP -> outside the 7-day window, REJECTED — `commands.txt line 61`
  - RR-0038: DEFECTIVE on day 25 for a phone (DOA window 30 days) -> accepted; defect confirmed; seller bears the loss — `commands.txt line 160`
  - REOPEN of RR-0026 exactly 3 days after it closed CUSTOMER_UNAVAILABLE (allowed once); REOPEN of RR-0028 4 days after closure -> rejected — `commands.txt line 203; commands.txt line 244`
  - RR-0030: grade B (score 70) -> REFURB; REFURB_QC FAIL -> downgrade to LIQUIDATE at 50% — `commands.txt line 272`
  - RR-0053: Rs 499 cable (ACCESSORY, 15-day window, request on day 11) — 10% restocking = 49.90 < minimum Rs 100 — `commands.txt line 258`
  - Prepaid vs COD refunds: COD refunds go to wallet instantly, prepaid in 5 business days — holidays.csv lists 2026-10-20 inside the period — `holidays.csv row 2; orders.csv payment_mode`

## What is NOT in this pack

Expected outputs are not provided for this set. Validate your engine with your own test suite against the rules in your brief (BR-01 … BR-nn). A separate hidden input set with the same schema will be used at final evaluation; outputs are compared field-for-field, so follow the column formats above exactly in your own output.

## Output format expected at evaluation

Produce these CSV files (header row, same conventions as above, rows sorted as stated). Where the brief is silent on a format detail the choice below is binding for evaluation.

### `case_files.csv`

One row per PRINT_CASE, in file order.

Columns, in order: `return_id`, `order_id`, `decision`, `final_state`, `grade`, `score`, `routing`, `refund_amount`, `restocking_fee`, `pickup_fee`, `accessory_deduction`, `refund_mode`, `refund_date`, `recovery_amount`, `loss_amount`, `loss_bearer`, `courier_claim`, `wallet_charge`

### `state_log.csv`

One row per state transition or rejected command, in file order.

Columns, in order: `line_no`, `return_id`, `from_state`, `to_state`, `status`, `reason`

### `weekly_report.csv`

One row per routing per WEEKLY_REPORT.

Columns, in order: `week_start`, `week_end`, `routing`, `units`, `price_total`, `recovery_total`, `loss_total`, `courier_claims`, `seller_recovery`, `platform_loss`

Binding choices: `decision` is ACCEPT, REJECT or ACCEPT_WITH_DEDUCTION; `routing` is RESTOCK, REFURB, LIQUIDATE, SCRAP or blank; `loss_bearer` is COURIER, SELLER, PLATFORM or blank; `refund_mode` is SOURCE or WALLET; state_log `status` is OK or ERROR (illegal transition); window days count from the delivery date (delivery day = day 0).
