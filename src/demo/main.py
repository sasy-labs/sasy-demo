"""Entry point for the SASY airline demo.

Uploads a Datalog policy to the SASY cloud service, then
runs one or more curated scenarios that exercise the
reference monitor.
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

# Load .env from the demo root (two levels up from this file)
_demo_root = Path(__file__).resolve().parent.parent.parent
load_dotenv(_demo_root / ".env")

from .agent import run_scenario
from .config import OPENAI_MODEL
from .data_model import FlightDB
from .scenarios import get_scenario, get_scenarios
from .tool_schema import as_tool
from .tools import AirlineTools


def _parse_args() -> argparse.Namespace:
    """Build and parse CLI arguments.

    Returns:
        Parsed ``argparse.Namespace``.
    """
    parser = argparse.ArgumentParser(
        description="SASY airline policy demo",
    )
    group = parser.add_mutually_exclusive_group()
    group.add_argument(
        "--all",
        action="store_true",
        help="Run all scenarios",
    )
    group.add_argument(
        "--scenario",
        type=int,
        metavar="N",
        help="Run scenario N (1-5)",
    )
    parser.add_argument(
        "--upload-only",
        action="store_true",
        help="Upload policy and exit",
    )
    parser.add_argument(
        "--skip-upload",
        action="store_true",
        help="Skip policy upload (use already-uploaded policy)",
    )
    parser.add_argument(
        "--policy-file",
        type=Path,
        default=None,
        metavar="PATH",
        help=(
            "Path to the .dl policy to upload "
            "(default: <repo>/policy.dl). Useful for running "
            "scenarios against a translated or alternate policy "
            "without mutating the tracked reference file."
        ),
    )
    parser.add_argument(
        "--model",
        default=OPENAI_MODEL,
        help=f"OpenAI model (default: {OPENAI_MODEL})",
    )
    parser.add_argument(
        "--step",
        action="store_true",
        help="Interactive mode: pause between stages",
    )
    return parser.parse_args()


def main() -> None:
    """Run the demo CLI."""
    args = _parse_args()

    if args.step:
        os.environ["STEP_MODE"] = "1"

    # ── Validate environment ─────────────────────────
    if not os.environ.get("OPENAI_API_KEY"):
        print(
            "ERROR: OPENAI_API_KEY is not set.\n"
            "Add it to your .env file:\n"
            "  OPENAI_API_KEY=sk-..."
        )
        sys.exit(1)

    if not os.environ.get("SASY_API_KEY"):
        print(
            "ERROR: SASY_API_KEY is not set.\n"
            "Add it to your .env file:\n"
            "  SASY_API_KEY=demo-key-..."
        )
        sys.exit(1)

    # The sasy SDK picks up SASY_URL and SASY_API_KEY
    # from the env automatically.

    # ── Upload policy ────────────────────────────────
    if not args.skip_upload:
        from sasy.policy import upload_policy_file

        repo_root = Path(__file__).parent.parent.parent
        policy_path = (
            args.policy_file
            if args.policy_file is not None
            else repo_root / "policy.dl"
        )
        if not policy_path.exists():
            print(
                f"ERROR: policy file not found: {policy_path}"
            )
            sys.exit(1)
        print(f"Uploading policy from {policy_path} ...")
        try:
            resp = upload_policy_file(policy_path)
            if resp.accepted:
                print(
                    f"Policy uploaded: {resp.message}"
                )
            else:
                print(
                    f"Policy upload failed: "
                    f"{resp.message}"
                )
                if resp.error_output:
                    print(resp.error_output)
                sys.exit(1)
        except Exception as exc:
            print(f"Policy upload error: {exc}")
            sys.exit(1)

        if args.upload_only:
            return
    else:
        print("Skipping policy upload (--skip-upload)")

    # ── Load data ────────────────────────────────────
    data_dir = Path(__file__).parent.parent.parent / "data"
    db = FlightDB.load(data_dir / "db.json")

    # ── Build tools ──────────────────────────────────
    airline_tools = AirlineTools(db)
    openai_tools: list[dict[str, Any]] = [
        as_tool(method).openai_schema
        for method in (
            airline_tools.get_tool_methods().values()
        )
    ]

    # ── Select scenarios ─────────────────────────────
    if args.all:
        scenarios = get_scenarios()
    elif args.scenario is not None:
        scenarios = [get_scenario(args.scenario)]
    else:
        scenarios = [get_scenario(1)]

    # ── Run scenarios and collect results ─────────────
    all_results: list[
        tuple[str, list[tuple[str, bool]]]
    ] = []
    for scenario in scenarios:
        results = run_scenario(
            scenario=scenario,
            airline_tools=airline_tools,
            openai_tools=openai_tools,
            model=args.model,
        )
        all_results.append((scenario.title, results))

    # ── Final summary ────────────────────────────────
    print("\n" + "=" * 60)
    print("DEMO SUMMARY")
    print("=" * 60)
    for title, results in all_results:
        print(f"\n  {title}")
        if not results:
            print("    (no tool calls)")
            continue
        for fn_name, authorized in results:
            status = (
                "ALLOWED" if authorized else "DENIED"
            )
            print(f"    {fn_name}: {status}")
    print()


if __name__ == "__main__":
    main()
