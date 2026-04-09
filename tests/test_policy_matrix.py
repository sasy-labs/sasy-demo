"""Policy matrix test — attribute-based rules.

Evaluates every cell of the cancellation and modification
matrices directly against the policy engine, without any
LLM agent or simulated customer.

Requires: SASY server running (local or cloud).
Cloud: set SASY_API_KEY_SUFFIX env var.
Local: run ``make serve-airline``.

Run:
    pytest tests/test_policy_matrix.py -xvs
"""

from __future__ import annotations

import json
import os
import time
from pathlib import Path

import pytest
from dotenv import load_dotenv

# Load .env from the demo root
load_dotenv(Path(__file__).parent.parent / ".env")

from sasy.instrumentation.testing import (
    PolicyResult,
    evaluate_policy,
)


@pytest.fixture(scope="module", autouse=True)
def configure_and_upload():
    """Configure sasy and upload the current policy."""
    suffix = os.environ.get("SASY_API_KEY_SUFFIX")
    default_url = (
        "sasy.fly.dev:443" if suffix
        else "localhost:10089"
    )
    sasy_url = os.environ.get("SASY_URL", default_url)

    from sasy.auth.hooks import APIKeyAuthHook
    from sasy.config import configure

    if suffix:
        api_key = f"demo-key-{suffix}"
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
        configure(
            url="localhost:10089",
            ca_path="certs/ca.crt",
            cert_path="certs/client.crt",
            key_path="certs/client.key",
            auth_hook=APIKeyAuthHook(
                api_key="admin-test-key"
            ),
        )

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


# ── Cancellation matrix ──────────────────────────────
#
# | Tier    | No Insurance | With Insurance |
# |---------|-------------|----------------|
# | Regular | DENY        | ALLOW          |
# | Silver  | DENY        | ALLOW          |
# | Gold    | ALLOW       | ALLOW          |

CANCEL_MATRIX = [
    ("regular", "no", False),
    ("regular", "yes", True),
    ("silver", "no", False),
    ("silver", "yes", True),
    ("gold", "no", True),
    ("gold", "yes", True),
]


@pytest.mark.parametrize(
    "membership,insurance,expected",
    CANCEL_MATRIX,
    ids=[
        f"cancel-{m}-ins_{i}"
        for m, i, _ in CANCEL_MATRIX
    ],
)
def test_cancellation(
    membership: str,
    insurance: str,
    expected: bool,
) -> None:
    """Test cancellation policy matrix cell."""
    result = evaluate_policy(
        tool_name="cancel_reservation",
        tool_args={"reservation_id": "TEST001"},
        tool_results={
            "get_reservation_details": {
                "reservation_id": "TEST001",
                "insurance": insurance,
                "membership": membership,
                "cabin": "economy",
            },
        },
    )
    assert result.authorized == expected, (
        f"{membership}/insurance={insurance}: "
        f"expected {'ALLOW' if expected else 'DENY'}, "
        f"got {'ALLOW' if result.authorized else 'DENY'}"
        f" reasons={result.reasons}"
    )


# ── Modification matrix ──────────────────────────────
#
# | Tier    | Basic Economy | Economy |
# |---------|--------------|---------|
# | Regular | DENY         | ALLOW   |
# | Silver  | ALLOW        | ALLOW   |
# | Gold    | ALLOW        | ALLOW   |

MODIFY_MATRIX = [
    ("regular", "basic_economy", False),
    ("regular", "economy", True),
    ("silver", "basic_economy", True),
    ("silver", "economy", True),
    ("gold", "basic_economy", True),
    ("gold", "economy", True),
]


@pytest.mark.parametrize(
    "membership,cabin,expected",
    MODIFY_MATRIX,
    ids=[
        f"modify-{m}-{c}"
        for m, c, _ in MODIFY_MATRIX
    ],
)
def test_modification(
    membership: str,
    cabin: str,
    expected: bool,
) -> None:
    """Test modification policy matrix cell."""
    result = evaluate_policy(
        tool_name="update_reservation_flights",
        tool_args={
            "reservation_id": "TEST002",
            "cabin": cabin,
            "flights": json.dumps(
                [
                    {
                        "flight_number": "HAT001",
                        "date": "2024-05-18",
                    }
                ]
            ),
        },
        tool_results={
            "get_reservation_details": {
                "reservation_id": "TEST002",
                "insurance": "no",
                "membership": membership,
                "cabin": cabin,
            },
        },
    )
    assert result.authorized == expected, (
        f"{membership}/{cabin}: "
        f"expected {'ALLOW' if expected else 'DENY'}, "
        f"got {'ALLOW' if result.authorized else 'DENY'}"
        f" reasons={result.reasons}"
    )


# ── Guard rule tests ─────────────────────────────────

class TestGuardRules:
    """Verify guard rules deny when lookup is missing."""

    def test_cancel_without_lookup(self) -> None:
        """Cancel without get_reservation_details."""
        result = evaluate_policy(
            tool_name="cancel_reservation",
            tool_args={"reservation_id": "TEST003"},
        )
        assert not result.authorized
        assert any(
            "look up" in r.lower()
            for r in result.reasons
        ), f"Expected guard message: {result.reasons}"

    def test_modify_without_lookup(self) -> None:
        """Modify without get_reservation_details."""
        result = evaluate_policy(
            tool_name="update_reservation_flights",
            tool_args={"reservation_id": "TEST004"},
        )
        assert not result.authorized
        assert any(
            "look up" in r.lower()
            for r in result.reasons
        ), f"Expected guard message: {result.reasons}"

    def test_lookup_always_allowed(self) -> None:
        """Read-only lookups are always authorized."""
        result = evaluate_policy(
            tool_name="get_reservation_details",
            tool_args={"reservation_id": "TEST005"},
        )
        assert result.authorized
