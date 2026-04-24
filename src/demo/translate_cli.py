"""CLI wrapper around `sasy.policy.translate` with a single-line spinner.

The SDK emits one INFO log per poll (every ~15s); a CLI watching that
flow for 5–15 minutes shouldn't leave the user staring at a scrolling
log. This helper holds a single rich-status line that updates in
place: spinner + friendly stage label + mm:ss elapsed counter ticking
every quarter-second, with the raw SDK log lines suppressed.

Stage names from the SDK are internal jargon (``stage1_analyze``,
``stage2_translate``, ``done``); we map them to human strings before
display.

Run via ``make translate`` or directly:
    uv run python -m demo.translate_cli
"""

from __future__ import annotations

import argparse
import logging
import re
import sys
import time
from pathlib import Path
from typing import Callable

from rich.console import Console, ConsoleOptions, RenderResult
from rich.live import Live
from rich.spinner import Spinner

# Friendly text for each stage emitted by the translate service.
# Anything not in this map falls back to the raw stage name verbatim.
_STAGE_LABELS: dict[str, str] = {
    "submitting": "Submitting job",
    "extract_codebase": "Unpacking your codebase",
    "stage1_analyze": "Analyzing your codebase",
    "stage2_translate": "Translating to Datalog",
    "stage3_validate": "Validating Datalog",
    "done": "Finalizing",
}

# Per-poll INFO line shape, e.g.
#   "translate job 80ed9f9c14c7: stage1_analyze (15s)"
_STAGE_RE = re.compile(r":\s*(\w+)\s*\(\d+\.?\d*s\)\s*$")


class _StageCaptureHandler(logging.Handler):
    """Plucks the current stage out of each per-poll INFO line.

    Doesn't print anything itself — the spinner re-renders on its own
    schedule and reads the captured stage on each refresh.
    """

    def __init__(self, on_stage: Callable[[str], None]) -> None:
        super().__init__(level=logging.INFO)
        self._on_stage = on_stage

    def emit(self, record: logging.LogRecord) -> None:
        msg = record.getMessage()
        m = _STAGE_RE.search(msg)
        if m:
            self._on_stage(m.group(1))


class _ElapsedSpinner:
    """Renderable that recomputes elapsed + label on every Live refresh.

    Using a custom renderable (instead of pushing updates from a
    background thread) lets ``Live(refresh_per_second=4)`` drive the
    timer for free — no extra coordination needed.
    """

    def __init__(
        self,
        start: float,
        get_stage: Callable[[], str],
    ) -> None:
        self._start = start
        self._get_stage = get_stage
        self._spinner = Spinner("dots", text="")

    def __rich_console__(
        self, console: Console, options: ConsoleOptions
    ) -> RenderResult:
        elapsed = int(time.monotonic() - self._start)
        mm, ss = divmod(elapsed, 60)
        stage = self._get_stage()
        label = _STAGE_LABELS.get(stage, stage)
        self._spinner.update(text=f"{label}… ({mm:02d}:{ss:02d})")
        yield self._spinner


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Run sasy.policy.translate with a friendly single-line "
            "spinner instead of a scrolling poll log."
        ),
    )
    parser.add_argument(
        "--policy-file",
        type=Path,
        default=Path("policy_english.md"),
        help="Natural-language policy spec (default: policy_english.md)",
    )
    parser.add_argument(
        "--codebase",
        action="append",
        default=None,
        metavar="PATH",
        help=(
            "Codebase directory or file the translator should "
            "analyze (repeatable; default: src/demo)"
        ),
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("output"),
        help="Where to write the generated artifacts (default: output/)",
    )
    parser.add_argument(
        "--base-name",
        default="airline",
        help="Base filename for saved artifacts (default: airline)",
    )
    parser.add_argument(
        "--model",
        default=None,
        choices=["haiku", "sonnet", "opus"],
        help="Override the SDK default model",
    )
    return parser.parse_args()


def main() -> None:
    args = _parse_args()
    codebase_paths = args.codebase or ["src/demo"]

    # Defer the import so the SDK isn't loaded until we know we're
    # really running (keeps `python -m demo.translate_cli --help`
    # snappy and free of side effects).
    from sasy.policy import translate, TranslateError

    if not args.policy_file.exists():
        print(
            f"ERROR: policy spec not found: {args.policy_file}",
            file=sys.stderr,
        )
        sys.exit(1)
    policy_text = args.policy_file.read_text()

    state = {"stage": "submitting"}

    def _on_stage(stage: str) -> None:
        state["stage"] = stage

    handler = _StageCaptureHandler(_on_stage)
    sasy_logger = logging.getLogger("sasy")
    # Capture stage-bearing log lines without echoing them to stderr.
    sasy_logger.addHandler(handler)
    sasy_logger.setLevel(logging.INFO)
    # Don't let other handlers (e.g. an inherited basicConfig
    # StreamHandler) double-print the per-poll lines and ruin the
    # single-line spinner illusion.
    sasy_logger.propagate = False

    console = Console()
    start = time.monotonic()
    extra: dict[str, str] = {}
    translate_kwargs = {"model": args.model} if args.model else {}

    try:
        with Live(
            _ElapsedSpinner(start, lambda: state["stage"]),
            console=console,
            refresh_per_second=4,
            transient=True,
        ):
            result = translate(
                policy_text,
                codebase_paths=codebase_paths,
                **translate_kwargs,
            )
    except TranslateError as exc:
        # Spinner is gone (Live cleaned up); print the friendly error.
        console.print(f"[red]Translate failed:[/red] {exc}")
        sys.exit(2)
    except KeyboardInterrupt:
        console.print("[yellow]Interrupted; the SDK fired DELETE on the job.[/yellow]")
        sys.exit(130)
    finally:
        sasy_logger.removeHandler(handler)

    elapsed = time.monotonic() - start
    mm, ss = divmod(int(elapsed), 60)
    console.print(
        f"[green]✓[/green] Translation done in {mm:02d}:{ss:02d} "
        f"({result.status})"
    )
    if result.cost_usd is not None:
        console.print(f"  Cost: ${result.cost_usd:.2f}")
    if result.validation is not None:
        mark = (
            "[green]OK[/green]"
            if result.validation.ok
            else "[red]FAIL[/red]"
        )
        console.print(f"  Validation: {mark}")

    saved = result.save_all(args.output_dir, base_name=args.base_name)
    console.print()
    if "policy" in saved:
        console.print(
            "Datalog policy (upload to the SASY engine to enforce):"
        )
        console.print(f"  [cyan]{saved['policy']}[/cyan]")
    if "summary" in saved:
        console.print("Summary of your agent's codebase analysis:")
        console.print(f"  [cyan]{saved['summary']}[/cyan]")
    if "functors" in saved:
        console.print(
            "C++ helpers for content matching / date arithmetic:"
        )
        console.print(f"  [cyan]{saved['functors']}[/cyan]")


if __name__ == "__main__":
    main()
