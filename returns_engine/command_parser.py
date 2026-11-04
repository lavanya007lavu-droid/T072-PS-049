
"""Parser for the official PS-049 pipe-separated command file."""

from datetime import datetime, date


COMMAND_ARGUMENTS = {
    "RETURN_REQUEST": 6,
    "SCHEDULE_PICKUP": 3,
    "PICKUP_ATTEMPT": 4,
    "REOPEN": 2,
    "RECEIVE": 2,
    "GRADE": 2,
    "APPROVE": 3,
    "REFURB_QC": 3,
    "WEEKLY_REPORT": 3,
    "PRINT_CASE": 2,
}


def parse_commands(lines: list[str]) -> list[dict]:
    """Parse commands while preserving their original file order."""

    parsed = []

    for line_no, raw_line in enumerate(lines, start=1):
        line = raw_line.strip()

        # Ignore blank lines and comments.
        if not line or line.startswith("#"):
            continue

        parts = [part.strip() for part in line.split("|")]
        command = parts[0].upper()

        if command not in COMMAND_ARGUMENTS:
            raise ValueError(
                f"Line {line_no}: unknown command {command!r}"
            )

        args = parts[1:]
        expected = COMMAND_ARGUMENTS[command]

        if len(args) != expected:
            raise ValueError(
                f"Line {line_no}: {command} expects "
                f"{expected} arguments, received {len(args)}"
            )

        if any(value == "" for value in args):
            raise ValueError(
                f"Line {line_no}: unexpected empty argument in {command}"
            )

        try:
            timestamp = datetime.strptime(
                args[0], "%Y-%m-%d %H:%M:%S"
            )
        except ValueError as exc:
            raise ValueError(
                f"Line {line_no}: invalid command timestamp {args[0]!r}"
            ) from exc

        record = {
            "line_no": line_no,
            "command": command,
            "timestamp": timestamp,
            "args": args,
            "raw": line,
        }

        # Validate command-specific fields.
        if command == "RETURN_REQUEST":
            if args[3] not in {
                "WRONG_ITEM",
                "DAMAGED_IN_TRANSIT",
                "CHANGED_MIND",
                "DEFECTIVE",
            }:
                raise ValueError(
                    f"Line {line_no}: invalid return reason {args[3]!r}"
                )

            if args[4] not in {"REFUND", "EXCHANGE"}:
                raise ValueError(
                    f"Line {line_no}: request type must be REFUND or EXCHANGE"
                )

            if args[5].lower() not in {"true", "false"}:
                raise ValueError(
                    f"Line {line_no}: evidence_provided must be true or false"
                )

        elif command == "SCHEDULE_PICKUP":
            try:
                date.fromisoformat(args[2])
            except ValueError as exc:
                raise ValueError(
                    f"Line {line_no}: invalid pickup date {args[2]!r}"
                ) from exc

        elif command == "PICKUP_ATTEMPT":
            if args[2] not in {"1", "2"}:
                raise ValueError(
                    f"Line {line_no}: pickup attempt must be 1 or 2"
                )
            if args[3] not in {"SUCCESS", "FAILED"}:
                raise ValueError(
                    f"Line {line_no}: invalid pickup result {args[3]!r}"
                )

        elif command == "REFURB_QC":
            if args[2] not in {"PASS", "FAIL"}:
                raise ValueError(
                    f"Line {line_no}: QC result must be PASS or FAIL"
                )

        elif command == "WEEKLY_REPORT":
            try:
                start = date.fromisoformat(args[1])
                end = date.fromisoformat(args[2])
            except ValueError as exc:
                raise ValueError(
                    f"Line {line_no}: invalid weekly report date"
                ) from exc

            if start > end:
                raise ValueError(
                    f"Line {line_no}: week_start cannot be after week_end"
                )

        parsed.append(record)

    return parsed
