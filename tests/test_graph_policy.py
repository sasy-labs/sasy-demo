"""Integration test: graph event recording + policy evaluation.

Verifies the full pipeline through sasy.fly.dev:
  1. Upload airline policy (with functors)
  2. Record conversation events into the graph
  3. Check tool call authorization
  4. Assert the policy fires the CORRECT specific rule
     based on conversation context, not the catch-all

Run:
    SASY_API_KEY_SUFFIX=<suffix> \
    pytest examples/customer-demo/tests/test_graph_policy.py -xvs
"""

import os
import time
from pathlib import Path
from uuid import uuid4

import pytest

# ── sasy setup ──────────────────────────────────────────


@pytest.fixture(scope="module", autouse=True)
def configure_sasy():
    """Configure sasy to talk to fly.io and upload policy."""
    suffix = os.environ.get("SASY_API_KEY_SUFFIX")
    if not suffix:
        pytest.skip("SASY_API_KEY_SUFFIX not set")

    api_key = f"demo-key-{suffix}"
    sasy_url = os.environ.get(
        "SASY_URL", "sasy.fly.dev:443"
    )

    # Clear local TLS from .env
    os.environ.pop("TLS_CA_PATH", None)
    os.environ.pop("TLS_CERT_PATH", None)
    os.environ.pop("TLS_KEY_PATH", None)
    os.environ["SASY_URL"] = sasy_url

    from sasy.auth.hooks import APIKeyAuthHook
    from sasy.config import configure

    configure(
        url=sasy_url,
        ca_path="",
        cert_path="",
        key_path="",
        auth_hook=APIKeyAuthHook(api_key=api_key),
    )

    # Upload airline policy with functors
    from sasy.policy import upload_policy_file

    policy_path = (
        Path(__file__).parent.parent / "policy.dl"
    )
    resp = upload_policy_file(policy_path)
    assert resp.accepted, (
        f"Policy upload failed: {resp.error_output}"
    )
    # Give the evaluator a moment to start workers
    time.sleep(2)


# ── Helpers ─────────────────────────────────────────────


def _record_user_message(text: str) -> str:
    """Record a user message event. Returns event ID."""
    from sasy.observability.api import record_events
    from sasy.proto.observability_pb2 import (
        Event,
        Role,
    )

    event = Event(
        text=text,
        role=Role.USER,
        agent="LLMAgent",
        id=str(uuid4()),
    )
    ids = record_events([event])
    return ids[0]


def _record_agent_tool_call(
    tool_name: str,
    tool_args: str,
    depends_on: list[str],
) -> str:
    """Record an agent message with a tool call.

    Returns the event ID.
    """
    from sasy.observability.api import (
        record_events_with_dependencies,
    )
    from sasy.proto.observability_pb2 import (
        Edge,
        Event,
        Role,
        Tool,
    )

    event_id = str(uuid4())
    event = Event(
        text="",
        role=Role.LLM,
        agent="LLMAgent",
        id=event_id,
        tools=[
            Tool(name=tool_name, arguments=tool_args)
        ],
    )
    edges = [
        Edge(
            source=dep_id,
            destination=event_id,
            proximal=(i == len(depends_on) - 1),
        )
        for i, dep_id in enumerate(depends_on)
    ]
    ids = record_events_with_dependencies(
        [event], edges
    )
    return ids[0]


def _check_tool(
    tool_name: str,
    tool_args: str,
    input_node_ids: list[str],
) -> tuple[bool, str]:
    """Check tool authorization. Returns (authorized, reason)."""
    from sasy.reference_monitor import check_tool_call

    resp = check_tool_call(
        tool_name, tool_args, input_node_ids
    )
    if resp.authorized:
        return True, ""
    if resp.denial_trace:
        reasons = [
            r.details
            for r in resp.denial_trace.reasons
            if r.details
        ]
        return False, "; ".join(reasons)
    return False, "denied (no trace)"


# ── Tests ───────────────────────────────────────────────


def test_cancel_denied_no_reason():
    """Cancel with no prior user message → catch-all denial."""
    authorized, reason = _check_tool(
        "cancel_reservation",
        '{"reservation_id": "EHGLP3"}',
        [],
    )
    assert not authorized
    assert "No valid cancellation reason" in reason


def test_cancel_denied_social_event():
    """User says 'birthday party' → social event rule fires."""
    user_id = _record_user_message(
        "I need to cancel because I have a birthday "
        "party that weekend."
    )
    # Record agent tool call depending on user message
    tool_id = _record_agent_tool_call(
        "cancel_reservation",
        '{"reservation_id": "EHGLP3"}',
        depends_on=[user_id],
    )

    authorized, reason = _check_tool(
        "cancel_reservation",
        '{"reservation_id": "EHGLP3"}',
        [user_id, tool_id],
    )
    assert not authorized, f"Expected denial, got authorized"
    assert "Social events" in reason, (
        f"Expected 'Social events' in reason, got: {reason}"
    )


def test_cancel_denied_user_error():
    """User says 'booked the wrong flight' → user error rule."""
    user_id = _record_user_message(
        "I accidentally booked the wrong flight, "
        "it was a mistake."
    )
    tool_id = _record_agent_tool_call(
        "cancel_reservation",
        '{"reservation_id": "EHGLP3"}',
        depends_on=[user_id],
    )

    authorized, reason = _check_tool(
        "cancel_reservation",
        '{"reservation_id": "EHGLP3"}',
        [user_id, tool_id],
    )
    assert not authorized
    assert "Accidental booking" in reason, (
        f"Expected 'Accidental booking' in reason, "
        f"got: {reason}"
    )


def test_lookup_always_allowed():
    """get_reservation_details is always authorized."""
    authorized, reason = _check_tool(
        "get_reservation_details",
        '{"reservation_id": "EHGLP3"}',
        [],
    )
    assert authorized, f"Expected authorized, got: {reason}"
