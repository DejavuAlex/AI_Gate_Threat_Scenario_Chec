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
        task_id=args.task_id,
        task_name=args.task_name,
        repository=args.repo,
        branch=args.branch,
        documents=args.docs,
        gate2_documents=getattr(args, "gate2_docs", None) or [],
        threshold=args.threshold,
        triggered_by=args.triggered_by,
        gate1_report=getattr(args, "gate1_report", None),
        auto_run_gate2_on_gate1_approval=not getattr(args, "disable_auto_gate2", False),
    )
    result = ReviewService().run(gate, request)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    print(f"\nTask: {result.get('task_code')} / {result.get('task_id')}")
    print(f"Activity: {result.get('work_order_id')}")
    print(f"Report generated: {result.get('report_path')}")
    print(f"Report URL: {result.get('report_url')}")
    print(f"Download URL: {result.get('report_download_url')}")
    return 0


def approve(args: argparse.Namespace) -> int:
    result = ReviewService().approve(args.review_id, args.reviewer, args.comment)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    if result.get("auto_gate2_triggered"):
        print("\nGate1 approval auto-triggered Gate2.")
        print(f"Gate2 report: {result['auto_gate2_result'].get('report_path')}")
    return 0


def final_report(args: argparse.Namespace) -> int:
    task = ReviewService().get_task(args.task_id)
    print(json.dumps(task, ensure_ascii=False, indent=2) if args.json else f"Task {task.get('task_code') or task.get('task_id')} final report is available at /api/v1/tasks/{task.get('task_id')}/final-report")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="AI Security Gate CLI")
    sub = parser.add_subparsers(dest="command", required=True)

    for gate in ["gate1", "gate2"]:
        gate_parser = sub.add_parser(gate)
        actions = gate_parser.add_subparsers(dest="action", required=True)
        run = actions.add_parser("run")
        run.add_argument("--project-id", default="demo")
        run.add_argument("--product-name", default="Demo Security Gate Product")
        run.add_argument("--product-version", default="v1.0.0")
        run.add_argument("--task-id", default=None, help="Existing task id or task code. Gate1 creates a new serial task if omitted.")
        run.add_argument("--task-name", default=None)
        run.add_argument("--repo", default="quy7_roche/AI_Security_Gate")
        run.add_argument("--branch", default="main")
        run.add_argument("--docs", nargs="+", required=True)
        run.add_argument("--gate2-docs", nargs="*", default=[])
        run.add_argument("--threshold", type=float, default=0.78)
        run.add_argument("--triggered-by", default="cli")
        run.add_argument("--disable-auto-gate2", action="store_true")
        if gate == "gate2":
            run.add_argument("--gate1-report", default=None)

    approve_parser = sub.add_parser("approve")
    approve_parser.add_argument("--review-id", required=True)
    approve_parser.add_argument("--reviewer", required=True)
    approve_parser.add_argument("--comment", default=None)

    final_parser = sub.add_parser("final-report")
    final_parser.add_argument("--task-id", required=True)
    final_parser.add_argument("--json", action="store_true")

    args = parser.parse_args()
    if args.command in {"gate1", "gate2"} and args.action == "run":
        return run_gate(args.command, args)
    if args.command == "approve":
        return approve(args)
    if args.command == "final-report":
        return final_report(args)
    parser.print_help()
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
