#!/usr/bin/env python3
"""Translate the tau2 airline policy via the sasy-translate cloud service.

Modes:
  single      One translation from the original spec.
  variance    N translations from the original + N from paraphrases,
              saved under output/original_{i}/ and output/paraphrase_{i}/.

Uses the `sasy` Python SDK (`sasy.policy.translate`) to talk to
the cloud endpoint at SASY_TRANSLATE_URL (default https://sasy-translate.fly.dev).

Usage:
    # Single translation
    uv run python benchmarks/tau2-airline/run.py single

    # N original + N paraphrased (for variance measurement)
    uv run python benchmarks/tau2-airline/run.py variance --n 3

    # Against a local translator
    SASY_TRANSLATE_URL=http://127.0.0.1:8081 uv run python ... single
"""

from __future__ import annotations

import argparse
import concurrent.futures
import json
import logging
import os
import sys
import time
from pathlib import Path

from sasy.policy import translate

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("bench")

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
SPEC_FILE = REPO_ROOT / "benchmarks" / "tau2-airline" / "spec.md"
OUTPUT_DIR = REPO_ROOT / "benchmarks" / "tau2-airline" / "output"

# Key instructions that reliably produce good translations for this agent.
# These are the minimum the skill needs to know.
INSTRUCTIONS = """\
You are enforcing the policy on LLMAgent (the tau2 airline agent).

Two baseline constraints:

1. User messages in the dependency chain have msg.agent = "LLMAgent" and
   msg.agent_role = $UserRole(). All SentMessage rules matching user
   messages MUST filter on both.

2. Use custom C++ functors for content checks (keyword/phrase matching),
   not @llm_check_fn.
"""

CODEBASE_PATHS = [
    "tau2-bench/src/tau2",
]


def _codebase_paths_from_repo() -> tuple[list[str], Path]:
    """Resolve codebase paths; fall back gracefully if the demo layout
    doesn't have them at the repo root (used from the sasy main repo)."""
    here = REPO_ROOT
    candidates = [here, here / "examples"]
    for root in candidates:
        resolved = [root / p for p in CODEBASE_PATHS]
        if all(p.exists() for p in resolved):
            return [str(p) for p in resolved], root
    # As a fallback, just pass what we have
    return [str(here / p) for p in CODEBASE_PATHS], here


def translate_once(spec_text: str, label: str, *, model: str) -> Path:
    """Run one translation, save artifacts under output/<label>/."""
    paths, root = _codebase_paths_from_repo()
    log.info("[%s] translating (model=%s, %d codebase paths)...", label, model, len(paths))
    t0 = time.monotonic()

    result = translate(
        spec_text,
        codebase_paths=paths,
        codebase_root=str(root),
        instructions=INSTRUCTIONS,
        model=model,
        on_progress=lambda stage, elapsed: log.info(
            "[%s] stage=%s elapsed=%.0fs", label, stage, elapsed
        ),
    )

    out = OUTPUT_DIR / label
    out.mkdir(parents=True, exist_ok=True)
    result.save_all(out, base_name="airline")

    # Persist per-run metadata
    (out / "meta.json").write_text(
        json.dumps(
            {
                "label": label,
                "status": result.status,
                "model": model,
                "duration_seconds": result.duration_seconds,
                "cost_usd": result.cost_usd,
                "errors": result.errors,
                "wall_clock_seconds": time.monotonic() - t0,
            },
            indent=2,
        )
    )
    log.info("[%s] %s — saved to %s", label, result.status.upper(), out)
    if result.errors:
        for e in result.errors:
            log.warning("[%s] %s", label, e)
    return out


def paraphrase_spec(spec_text: str, n: int, model: str) -> list[str]:
    """Ask the translator service for N paraphrased versions of the spec.

    We reuse translate's model access by sending a degenerate
    instruction — but that would also trigger a Datalog translation.
    Simpler: just call the LLM via the same sasy-write service if it's
    available; otherwise fall back to just duplicating the original spec.

    For the demo, we ship 3 pre-computed paraphrases alongside the spec.
    This function reads them from disk if present, or falls back to dup.
    """
    para_dir = SPEC_FILE.parent / "paraphrases"
    if para_dir.exists():
        files = sorted(para_dir.glob("spec_paraphrase_*.md"))[:n]
        if files:
            return [f.read_text() for f in files]
    log.warning(
        "No paraphrases in %s; using the original spec %d times "
        "(variance will reflect only model nondeterminism)",
        para_dir,
        n,
    )
    return [spec_text] * n


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("mode", choices=["single", "variance"])
    ap.add_argument("--n", type=int, default=3, help="N for variance mode")
    ap.add_argument("--model", default="sonnet", choices=["haiku", "sonnet", "opus"])
    ap.add_argument("--parallel", type=int, default=4, help="concurrent translations")
    args = ap.parse_args()

    if not SPEC_FILE.exists():
        log.error("Missing %s", SPEC_FILE)
        return 1

    spec = SPEC_FILE.read_text()
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    if args.mode == "single":
        translate_once(spec, "single", model=args.model)
        return 0

    # variance mode: N original + N paraphrased in parallel
    paraphrases = paraphrase_spec(spec, args.n, args.model)
    jobs: list[tuple[str, str]] = []
    for i in range(1, args.n + 1):
        jobs.append((f"original_{i}", spec))
    for i, p in enumerate(paraphrases, start=1):
        jobs.append((f"paraphrase_{i}", p))

    log.info("Launching %d translations in parallel (concurrency=%d)", len(jobs), args.parallel)
    with concurrent.futures.ThreadPoolExecutor(max_workers=args.parallel) as pool:
        futures = {
            pool.submit(translate_once, text, label, model=args.model): label
            for label, text in jobs
        }
        for fut in concurrent.futures.as_completed(futures):
            label = futures[fut]
            try:
                fut.result()
            except Exception as e:  # noqa: BLE001
                log.error("[%s] failed: %s", label, e)

    log.info("Done. Results under %s", OUTPUT_DIR)
    return 0


if __name__ == "__main__":
    sys.exit(main())
