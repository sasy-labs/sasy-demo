"""Narrated terminal output for the demo.

Shows a clean, stage-by-stage view of the agent loop
with policy enforcement highlighted. Uses raw ANSI
escapes (no external deps).

When STEP_MODE is True, pauses between stages within
each scenario for interactive walkthrough.
"""

from __future__ import annotations

import json
import os
import textwrap
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from demo.scenarios import Scenario

# ── Configuration ────────────────────────────────────

STEP_MODE = os.environ.get("STEP_MODE", "") == "1"

# ── ANSI escape helpers ─────────────────────────────

_RESET = "\033[0m"
_BOLD = "\033[1m"
_DIM = "\033[2m"
_RED = "\033[31m"
_GREEN = "\033[32m"
_YELLOW = "\033[33m"
_BLUE = "\033[34m"
_CYAN = "\033[36m"
_WHITE = "\033[37m"


def _pause() -> None:
    """Pause for Enter if step mode is on."""
    if STEP_MODE:
        input(
            f"{_DIM}  Press Enter to continue..."
            f"{_RESET}"
        )


def _wrap(text: str, prefix: str = "") -> str:
    """Wrap text to 60 chars with indent."""
    lines = textwrap.wrap(text, width=58)
    if not lines:
        return ""
    first = lines[0]
    rest = textwrap.indent(
        "\n".join(lines[1:]),
        " " * len(prefix),
    )
    return f"{first}\n{rest}" if rest.strip() else first


# ── Scenario header / footer ────────────────────────


def display_scenario_header(
    scenario: Scenario,
) -> None:
    """Print a bold banner with scenario info."""
    width = 60
    border = "=" * width
    print(f"\n{_BOLD}{border}{_RESET}")
    print(
        f"{_BOLD}Scenario {scenario.id}: "
        f"{scenario.title}{_RESET}"
    )
    print(f"{_BOLD}{border}{_RESET}")
    print(f"{scenario.description}")
    expected = (
        scenario.expected_denial
        if scenario.expected_denial
        else "ALLOWED"
    )
    print(
        f"{_DIM}Policy: {scenario.policy_note}{_RESET}"
    )
    print(f"{_DIM}Expected: {expected}{_RESET}\n")
    _pause()


def display_summary(
    scenario: Scenario,
    denied: bool,
) -> None:
    """Print a scenario result summary."""
    width = 60
    print(f"\n{_BOLD}{'─' * width}{_RESET}")
    print(f"{_BOLD}Summary: {scenario.title}{_RESET}")

    if scenario.expected_denial is not None:
        if denied:
            print(
                f"{_GREEN}{_BOLD}"
                f"  PASS - policy correctly denied "
                f"{scenario.expected_denial}"
                f"{_RESET}"
            )
        else:
            print(
                f"{_RED}{_BOLD}"
                f"  FAIL - expected denial of "
                f"{scenario.expected_denial} "
                f"but it was allowed"
                f"{_RESET}"
            )
    else:
        if not denied:
            print(
                f"{_GREEN}{_BOLD}"
                f"  PASS - policy correctly allowed "
                f"the request"
                f"{_RESET}"
            )
        else:
            print(
                f"{_RED}{_BOLD}"
                f"  FAIL - expected request to be "
                f"allowed but it was denied"
                f"{_RESET}"
            )
    print(f"{_BOLD}{'─' * width}{_RESET}\n")


# ── Messages ────────────────────────────────────────


def display_user(text: str) -> None:
    """Print a customer message."""
    prefix = "[Customer] "
    print(
        f"\n{_GREEN}{prefix}{_wrap(text, prefix)}"
        f"{_RESET}"
    )
    _pause()


def display_agent(text: str) -> None:
    """Print an agent response."""
    prefix = "[Agent]    "
    print(
        f"\n{_CYAN}{prefix}{_wrap(text, prefix)}"
        f"{_RESET}"
    )
    _pause()


# ── Tool calls ──────────────────────────────────────


def _summarize_args(
    fn_name: str,
    args: dict | str | None,
) -> str:
    """One-line summary of tool call args."""
    if not args:
        return ""
    if isinstance(args, str):
        try:
            args = json.loads(args)
        except json.JSONDecodeError:
            return args[:60]
    if not isinstance(args, dict):
        return str(args)[:60]

    # Show key fields concisely
    parts = []
    for k, v in args.items():
        if isinstance(v, str) and len(v) < 30:
            parts.append(f"{k}={v}")
        elif isinstance(v, (int, float, bool)):
            parts.append(f"{k}={v}")
    return ", ".join(parts) if parts else ""


def display_tool_call(
    fn_name: str,
    args: dict | str | None = None,
) -> None:
    """Print a concise tool call."""
    summary = _summarize_args(fn_name, args)
    call_str = (
        f"{fn_name}({summary})"
        if summary
        else f"{fn_name}()"
    )
    print(
        f"\n{_YELLOW}  → {call_str}{_RESET}"
    )
    print(
        f"{_DIM}    [SASY] Consulting policy engine..."
        f"{_RESET}"
    )


def display_tool_result(content: str) -> None:
    """Print a concise tool result summary."""
    try:
        data = json.loads(content)
        if isinstance(data, dict):
            # Show key fields only
            skip = {
                "payment_history", "flights",
                "passengers", "created_at",
            }
            parts = []
            for k, v in data.items():
                if k in skip:
                    continue
                if isinstance(v, (str, int, float)):
                    parts.append(f"{k}: {v}")
                elif isinstance(v, list):
                    parts.append(f"{k}: [{len(v)} items]")
            summary = " | ".join(parts[:6])
            print(
                f"{_DIM}    Result: {summary}{_RESET}"
            )
            return
    except (json.JSONDecodeError, TypeError):
        pass
    # Fallback: truncate
    short = content[:80] + ("..." if len(content) > 80 else "")
    print(f"{_DIM}    Result: {short}{_RESET}")


# ── Policy decisions ────────────────────────────────


def display_policy_allowed(fn_name: str) -> None:
    """Print a green AUTHORIZED verdict."""
    print(
        f"{_GREEN}{_BOLD}"
        f"    [SASY] ✓ AUTHORIZED: {fn_name}"
        f"{_RESET}"
    )
    _pause()


def display_policy_denied(
    fn_name: str,
    reason: str,
    suggestions: list[str] | None = None,
) -> None:
    """Print a red DENIED verdict with explanation."""
    print(
        f"{_RED}{_BOLD}"
        f"    [SASY] ✗ DENIED: {fn_name}"
        f"{_RESET}"
    )
    print(f"{_RED}    Reason: {reason}{_RESET}")
    if suggestions:
        for s in suggestions:
            print(f"{_RED}    → {s}{_RESET}")
    _pause()
