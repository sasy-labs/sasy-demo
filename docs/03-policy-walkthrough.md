# Policy Walkthrough

This page explains the airline booking policy
step by step — from English to enforced Datalog.

## English Policy

The policy has three sections:

**Default:** All actions are authorized unless
explicitly denied.

**Cancellation:** Depends on membership tier and
insurance status.

**Modification:** Depends on membership tier and
cabin class.

## Structured Specification

The translation produces numbered clauses. Each
clause is one atomic authorization decision:

<details>
<summary><b>C1:</b> Authorize all actions by default</summary>

```datalog
IsAuthorized(idx) :- Actions(idx, _).
```

This is the default-allow rule. Every tool call
is authorized unless a specific deny rule overrides
it. Without this rule, tools like
`get_reservation_details` would be blocked.

</details>

<details>
<summary><b>C2:</b> Allow cancel if gold member</summary>

```datalog
IsAuthorized(idx) :-
    Actions(idx, a),
    IsTool(a, "cancel_reservation"),
    ToolResultField("get_reservation_details",
        "membership", "gold").
```

Gold members can cancel any reservation regardless
of insurance. The policy checks the `membership`
field from `get_reservation_details`.

</details>

<details>
<summary><b>C3:</b> Allow cancel if has insurance</summary>

```datalog
IsAuthorized(idx) :-
    Actions(idx, a),
    IsTool(a, "cancel_reservation"),
    ToolResultField("get_reservation_details",
        "insurance", "yes").
```

Any member with insurance can cancel.

</details>

<details>
<summary><b>C4:</b> Deny cancel if no insurance and not gold</summary>

```datalog
// @deny_message: Cannot cancel without insurance
//   unless you are a gold member
// @suggestion: Consider adding travel insurance
// @tool_pattern: cancel_reservation
Unauthorized(idx) :-
    Actions(idx, a),
    IsTool(a, "cancel_reservation"),
    ToolResultField("get_reservation_details",
        "insurance", "no"),
    !ToolResultField("get_reservation_details",
        "membership", "gold").
```

The `@deny_message` annotation is shown to the
agent when the action is denied. The `@suggestion`
offers actionable advice.

</details>

<details>
<summary><b>C5:</b> Guard — deny cancel if reservation not looked up</summary>

```datalog
// @deny_message: Look up reservation details first
// @tool_pattern: cancel_reservation
Unauthorized(idx) :-
    Actions(idx, a),
    IsTool(a, "cancel_reservation"),
    !ToolResultField("get_reservation_details",
        "insurance", _).
```

Guard rules enforce prerequisites. The agent must
call `get_reservation_details` before attempting to
cancel. This prevents the agent from bypassing the
insurance check.

</details>

<details>
<summary><b>C6:</b> Allow modify if economy cabin</summary>

```datalog
IsAuthorized(idx) :-
    Actions(idx, a),
    IsTool(a, "update_reservation_flights"),
    ToolResultField("get_reservation_details",
        "cabin", "economy").
```

Economy reservations can be modified by any member.

</details>

<details>
<summary><b>C7:</b> Allow modify basic economy for silver/gold</summary>

```datalog
IsAuthorized(idx) :-
    Actions(idx, a),
    IsTool(a, "update_reservation_flights"),
    ToolResultField("get_reservation_details",
        "cabin", "basic_economy"),
    ToolResultField("get_reservation_details",
        "membership", "silver").
```

(Similar rule for gold members.)

</details>

<details>
<summary><b>C8:</b> Deny modify basic economy for regular</summary>

```datalog
// @deny_message: Regular members cannot modify
//   basic economy reservations
// @suggestion: Upgrade membership or cabin class
// @tool_pattern: update_reservation_flights
Unauthorized(idx) :-
    Actions(idx, a),
    IsTool(a, "update_reservation_flights"),
    ToolResultField("get_reservation_details",
        "cabin", "basic_economy"),
    ToolResultField("get_reservation_details",
        "membership", "regular").
```

</details>

<details>
<summary><b>C9:</b> Guard — deny modify if reservation not looked up</summary>

```datalog
// @deny_message: Look up reservation details first
// @tool_pattern: update_reservation_flights
Unauthorized(idx) :-
    Actions(idx, a),
    IsTool(a, "update_reservation_flights"),
    !ToolResultField("get_reservation_details",
        "cabin", _).
```

</details>

## Truth Table

The truth table shows every scenario tested:

| Action | Membership | Insurance | Cabin | Decision |
|--------|-----------|-----------|-------|----------|
| cancel | gold | no | - | ALLOW |
| cancel | gold | yes | - | ALLOW |
| cancel | silver | yes | - | ALLOW |
| cancel | silver | no | - | DENY |
| cancel | regular | yes | - | ALLOW |
| cancel | regular | no | - | DENY |
| modify | any | - | economy | ALLOW |
| modify | silver | - | basic_economy | ALLOW |
| modify | gold | - | basic_economy | ALLOW |
| modify | regular | - | basic_economy | DENY |

Rows with unknown fields produce **GUARD_DENY** —
the policy defers the decision until the agent
looks up the reservation details.

## How Enforcement Works

```
Customer message
    ↓
Agent reasons about what to do
    ↓
Agent calls a tool (e.g. cancel_reservation)
    ↓
SASY policy engine checks the call
    ↓
  ┌─ AUTHORIZED → tool executes, agent sees result
  └─ DENIED → agent sees denial reason + suggestion
```

The agent never sees the Datalog rules. It only
sees the `@deny_message` when a call is blocked,
and the `@suggestion` for what to do instead.
