# Translate a Policy

Turn an English security policy into verified
Souffl&eacute; Datalog using the SASY SDK.

## Install the SDK

```bash
pip install sasy
```

## Write Your English Policy

Create a file describing your authorization rules
in plain English:

```markdown
# Airline Booking Policy

## Default behavior
- All actions are authorized by default

## Cancellation policy
- Gold members can cancel any reservation,
  regardless of insurance status
- Silver and regular members can only cancel
  if the reservation has travel insurance
- Deny cancellation if the reservation has no
  insurance and the member is not gold

## Flight modification policy
- Economy reservations can be modified by any member
- Basic economy reservations can only be modified
  by silver or gold members
- Deny flight modifications on basic economy
  reservations for regular members
```

## Translate It

```python
from sasy.policy import write_policy

with open("policy_english.md") as f:
    english = f.read()

result = write_policy(
    english=english,
    on_progress=lambda stage, elapsed: print(
        f"  {stage} ({elapsed:.0f}s)"
    ),
)

result.print_summary()
result.save_datalog("policy_compiled.dl")
result.save_truth_table("truth_table.tsv")
```

Or use the Makefile shortcut:

```bash
make translate
```

## What You Get Back

The `result` object contains:

| Artifact | Description |
|----------|-------------|
| `result.datalog` | The generated Souffl&eacute; Datalog policy |
| `result.structured_spec` | Numbered clauses (C1, C2, ...) extracted from your English |
| `result.truth_table_tsv` | Every test scenario with the expected decision |
| `result.verification` | Verification metrics (see below) |

## Confidence Report

Call `result.print_summary()` to see:

```
Policy Compilation Result
========================================
Status:       SUCCESS (336s)

Structured Spec
  9 clauses (C1-C9)

Verification
  Truth table:        25 scenarios
    11 ALLOW | 3 DENY | 11 GUARD_DENY
  Assertions:         25/25 passed
  Independent checks: 3/3 passed
  Round-trip audit:   PASS
```

### What the Numbers Mean

**Truth table** — every combination of attributes
(membership tier, insurance status, cabin class)
was tested. Each row shows what the policy decides
for that scenario.

**Assertions** — the generated Datalog was run
against every truth table row on the live SASY
policy engine. 25/25 means the Datalog produces
the exact same decisions as the specification.

**Independent checks** — three separate reviewers
examined the policy for:

- Omitted requirements (did we miss anything from
  the English?)
- Boundary conditions (do edge cases behave
  correctly?)
- Guard logic (are prerequisite lookups enforced?)

**Round-trip audit** — the Datalog was read back
without seeing the original English, and the
reconstructed intent was compared against the
specification. PASS means nothing was lost in
translation.

## Upload and Enforce

Once you're confident in the translation:

```python
from sasy.policy import upload_policy

with open("policy_compiled.dl") as f:
    datalog = f.read()

resp = upload_policy(
    policy_source=datalog,
    hot_reload=True,
)
print("Uploaded!" if resp.accepted else resp.error_output)
```

Or:

```bash
make upload-compiled
```

The policy is now live. Every tool call your agent
makes will be checked against it.

## Translate Multiple Variants

Want to test if different phrasings produce the
same policy? Translate several variants at once:

```python
from sasy.policy import write_policies

results = write_policies(
    [variant_a, variant_b, variant_c],
)

for i, r in enumerate(results):
    print(f"\nVariant {i+1}:")
    r.print_summary()
```

Compare the truth table shapes and assertion
results across variants.
