"""Local integration test: graph-aware policy evaluation.

Tests the full pipeline against the LOCAL Rust binary:
  1. Upload airline policy with custom functors
  2. Record conversation events into the graph
  3. Check tool call authorization
  4. Assert the policy fires ONLY the correct rule
     based on what the user said

This is the definitive test for graph-dependent policy
evaluation. If it fails locally, the policy/functor
logic is broken. If it passes locally but fails on
Fly.io, it's a deploy issue.

Prerequisites:
  - Local Rust binary running:
    make serve-airline
  - TLS certs in certs/ directory

Run:
    pytest tests/test_local_graph_policy.py -xvs
"""

import os
import time
from pathlib import Path
from uuid import uuid4

import pytest
from dotenv import load_dotenv

# Load .env from the demo root so SASY_API_KEY set via the
# Quickstart flow is picked up automatically.
load_dotenv(Path(__file__).parent.parent / ".env")


@pytest.fixture(scope="module", autouse=True)
def configure_sasy():
    """Configure sasy (local or cloud via env vars).

    For cloud: set SASY_API_KEY (in .env per Quickstart,
    or in shell).
    For local: start ``make serve-airline``; ensure
    SASY_API_KEY is not set in the environment.
    """
    api_key = os.environ.get("SASY_API_KEY")

    if api_key:
        # Cloud mode — SASY_API_KEY present signals cloud target
        sasy_url = os.environ.get(
            "SASY_URL", "sasy.fly.dev:443"
        )
        os.environ.pop("TLS_CA_PATH", None)
        os.environ.pop("TLS_CERT_PATH", None)
        os.environ.pop("TLS_KEY_PATH", None)

        from sasy.auth.hooks import APIKeyAuthHook
        from sasy.config import configure

        configure(
            url=sasy_url,
            ca_path="",
            cert_path="",
            key_path="",
            auth_hook=APIKeyAuthHook(
                api_key=api_key
            ),
        )
    else:
        # Local mode
        from sasy.auth.hooks import APIKeyAuthHook
        from sasy.config import configure

        configure(
            url="localhost:10089",
            ca_path="certs/ca.crt",
            cert_path="certs/client.crt",
            key_path="certs/client.key",
            auth_hook=APIKeyAuthHook(
                api_key="admin-test-key"
            ),
        )

    # Upload airline policy with functors
    from sasy.policy import upload_policy_file

    policy_path = (
        Path(__file__).parent.parent / "policy.dl"
    )
    try:
        resp = upload_policy_file(policy_path)
    except Exception as e:
        pytest.skip(f"Cannot connect to sasy: {e}")
    assert resp.accepted, (
        f"Policy upload failed: {resp.error_output}"
    )
    time.sleep(2)


def _record_user_msg(text: str) -> str:
    """Record a user message. Returns event ID."""
    from sasy.observability.api import record_events
    from sasy.proto.observability_pb2 import (
        Event,
        Role,
    )

    eid = str(uuid4())
    ev = Event(
        text=text,
        role=Role.USER,
        agent="LLMAgent",
        id=eid,
    )
    record_events([ev])
    return eid


def _record_tool_call(
    tool_name: str,
    tool_args: str,
    depends_on: list[str],
) -> str:
    """Record an agent tool call event with edges."""
    from sasy.observability.api import (
        record_events_with_dependencies,
    )
    from sasy.proto.observability_pb2 import (
        Edge,
        Event,
        Role,
        Tool,
    )

    eid = str(uuid4())
    ev = Event(
        text="",
        role=Role.LLM,
        agent="LLMAgent",
        id=eid,
        tools=[
            Tool(name=tool_name, arguments=tool_args)
        ],
    )
    edges = [
        Edge(
            source=dep_id,
            destination=eid,
            proximal=(i == len(depends_on) - 1),
        )
        for i, dep_id in enumerate(depends_on)
    ]
    record_events_with_dependencies([ev], edges)
    return eid


def _check(
    tool_name: str,
    tool_args: str,
    input_ids: list[str],
) -> tuple[bool, list[str]]:
    """Check tool auth. Returns (authorized, reasons)."""
    from sasy.reference_monitor import check_tool_call

    resp = check_tool_call(
        tool_name, tool_args, input_ids
    )
    if resp.authorized:
        return True, []
    reasons = []
    if resp.denial_trace:
        reasons = [
            r.details
            for r in resp.denial_trace.reasons
            if r.details
        ]
    return False, reasons


# ── Tests ───────────────────────────────────────────────
# Each test records a specific user message, then checks
# cancel_reservation. The assertion verifies that ONLY
# the correct specific denial rule fires.


class TestSocialEventDenial:
    """User mentions birthday party → only Rule 2."""

    def test_social_event_only(self):
        uid = _record_user_msg(
            "I need to cancel because I have a "
            "birthday party that weekend."
        )
        tid = _record_tool_call(
            "cancel_reservation",
            '{"reservation_id": "EHGLP3"}',
            depends_on=[uid],
        )
        authorized, reasons = _check(
            "cancel_reservation",
            '{"reservation_id": "EHGLP3"}',
            [uid, tid],
        )
        assert not authorized, "Should be denied"
        assert any(
            "Social events" in r for r in reasons
        ), f"Expected 'Social events' in {reasons}"
        # THIS is the key assertion: the other rules
        # should NOT fire
        assert not any(
            "Accidental booking" in r for r in reasons
        ), (
            f"'Accidental booking' should NOT be in "
            f"reasons: {reasons}"
        )


class TestUserErrorDenial:
    """User mentions 'wrong flight' → only Rule 1."""

    def test_user_error_only(self):
        uid = _record_user_msg(
            "I accidentally booked the wrong flight, "
            "it was a mistake."
        )
        tid = _record_tool_call(
            "cancel_reservation",
            '{"reservation_id": "EHGLP3"}',
            depends_on=[uid],
        )
        authorized, reasons = _check(
            "cancel_reservation",
            '{"reservation_id": "EHGLP3"}',
            [uid, tid],
        )
        assert not authorized, "Should be denied"
        assert any(
            "Accidental booking" in r for r in reasons
        ), f"Expected 'Accidental booking' in {reasons}"
        # Social events rule should NOT fire
        assert not any(
            "Social events" in r for r in reasons
        ), (
            f"'Social events' should NOT be in "
            f"reasons: {reasons}"
        )


class TestValidReasonAllowed:
    """User mentions medical emergency → should be ALLOWED."""

    def test_medical_allowed(self):
        uid = _record_user_msg(
            "I am sick and my doctor told me I "
            "cannot travel."
        )
        tid = _record_tool_call(
            "cancel_reservation",
            '{"reservation_id": "EHGLP3"}',
            depends_on=[uid],
        )
        authorized, reasons = _check(
            "cancel_reservation",
            '{"reservation_id": "EHGLP3"}',
            [uid, tid],
        )
        assert authorized, (
            f"Should be allowed for medical reason, "
            f"but got denied: {reasons}"
        )


class TestNoReasonCatchAll:
    """No user message at all → catch-all Rule 3."""

    def test_no_context_catchall(self):
        authorized, reasons = _check(
            "cancel_reservation",
            '{"reservation_id": "EHGLP3"}',
            [],
        )
        assert not authorized, "Should be denied"
        assert any(
            "No valid cancellation reason" in r
            for r in reasons
        ), f"Expected catch-all reason in {reasons}"


class TestLookupAlwaysAllowed:
    """Read-only lookups are always authorized."""

    def test_get_reservation(self):
        authorized, reasons = _check(
            "get_reservation_details",
            '{"reservation_id": "EHGLP3"}',
            [],
        )
        assert authorized, (
            f"Lookup should be allowed: {reasons}"
        )
