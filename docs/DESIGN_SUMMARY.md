# PS-049 — Week 2 Design Summary

## Architecture

`models.py` defines the domain entities and enumerations. `validation.py` parses and validates incoming order data and timestamps. `eligibility.py` makes the return decision. `state_machine.py` is the single source of truth for allowed state changes. `engine.py` orchestrates the case lifecycle. `grading.py` computes condition scores, grade, route and recovery. `refunds.py` calculates deductions, settlement and loss allocation. `reports.py` builds case and weekly reports. `cli.py` reads a JSON command file and writes a JSON report.

## Main happy path

`RETURN` creates a REQUESTED case. Eligible cases become APPROVED then PICKUP_SCHEDULED. A successful `PICKUP` moves to PICKED. `RECEIVE` verifies the serial, records RECEIVED, computes score and grade, then routes the unit. Grade A becomes RESTOCKED; grade B becomes REFURB_IN_PROGRESS and then RESOLD or LIQUIDATED according to QC; grade C becomes LIQUIDATED; grade D becomes SCRAPPED. Refund and loss records are calculated independently of product recovery.

## Special paths

- Ineligible return: REJECTED.
- Serial mismatch: FRAUD_REVIEW and no refund.
- Two failed pickup attempts: CUSTOMER_UNAVAILABLE; no refund. One reopen is allowed within three days.
- Grade C/D: refund waits for manager approval.
- Exchange: replacement is marked shipped on successful pickup; no cash refund; C/D creates wallet adjustment.

## State safety

`transition()` checks the current state against `ALLOWED`. If a transition is not listed, it raises `ValueError` without changing the case. Terminal states have no outgoing ordinary transitions. Reopening is handled by a dedicated method that checks the one-time limit and time window.

## Validation strategy

The input layer rejects missing order fields, malformed or timezone-naive timestamps, negative amounts, invalid payment types and unknown enums. The engine rejects unknown order/case IDs, duplicate case IDs, invalid pickup outcomes, excess attempts, non-consecutive attempts, invalid reopen requests and illegal transitions. The test suite covers key boundaries and business scenarios.
