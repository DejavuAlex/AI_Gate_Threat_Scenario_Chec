#!/usr/bin/env python3
import argparse
import json
from pathlib import Path
import sys

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from backend.app.schemas import ReviewRunRequest
from backend.app.services.review import ReviewService


def run_gate(gate: str, args: argparse.Namespace) -> int:
    request = ReviewRunRequest(
        project_id=args.project_id,
        product_name=args.product_name,
        product_version=args.product_version,
        task_id=None,
        task_name=None,
        repository=args.repo,
        branch=args.branch,
        documents=args.docs,
        gate2_documents=[],
        threshold=args.threshold,
        triggered_by="cli-local",
        gate1_report=getattr(args, "gate1_report", None),
        auto_run_gate2_on_gate1_approval=False,
    )
    result = ReviewService().run_local_agent(gate, request)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "AI Security Gate local CLI agents. Gate1 and Gate2 run independently, "
            "do not require API keys, do not create Review Tasks, and do not persist reports."
        )
    )
    sub = parser.add_subparsers(dest="command", required=True)

    for gate in ["gate1", "gate2"]:
        gate_parser = sub.add_parser(gate, help=f"Run {gate} as a local one-shot review agent")
        actions = gate_parser.add_subparsers(dest="action", required=True)
        run = actions.add_parser("run", help=f"Run {gate} locally and print the single review result")
        run.add_argument("--project-id", default="demo")
        run.add_argument("--product-name", default="Demo Security Gate Product")
        run.add_argument("--product-version", default="v1.0.0")
        run.add_argument("--repo", default="quy7_roche/AI_Security_Gate")
        run.add_argument("--branch", default="main")
        run.add_argument("--docs", nargs="+", required=True)
        run.add_argument("--threshold", type=float, default=0.78)
        if gate == "gate2":
            run.add_argument("--gate1-report", default=None, help="Optional local Gate1 report file for Gate2 control verification")

    args = parser.parse_args()
    if args.command in {"gate1", "gate2"} and args.action == "run":
        return run_gate(args.command, args)
    parser.print_help()
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
