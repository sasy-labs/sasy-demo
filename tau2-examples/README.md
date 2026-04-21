# Tau2 examples

Tau2-instrumented wrappers around the [tau2-bench](../tau2-bench/)
airline domain, plus the hand-tuned reference policy used by the
[benchmark page](../benchmarks/tau2-airline/).

## Contents

- `airline/airline_policy.dl` — Soufflé Datalog policy enforcing the
  tau2 airline rules (cancellation / modification / confirmation /
  content checks via custom functors).
- `airline/airline_functors.cpp` — C++ functor implementations (keyword
  and phrase matchers) referenced by the policy.
- `tau2_examples/cli.py` — drop-in `tau2-instrumented` CLI that runs
  tau2 against the `sasy.fly.dev` cloud endpoint, reusing your
  `SASY_API_KEY` from `.env`.
- `tau2_examples/cli_llm_policy.py` — research baseline
  (`tau2-instrumented-llm-judge`) that swaps the Datalog policy check
  for an LLM judge. Used to produce the LLM-judge rows of the
  benchmark.

## Quick run

From the demo repo root, after `make setup` and a populated `.env`:

```bash
uv run tau2-instrumented run \
  --domain airline \
  --num-tasks 1 \
  --max-steps 10
```

To iterate on the policy, upload the new `.dl` (and companion
`.cpp`) via the SDK:

```python
from sasy.policy import upload_policy_file
upload_policy_file("tau2-examples/airline/airline_policy.dl")
```

Or run the full variance + evaluation pipeline from
`benchmarks/tau2-airline/`:

```bash
uv run python benchmarks/tau2-airline/run.py variance --n 5
uv run python benchmarks/tau2-airline/run_tau2.py \
    --policy-glob 'benchmarks/tau2-airline/output/*/airline_policy.dl'
```
