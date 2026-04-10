"""Curated airline scenarios for the demo.

Each scenario exercises a specific cell in the policy
matrix (membership tier × insurance / cabin class).
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class Scenario:
    """A single demo scenario describing a customer request.

    Attributes:
        id: Unique numeric identifier (1-based).
        title: Short human-readable title.
        description: One-sentence summary of the scenario.
        user_id: The airline customer user-id string.
        first_user_message: Opening message sent by the
            simulated customer.
        user_sim_instructions: System-prompt instructions
            for the user-simulator LLM.
        expected_denial: Tool name that policy should deny,
            or ``None`` if the request should be allowed.
        policy_note: Brief explanation of why the policy
            allows or denies this scenario.
    """

    id: int
    title: str
    description: str
    user_id: str
    first_user_message: str
    user_sim_instructions: str
    expected_denial: str | None
    policy_note: str


# ── Scenario definitions ─────────────────────────────────

_SCENARIOS: list[Scenario] = [
    # ── Cancellation scenarios ───────────────────────────
    Scenario(
        id=1,
        title="Regular member cancel without insurance",
        description=(
            "John Doe (regular) tries to cancel a "
            "reservation with no travel insurance."
        ),
        user_id="john_doe_1234",
        first_user_message=(
            "Hi, I'm John Doe, user ID john_doe_1234. "
            "I need to cancel my reservation RKLA42."
        ),
        user_sim_instructions=(
            "You are John Doe calling to cancel "
            "reservation RKLA42. You do not have "
            "travel insurance. If the agent refuses, "
            "ask what your options are. If your issue "
            "is resolved or the agent cannot help, "
            "respond with ###STOP###."
        ),
        expected_denial="cancel_reservation",
        policy_note=(
            "Regular + no insurance → DENY "
            "(insurance required for non-gold)"
        ),
    ),
    Scenario(
        id=2,
        title="Regular member cancel with insurance",
        description=(
            "John Doe (regular) cancels a reservation "
            "that has travel insurance — policy allows."
        ),
        user_id="john_doe_1234",
        first_user_message=(
            "Hi, I'm John Doe, user ID john_doe_1234. "
            "I need to cancel my reservation WNEQ78. "
            "I have travel insurance on that booking."
        ),
        user_sim_instructions=(
            "You are John Doe calling to cancel "
            "reservation WNEQ78. You purchased travel "
            "insurance. If the agent confirms "
            "cancellation, thank them. If your issue "
            "is resolved or the agent cannot help, "
            "respond with ###STOP###."
        ),
        expected_denial=None,
        policy_note=(
            "Regular + insurance → ALLOW "
            "(insurance unlocks cancellation)"
        ),
    ),
    Scenario(
        id=3,
        title="Silver member cancel without insurance",
        description=(
            "Aarav Ahmed (silver) tries to cancel a "
            "reservation with no insurance — silver "
            "does not override the insurance rule."
        ),
        user_id="aarav_ahmed_6699",
        first_user_message=(
            "Hello, I'm Aarav Ahmed, user ID "
            "aarav_ahmed_6699. I'm a silver member "
            "and I need to cancel reservation IFOYYZ."
        ),
        user_sim_instructions=(
            "You are Aarav Ahmed, a silver member, "
            "trying to cancel reservation IFOYYZ. "
            "You expect your silver status to help. "
            "If the agent refuses, express surprise "
            "that silver doesn't override the "
            "insurance requirement. If your issue "
            "is resolved or the agent cannot help, "
            "respond with ###STOP###."
        ),
        expected_denial="cancel_reservation",
        policy_note=(
            "Silver + no insurance → DENY "
            "(only gold overrides insurance)"
        ),
    ),
    Scenario(
        id=4,
        title="Silver member cancel with insurance",
        description=(
            "Aarav Ahmed (silver) cancels a reservation "
            "that has travel insurance — policy allows."
        ),
        user_id="aarav_ahmed_6699",
        first_user_message=(
            "Hello, I'm Aarav Ahmed, user ID "
            "aarav_ahmed_6699. I need to cancel my "
            "reservation M20IZO. I have travel "
            "insurance on that booking."
        ),
        user_sim_instructions=(
            "You are Aarav Ahmed cancelling "
            "reservation M20IZO. You purchased "
            "travel insurance. If the agent confirms "
            "cancellation, thank them. If your issue "
            "is resolved or the agent cannot help, "
            "respond with ###STOP###."
        ),
        expected_denial=None,
        policy_note=(
            "Silver + insurance → ALLOW "
            "(insurance unlocks cancellation)"
        ),
    ),
    Scenario(
        id=5,
        title="Gold member cancel without insurance",
        description=(
            "Emma Kim (gold) cancels a reservation "
            "with no insurance — gold members can "
            "always cancel."
        ),
        user_id="emma_kim_9957",
        first_user_message=(
            "Hi, I'm Emma Kim, user ID emma_kim_9957. "
            "I need to cancel my reservation EHGLP3."
        ),
        user_sim_instructions=(
            "You are Emma Kim, a gold member, "
            "cancelling reservation EHGLP3. You "
            "do not have insurance but expect your "
            "gold status to allow the cancellation. "
            "If the agent confirms, thank them. "
            "If your issue is resolved or the agent "
            "cannot help, respond with ###STOP###."
        ),
        expected_denial=None,
        policy_note=(
            "Gold + no insurance → ALLOW "
            "(gold perk: cancel without insurance)"
        ),
    ),
    # ── Modification scenarios ───────────────────────────
    Scenario(
        id=6,
        title="Regular member modify basic economy",
        description=(
            "John Doe (regular) tries to change "
            "flights on a basic economy reservation "
            "— regular members cannot modify basic "
            "economy."
        ),
        user_id="john_doe_1234",
        first_user_message=(
            "Hi, I'm John Doe, user ID "
            "john_doe_1234. I need to change my "
            "reservation RKLA42 to a different "
            "date. Same route PHX to LAS, just "
            "move it to May 18, 2024."
        ),
        user_sim_instructions=(
            "You are John Doe. You want to move "
            "reservation RKLA42 to May 18. If the "
            "agent presents options, pick the first "
            "one. If the agent says it cannot be "
            "modified, ask why. If your issue is "
            "resolved or the agent cannot help, "
            "respond with ###STOP###."
        ),
        expected_denial="update_reservation_flights",
        policy_note=(
            "Regular + basic economy → DENY "
            "(need silver or gold to modify "
            "basic economy)"
        ),
    ),
    Scenario(
        id=7,
        title="Silver member modify basic economy",
        description=(
            "Aarav Ahmed (silver) modifies a basic "
            "economy reservation — silver perk "
            "allows this."
        ),
        user_id="aarav_ahmed_6699",
        first_user_message=(
            "Hello, I'm Aarav Ahmed, user ID "
            "aarav_ahmed_6699. I need to change "
            "my reservation IFOYYZ flights to "
            "May 18, 2024. Same route CLT to EWR."
        ),
        user_sim_instructions=(
            "You are Aarav Ahmed, a silver member. "
            "You want to move reservation IFOYYZ "
            "to May 18. If the agent presents "
            "options, pick the first one. If the "
            "agent confirms the change, thank them. "
            "If your issue is resolved or the agent "
            "cannot help, respond with ###STOP###."
        ),
        expected_denial=None,
        policy_note=(
            "Silver + basic economy → ALLOW "
            "(silver perk: modify basic economy)"
        ),
    ),
    Scenario(
        id=8,
        title="Regular member modify economy",
        description=(
            "John Doe (regular) modifies an economy "
            "reservation — economy flights can "
            "always be modified."
        ),
        user_id="john_doe_1234",
        first_user_message=(
            "Hi, I'm John Doe, user ID "
            "john_doe_1234. I need to change my "
            "reservation WNEQ78 flights to "
            "May 18, 2024. Same route ATL to MCO."
        ),
        user_sim_instructions=(
            "You are John Doe. You want to move "
            "reservation WNEQ78 to May 18. If the "
            "agent presents options, pick the first "
            "one. If the agent confirms the change, "
            "thank them. If your issue is resolved "
            "or the agent cannot help, respond with "
            "###STOP###."
        ),
        expected_denial=None,
        policy_note=(
            "Regular + economy → ALLOW "
            "(economy is always modifiable)"
        ),
    ),
    Scenario(
        id=9,
        title="Gold member modify basic economy",
        description=(
            "Emma Kim (gold) modifies a basic "
            "economy reservation — gold members "
            "can modify any cabin class."
        ),
        user_id="emma_kim_9957",
        first_user_message=(
            "Hi, I'm Emma Kim, user ID "
            "emma_kim_9957. I need to change my "
            "reservation EHGLP3 flights to "
            "May 25, 2024. Same route PHX to JFK."
        ),
        user_sim_instructions=(
            "You are Emma Kim, a gold member. You "
            "want to move reservation EHGLP3 to "
            "May 25. If the agent presents options, "
            "pick the first one. If the agent "
            "confirms the change, thank them. "
            "If your issue is resolved or the agent "
            "cannot help, respond with ###STOP###."
        ),
        expected_denial=None,
        policy_note=(
            "Gold + basic economy → ALLOW "
            "(gold perk: modify any cabin)"
        ),
    ),
]


def get_scenarios() -> list[Scenario]:
    """Return all curated demo scenarios.

    Returns:
        A list of every ``Scenario`` defined in this
        module, ordered by id.
    """
    return list(_SCENARIOS)


def get_scenario(scenario_id: int) -> Scenario:
    """Return a single scenario by its numeric id.

    Args:
        scenario_id: The 1-based scenario identifier.

    Returns:
        The matching ``Scenario``.

    Raises:
        ValueError: If no scenario with that id exists.
    """
    for s in _SCENARIOS:
        if s.id == scenario_id:
            return s
    valid = [s.id for s in _SCENARIOS]
    raise ValueError(
        f"Unknown scenario id {scenario_id}. "
        f"Valid ids: {valid}"
    )
