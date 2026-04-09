# Demo Scenarios

The demo includes 9 curated scenarios covering
every cell in the airline booking policy matrix.

## Running Scenarios

```bash
# All 9 scenarios
make demo

# Interactive (pause between stages)
make demo-step

# Individual scenario
make scenario-1
make scenario-3

# Individual with step mode
make scenario-1-step
```

## Cancellation Scenarios

### Scenario 1: Regular + no insurance → DENY

John Doe (regular member) tries to cancel
reservation RKLA42 which has no travel insurance.

**Expected:** Policy denies `cancel_reservation`.
The agent explains that insurance is required for
non-gold members.

```bash
make scenario-1
```

### Scenario 2: Regular + insurance → ALLOW

John Doe cancels a reservation that has travel
insurance.

**Expected:** Policy allows `cancel_reservation`.
Insurance unlocks cancellation for all tiers.

```bash
make scenario-2
```

### Scenario 3: Silver + no insurance → DENY

Aarav Ahmed (silver member) tries to cancel
without insurance.

**Expected:** Policy denies. Silver doesn't
override the insurance requirement — only gold
does.

```bash
make scenario-3
```

### Scenario 4: Silver + insurance → ALLOW

Aarav Ahmed cancels with insurance.

**Expected:** Policy allows.

```bash
make scenario-4
```

### Scenario 5: Gold + no insurance → ALLOW

Emma Kim (gold member) cancels without insurance.

**Expected:** Policy allows — gold perk.

```bash
make scenario-5
```

## Modification Scenarios

### Scenario 6: Regular + basic economy → DENY

John Doe tries to change flights on a basic
economy reservation.

**Expected:** Policy denies `update_reservation_flights`.
Regular members cannot modify basic economy.

```bash
make scenario-6
```

### Scenario 7: Silver + basic economy → ALLOW

Aarav Ahmed modifies a basic economy reservation.

**Expected:** Policy allows — silver perk.

```bash
make scenario-7
```

### Scenario 8: Regular + economy → ALLOW

John Doe modifies an economy reservation.

**Expected:** Policy allows — economy is always
modifiable.

```bash
make scenario-8
```

### Scenario 9: Gold + basic economy → ALLOW

Emma Kim modifies a basic economy reservation.

**Expected:** Policy allows — gold members can
modify any cabin.

```bash
make scenario-9
```

## What to Look For

In each scenario, watch for:

1. **[SASY] Consulting policy engine...** — the
   framework is checking the tool call
2. **[SASY] ✓ AUTHORIZED** or **[SASY] ✗ DENIED** —
   the policy decision
3. The **denial reason** — explains why in human
   terms
4. The **agent's response** — how it handles the
   denial gracefully

## Experiment: Edit the Policy

Try modifying `policy.dl` and re-uploading:

```bash
# Edit policy.dl (remove the insurance requirement)
make upload
make scenario-1   # Should now be ALLOWED
```

Or translate a modified English policy:

```bash
# Edit policy_english.md
make translate     # ~5-10 minutes
make upload-compiled
make demo          # See the new rules in action
```
