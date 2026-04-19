#!/usr/bin/env python3
"""Run tau2 airline benchmark against one or more uploaded policies.

For each policy in --policies, uploads it to the SASY cloud endpoint
(via the gRPC admin API), then runs tau2-instrumented on a fixed set
of airline tasks. Collects the simulation JSON into results/<label>/.

Assumes you're pointed at a running SASY deployment (cloud or local):
  SASY_URL              default: sasy.fly.dev:443
  SASY_API_KEY_SUFFIX   required for cloud auth

Usage:
    # Evaluate the hand-tuned reference policy
    uv run python benchmarks/tau2-airline/run_tau2.py \\
        --policy tau2-examples/airline/airline_policy.dl \\
        --label reference

    # Evaluate all the variance translations
    uv run python benchmarks/tau2-airline/run_tau2.py \\
        --policy-glob 'benchmarks/tau2-airline/output/*/airline_policy.dl'

    # Subset of tasks
    uv run python benchmarks/tau2-airline/run_tau2.py \\
        --policy <path> --tasks 36 43 47 48 49 --trials 2
"""

from __future__ import annotations

import argparse
import glob
import json
import logging
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

from dotenv import load_dotenv

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
RESULTS_DIR = REPO_ROOT / "benchmarks" / "tau2-airline" / "results"
TAU2_SIMS_DIR = REPO_ROOT / "tau2-bench" / "data" / "simulations"

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("tau2-runner")


def configure_sasy() -> None:
    """Configure the sasy SDK from env (.env)."""
    load_dotenv(REPO_ROOT / ".env")
    from sasy.auth.hooks import APIKeyAuthHook
    from sasy.config import configure

    api_key = os.environ.get("SASY_API_KEY", "")
    if not api_key:
        sfx = os.environ.get("SASY_API_KEY_SUFFIX", "")
        api_key = f"demo-key-{sfx}" if sfx else ""
    sasy_url = os.environ.get("SASY_URL", "sasy.fly.dev:443")

    configure(
        url=sasy_url,
        ca_path=None,
        cert_path=None,
        key_path=None,
        auth_hook=APIKeyAuthHook(api_key=api_key),
    )
    log.info("sasy configured: url=%s key=%s", sasy_url, "set" if api_key else "none")


def upload_policy(policy_path: Path, functors_path: Path | None = None) -> None:
    """Upload a policy (and optional companion functors) to the running SASY."""
    from sasy.policy import upload_policy_file

    log.info("uploading %s", policy_path)
    resp = upload_policy_file(str(policy_path), hot_reload=True)
    if not resp.accepted:
        raise RuntimeError(f"policy upload rejected: {resp.error_output or resp.message}")
    log.info("policy accepted: %s", resp.message)


def run_tau2(task_ids: list[int], trials: int, concurrency: int, agent_llm: str, user_llm: str) -> Path | None:
    """Run tau2-instrumented and return the path of the produced simulation JSON."""
    log.info("running tau2 (tasks=%s, trials=%d)", task_ids, trials)
    # Snapshot existing sims so we can pick the new one afterward
    prev = set(TAU2_SIMS_DIR.glob("*.json")) if TAU2_SIMS_DIR.exists() else set()

    env = os.environ.copy()
    cmd = [
        "uv", "run", "tau2-instrumented", "run",
        "--domain", "airline",
        "--task-ids", *map(str, task_ids),
        "--num-trials", str(trials),
        "--agent-llm", agent_llm,
        "--user-llm", user_llm,
        "--max-concurrency", str(concurrency),
    ]
    result = subprocess.run(cmd, env=env, check=False)
    if result.returncode != 0:
        log.warning("tau2 exited with non-zero code %d (continuing)", result.returncode)

    # Find the new sim file
    current = set(TAU2_SIMS_DIR.glob("*.json"))
    new = sorted(current - prev, key=lambda p: p.stat().st_mtime)
    if not new:
        log.error("no new simulation file produced")
        return None
    return new[-1]


def eval_one(policy_path: Path, label: str, task_ids: list[int], trials: int, concurrency: int,
             agent_llm: str, user_llm: str) -> dict:
    result_dir = RESULTS_DIR / label
    result_dir.mkdir(parents=True, exist_ok=True)

    upload_policy(policy_path)

    sim_file = run_tau2(task_ids, trials, concurrency, agent_llm, user_llm)
    if sim_file is None:
        (result_dir / "status.txt").write_text("no_results")
        return {"label": label, "status": "failure"}
    shutil.copy(sim_file, result_dir / "tau2_results.json")
    return summarize(sim_file, label, task_ids, trials)


def summarize(sim_file: Path, label: str, task_ids: list[int], trials: int) -> dict:
    data = json.loads(sim_file.read_text())
    by_task: dict[str, list[float]] = {}
    for sim in data.get("simulations", []):
        tid = str(sim.get("task_id"))
        by_task.setdefault(tid, []).append(float(sim.get("reward_info", {}).get("reward", 0.0)))

    summary = {
        "label": label,
        "per_task": {
            tid: {
                "passes": sum(1 for r in rs if r >= 1.0),
                "total": len(rs),
                "mean": sum(rs) / len(rs) if rs else 0.0,
            }
            for tid, rs in by_task.items()
        },
        "overall": sum(sum(rs) for rs in by_task.values()) / max(1, sum(len(rs) for rs in by_task.values())),
    }
    log.info("[%s] overall=%.3f per_task=%s", label, summary["overall"],
             {t: f"{v['passes']}/{v['total']}" for t, v in summary["per_task"].items()})
    return summary


def main() -> int:
    ap = argparse.ArgumentParser()
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--policy", help="single policy file to evaluate")
    g.add_argument("--policy-glob", help="glob of policy files (each in a dir named as its label)")
    ap.add_argument("--label", help="label (dir name under results/) when --policy is given")
    ap.add_argument("--tasks", type=int, nargs="+", default=[36, 43, 47, 48, 49])
    ap.add_argument("--trials", type=int, default=2)
    ap.add_argument("--concurrency", type=int, default=10)
    ap.add_argument("--agent-llm", default=os.environ.get("AGENT_LLM", "vertex_ai/claude-opus-4-5@20251101"))
    ap.add_argument("--user-llm", default=os.environ.get("USER_LLM", "vertex_ai/claude-opus-4-5@20251101"))
    args = ap.parse_args()

    configure_sasy()

    policies: list[tuple[Path, str]] = []
    if args.policy:
        policies.append((Path(args.policy), args.label or "single"))
    else:
        for p in sorted(glob.glob(args.policy_glob)):
            path = Path(p)
            label = path.parent.name
            policies.append((path, label))

    if not policies:
        log.error("no policies matched")
        return 1

    log.info("evaluating %d policies: %s", len(policies), [l for _, l in policies])
    summaries = []
    for path, label in policies:
        try:
            summaries.append(eval_one(path, label, args.tasks, args.trials, args.concurrency,
                                      args.agent_llm, args.user_llm))
        except Exception as e:  # noqa: BLE001
            log.error("[%s] failed: %s", label, e)

    # Top-level summary
    all_summary_path = RESULTS_DIR / "_summary" / "combined.json"
    all_summary_path.parent.mkdir(parents=True, exist_ok=True)
    all_summary_path.write_text(json.dumps({"policies": summaries}, indent=2))
    log.info("summary written to %s", all_summary_path)
    return 0


if __name__ == "__main__":
    sys.exit(main())
