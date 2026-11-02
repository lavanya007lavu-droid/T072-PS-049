# T072 – PS-049 Returns and Reverse Logistics Grading Engine

**Language:** Python 3.10+  
**Mode:** Command-file-driven backend (JSON input; no UI)  
**Team:** T072 — Lavanya V and Likith U

## 1. Project status and scope

This is a Week 2 working baseline built from the supplied PS-049 brief and the team's Week 1 design. It implements the core return workflow, grading/routing, refund/loss calculations, command-file processing, reports and automated tests. The organiser's official sample files and visible expected outputs were not included in the material supplied so far. Therefore, the JSON schema in `sample_data/commands.json` is a documented local development format, not a claim about the organiser's final schema. Reconcile it with the official files when they arrive.

## 2. Requirements implemented

- Load and validate order records.
- Accept/reject return requests for WRONG_ITEM, DAMAGED_IN_TRANSIT, CHANGED_MIND and DEFECTIVE.
- Apply NO_RETURN exclusions and category-specific windows.
- Record pickup attempts, retry on the next calendar day, close after two failures and allow one reopen within three days.
- Verify serial number at receipt; mismatch enters FRAUD_REVIEW with no refund.
- Calculate grade score and A/B/C/D mapping; route to RESTOCK, REFURB/RESOLD, LIQUIDATE or SCRAP.
- Apply refurb QC failure fallback to LIQUIDATE.
- Calculate refund deductions, approval status and settlement type.
- Allocate loss to seller, courier or platform; cap courier claim.
- Handle same-SKU exchange flow and C/D wallet adjustment.
- Enforce state transitions and produce case/weekly reports.
- Unit tests for principal rules and listed edge cases.

## 3. Run it

Requires Python 3.10 or later. No third-party packages are required.

```bash
python --version
python -m unittest discover -s tests -v
python -m returns_engine.cli sample_data/commands.json
```

The CLI prints the result and writes `output/report.json`.

Run from this project folder. On Windows, use `py -3.10` in place of `python` if needed.

## 4. Input command format

The top-level JSON object has `orders` and `commands` arrays. Supported `op` values:

- `RETURN`: `case_id`, `order_id`, `reason`, `requested_at`, optional `customer_id`, `evidence_flags`, `is_exchange`, `replacement_sku`.
- `PICKUP`: `case_id`, `attempted_at`, `outcome` (`SUCCESS` or `FAILED`).
- `REOPEN`: `case_id`, `reopened_at`.
- `RECEIVE`: `case_id`, `receipt` object. Receipt includes `received_at`, `returned_serial`, inspection flags, `missing_accessory_values`, `defect_confirmed`; grade B also requires `qc_passed`.
- `MANAGER_APPROVE`: `case_id`, `approved_at`.

All timestamps must be ISO-8601 and include a timezone offset. See `sample_data/commands.json`.

## 5. Important calculation rules

- Score = 100 − min(10 × scratches, 30) − 40 (functional fault) − 10 (box missing) − 15 (seal broken) − 20 (usage detected).
- Grade A ≥ 90; B 70–89; C 50–69; D < 50.
- A: 100% price recovery; B: 85% resale value and Rs 500 + 5% refurbishment cost if QC passes; B QC failure: liquidate at 50%; C: liquidate at 50%; D: Rs 0 recovery and Rs 50 disposal cost.
- Accessory deduction is capped at 30% of gross refund.
- Courier claim = min(price paid − recovery value, declared value, Rs 5,000).

## 6. Decisions and assumptions pending organiser confirmation

See `docs/DECISION_LOG.md`. These assumptions are explicit because the supplied brief does not specify every calculation boundary/formula. Do not silently treat them as confirmed organiser policy. The visible expected output and official sample schema must take precedence when provided.

## 7. Viva preparation

Be able to explain:
1. Why score 55 maps to grade C and LIQUIDATE.
2. Why a serial mismatch prevents refund.
3. Why grade C/D refunds wait for manager approval.
4. Why state transitions are centralized and illegal transitions raise errors.
5. Difference between customer refund, product recovery, seller recovery, courier claim and platform loss.

## 8. Submission reminder

The organiser requires a repository named `T072-PS-049`, README, design document PDF, test suite, decision log and a five-minute demo video link for final submission. This local folder is not yet a Git repository and no official sample-output comparison has been performed. The organiser's email says to reply on the same email thread for queries.
