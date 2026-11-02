"""JSON command-file entry point. Run: python -m returns_engine.cli sample_data/commands.json"""
import json, sys
from pathlib import Path
from .validation import load_order
from .engine import ReturnEngine
from .reports import case_report, weekly_report

def run_file(path: str) -> dict:
    command_path = Path(path)
    data = json.loads(command_path.read_text(encoding="utf-8"))
    orders = {o.order_id: o for o in [load_order(raw) for raw in data.get("orders", [])]}
    if len(orders) != len(data.get("orders", [])): raise ValueError("Duplicate order_id in input")
    engine = ReturnEngine(orders)
    for command in data.get("commands", []):
        op = command.get("op", "").upper()
        if op == "RETURN": engine.request_return(command)
        elif op == "PICKUP": engine.pickup_attempt(command["case_id"], command["attempted_at"], command["outcome"])
        elif op == "REOPEN": engine.reopen(command["case_id"], command["reopened_at"])
        elif op == "RECEIVE": engine.receive_and_grade(command["case_id"], command["receipt"])
        elif op == "MANAGER_APPROVE": engine.manager_approve(command["case_id"], command["approved_at"])
        else: raise ValueError(f"Unknown command: {op}")
    return {"cases": [case_report(c) for c in engine.cases.values()], "weekly_report": weekly_report(list(engine.cases.values()))}

def main():
    if len(sys.argv) != 2:
        print("Usage: python -m returns_engine.cli <commands.json>"); raise SystemExit(2)
    result = run_file(sys.argv[1])
    output = json.dumps(result, indent=2, ensure_ascii=False)
    out_path = Path("output")
    out_path.mkdir(exist_ok=True)
    (out_path / "report.json").write_text(output, encoding="utf-8")
    print(output)
    print("\nSaved: output/report.json")

if __name__ == "__main__": main()
