# PS-049 Decision Log — T072

| ID | Decision / implementation | Reason and status |
|---|---|---|
| DL-01 | Python 3.10+ | Follows Week 1 team design. |
| DL-02 | Dataclasses and enums for domain data | Makes records and allowed values explicit. |
| DL-03 | Central state transition map | One validation point for legal workflow transitions. |
| DL-04 | Refund, recovery, costs and loss allocation stored separately | These amounts represent different business concepts. |
| DL-05 | Timezone-aware ISO-8601 timestamps | Avoids ambiguous local/UTC comparisons. |
| DL-06 | Built-in `unittest` | No third-party dependency. |
| DL-07 | Official teacher-pack CSV data and `commands.txt` are used by the official sample processor; the earlier `commands.json` remains available for the baseline JSON workflow. | Adapted the implementation to the supplied official teacher pack. |
| DL-08 | Return window uses inclusive calendar-day boundary through 23:59:59.999999 on final day | Makes the required day-7 23:59 edge case eligible. Confirm with organiser. |
| DL-09 | Category `ELECTRONICS` uses 7 days, `ACCESSORIES` 15 days, `DEFECTIVE` 30 days; other categories use order policy window | Follows category rules while retaining order policy fallback. Confirm category vocabulary. |
| DL-10 | Three CHANGED_MIND returns includes the current request; 90-day start boundary is inclusive | Implements the specified third-return boundary. Confirm rolling-window convention. |
| DL-11 | Repeat-return 20% fee replaces the normal 10% fee; minimum remains Rs 100; pickup is Rs 99 except DAMAGED_IN_TRANSIT | Explicit operational interpretation of abuse override. Confirm fee precedence. |
| DL-12 | Accessory deduction is capped at 30% of gross refund, after which all deductions are subtracted; net refund cannot be below zero | The brief specifies the cap but not ordering. Confirm exact deduction order. |
| DL-13 | Refund = gross price − restocking fee − pickup fee − accessory deduction | Transparent provisional formula; confirm against available sample data and coordinator clarification. |
| DL-14 | Courier claim = min(price − recovery, declared value, Rs 5,000) | Interprets the stated caps; confirm whether costs enter loss. |
| DL-15 | Seller recovery = max(0, price − recovery) for WRONG_ITEM/DEFECTIVE | Provisional loss formula; confirm with organiser. |
| DL-16 | Platform loss = max(0, price − recovery − restocking fee) for CHANGED_MIND | Implements “net of restocking fee”; confirm treatment of pickup/refurb costs. |
| DL-17 | Prepaid settlement represented as source refund within 5 business days; COD as instant wallet refund | Exact calendar date is not computed in this baseline; weekend/holiday calendar rules need confirmation. |
| DL-18 | Pickup attempts must be on consecutive calendar dates; Sunday counts as a calendar day | Implements “consecutive days” literally; no business-day exclusion. |
| DL-19 | Reopen window starts at second failed pickup timestamp and is inclusive through +3 days | Week 1 proposed this boundary; confirm start point. |
| DL-20 | Grade B requires explicit `qc_passed` value; QC failure routes to LIQUIDATE at 50% recovery | Brief requires QC outcome but does not separately define QC input schema. |
| DL-21 | Same-SKU exchange skips cash refund; C/D wallet adjustment = original price − recovery | Follows exchange rule; negative wallet balance is allowed conceptually. |
| DL-22 | Evidence flags are retained but only DOA evidence presence is optionally checked; business eligibility does not invent photo requirements | Required evidence definitions were not supplied. |

**Status:** The official teacher-pack files have been received and integrated into the implementation. The official sample processor and test suite have been executed successfully, with 34 tests passing. Remaining calculation and workflow assumptions are documented as provisional unless confirmed by the supplied sample data or coordinator clarification. No official expected-output files were supplied for an exact output comparison.
