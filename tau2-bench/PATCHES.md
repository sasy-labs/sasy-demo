# Local patches vs upstream

Vendored from [`sierra-research/tau2-bench`](https://github.com/sierra-research/tau2-bench)
at commit [`0ed2fd8`](https://github.com/sierra-research/tau2-bench/commit/0ed2fd8).

SASY-specific wiring lives in `../tau2-examples/` (the `tau2-instrumented`
entry point). The patches in the vendored tree itself are the ones that
*can't* live outside it — hooks into core types and replay logic.

## SASY enforcement hooks

- **`src/tau2/domains/airline/environment.py`**, **`src/tau2/domains/retail/environment.py`** —
  honor `TAU2_SKIP_NL_POLICY=1`. When set, the domain loads an empty /
  placeholder NL policy so the agent cannot read the rules from its
  system prompt and has to rely on Datalog enforcement via the reference
  monitor. Upstream hard-codes `open(POLICY_PATH).read()`.
- **`src/tau2/environment/environment.py`** — during trajectory replay,
  skip tool calls whose response starts with `[BLOCKED]`. These are
  policy-level denials from the SASY reference monitor; replaying them
  against the gold environment would succeed (no policy engine there)
  and cause a spurious mismatch.
- **`src/tau2/run.py`** — set `GRPC_ENABLE_FORK_SUPPORT=false` at import
  time to silence "Other threads are currently calling into gRPC"
  warnings introduced by the SASY gRPC client + tau2's fork-based
  concurrency.

## Modified domain content

- **`data/tau2/domains/airline/policy.md`** — tightened cancellation /
  compensation rules (explicitly bars regular members from compensation
  regardless of cabin, adds "covered reason" enumeration for travel
  insurance, documents that compensation is independent of
  change/cancel). This is the policy the benchmark rows refer to; the
  modifications are intentional and should be preserved across rebases.

## Feature backports (predate 0ed2fd8 on the upstream branch)

- **`src/tau2/data_model/message.py`** — add `thought_signature` /
  `thinking_blocks` fields on `ToolCall` / `AssistantMessage` for Gemini
  multi-turn function calling. Upstream landed equivalent plumbing in
  later commits; this is the minimal port that works with our pinned
  snapshot.
- **`src/tau2/utils/llm_utils.py`** — pass the full provider-prefixed
  model name (`vertex_ai/claude-opus-4-5@...`) through to litellm's
  `completion_cost` so billing lookups work when the provider strips
  the prefix from `response.model`. Also threads `thought_signature`
  into the litellm request body via `provider_specific_fields`.
- **`pyproject.toml`** — adds `gymnasium>=1.2.2` to match the gym
  interface the pinned commit introduces.
