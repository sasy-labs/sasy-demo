# SASY Policy Enforcement Demo

> **[Documentation](https://sasy-demo.pages.dev)**

Interactive demo showing how Datalog policies enforce
rules on airline agent tool calls in real time.

An LLM-powered customer service agent handles airline
requests (cancellations, modifications, bookings).
Every tool call the agent makes is checked against a
Souffle Datalog policy running on `sasy.fly.dev`. The
policy can **deny** unsafe actions with reasons and
suggestions.

You can **edit the policy**, re-upload it, and re-run
the demo to see how different rules change agent
behavior.

## Policy Matrix

The policy uses **membership tier**, **insurance
status**, and **cabin class** to determine what
actions are allowed — no phrase-matching.

### Cancellation (cabin class irrelevant)

| | No Insurance | With Insurance |
|---|---|---|
| Regular | DENY | ALLOW |
| Silver | DENY | ALLOW |
| Gold | ALLOW | ALLOW |

- **Gold perk:** cancel without insurance
- **Insurance:** unlocks cancellation for all tiers

### Modification

| | Basic Economy | Economy |
|---|---|---|
| Regular | DENY | ALLOW |
| Silver | ALLOW | ALLOW |
| Gold | ALLOW | ALLOW |

- **Silver perk:** modify basic economy
- **Economy:** always modifiable

## Prerequisites

- Python 3.10+
- [uv](https://docs.astral.sh/uv/) package manager
- `OPENAI_API_KEY` — for the LLM agent (uses gpt-4.1)
- `SASY_API_KEY_SUFFIX` — provided to you by us

## Quick Start

```bash
# 1. Install dependencies
make setup

# 2. Create your .env file (copy from template)
cp .env.example .env
# Edit .env — add your OPENAI_API_KEY and SASY_API_KEY_SUFFIX

# 3. Run all 9 demo scenarios
make demo
```

## What You'll See

The demo runs 9 curated scenarios covering every cell
in the policy matrix. For each one:

- A simulated customer calls with a specific request
- The agent calls tools (cancel, modify, look up, etc.)
- Each tool call shows `[POLICY] AUTHORIZED` (green)
  or `[POLICY] DENIED` (red) with the reason

### Cancellation Scenarios

**Scenario 1: Regular + no insurance → DENY**
John Doe (regular member) tries to cancel a reservation
with no travel insurance. Policy denies — insurance is
required for non-gold members.

**Scenario 2: Regular + with insurance → ALLOW**
John Doe cancels a reservation that has travel
insurance. Policy allows — insurance unlocks
cancellation.

**Scenario 3: Silver + no insurance → DENY**
Aarav Ahmed (silver member) tries to cancel without
insurance. Policy denies — silver doesn't override the
insurance requirement (only gold does).

**Scenario 4: Silver + with insurance → ALLOW**
Aarav Ahmed cancels a reservation with insurance.
Policy allows.

**Scenario 5: Gold + no insurance → ALLOW**
Emma Kim (gold member) cancels without insurance.
Policy allows — gold perk.

### Modification Scenarios

**Scenario 6: Regular + basic economy → DENY**
John Doe tries to change flights on a basic economy
reservation. Policy denies — regular members cannot
modify basic economy.

**Scenario 7: Silver + basic economy → ALLOW**
Aarav Ahmed modifies a basic economy reservation.
Policy allows — silver perk.

**Scenario 8: Regular + economy → ALLOW**
John Doe modifies an economy reservation. Policy
allows — economy is always modifiable.

**Scenario 9: Gold + basic economy → ALLOW**
Emma Kim modifies a basic economy reservation.
Policy allows — gold members can modify any cabin.

## Running Individual Scenarios

```bash
make scenario-1   # Regular cancel no insurance (DENY)
make scenario-2   # Regular cancel with insurance (ALLOW)
make scenario-3   # Silver cancel no insurance (DENY)
make scenario-4   # Silver cancel with insurance (ALLOW)
make scenario-5   # Gold cancel no insurance (ALLOW)
make scenario-6   # Regular modify basic economy (DENY)
make scenario-7   # Silver modify basic economy (ALLOW)
make scenario-8   # Regular modify economy (ALLOW)
make scenario-9   # Gold modify basic economy (ALLOW)
```

## Editing the Policy

The Datalog policy is in `policy.dl`. Try these
experiments:

### Experiment 1: Allow all cancellations

Remove the cancellation denial rule and re-run:

```bash
make demo
```

Now scenarios 1 and 3 should also be **allowed**.

### Experiment 2: Remove the silver perk

Add `!MembershipTier("silver")` to the modification
rule so only gold can modify basic economy:

```datalog
Unauthorized(idx) :-
    Actions(idx, a),
    IsTool(a, "update_reservation_flights"),
    a = $CallTool(_, args),
    res_id = @json_get_str(args, "reservation_id"),
    res_id != "",
    ReservationCabin(res_id, "basic_economy"),
    !MembershipTier("gold").
```

Now scenario 7 (silver + basic economy) is **denied**.

### Experiment 3: Make insurance override everything

Add a rule allowing insured reservations to be modified
regardless of cabin class:

```datalog
// Never deny modification if insured
// (override the basic economy restriction)
```

## How It Works

```
Customer (simulated)
    |
    v
LLM Agent (OpenAI gpt-4.1)
    |
    v  tool call: cancel_reservation(...)
    |
SASY Policy Check (sasy.fly.dev)
    |
    +-- AUTHORIZED --> execute tool
    |
    +-- DENIED ------> return [BLOCKED] to agent
                        agent explains to customer
```

The policy reads **membership tier** from the
`get_user_details` tool result and **cabin class** +
**insurance** from the `get_reservation_details` tool
result — all via the dependency graph. The same tool
call is allowed or denied based on the user's
attributes, not keywords in the conversation.

## Project Structure

```
policy.dl              # Datalog policy (edit this!)
functors.cpp           # C++ custom functors (JSON
                       #   field extraction)
policy_english.md      # Plain-English policy rules
data/
  db.json              # Airline database (users,
                       #   reservations, flights)
src/customer_demo/
  main.py              # Entry point
  agent.py             # Agent loop + user simulator
  tools.py             # Airline tool implementations
  scenarios.py         # 9 curated scenarios
  display.py           # Colored terminal output
  data_model.py        # Data types
  tool_schema.py       # Function -> OpenAI schema
```

## Configuration

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `OPENAI_API_KEY` | Yes | — | OpenAI API key |
| `SASY_API_KEY_SUFFIX` | Yes | — | Provided by us |
| `SASY_URL` | No | `sasy.fly.dev:443` | Policy service |
| `OPENAI_MODEL` | No | `gpt-4.1` | LLM model |
