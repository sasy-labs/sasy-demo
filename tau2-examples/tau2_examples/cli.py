"""Run tau2 benchmarks against the SASY cloud service.

Uses API-key auth over gRPC+TLS (Fly.io's h2_backend).
By default targets ``sasy.fly.dev:443`` and builds the
key from ``SASY_API_KEY_SUFFIX`` (``demo-key-<suffix>``)
— the same convention as ``src/demo/main.py``. Set
``SASY_API_KEY`` to override, or ``SASY_URL`` to point
at a different endpoint.

Usage::

    SASY_API_KEY_SUFFIX=<your-suffix> \
    uv run tau2-instrumented run \
        --domain airline --num-tasks 1 --max-steps 10
"""

import logging
import os
from typing import Any

from dotenv import load_dotenv

load_dotenv()
load_dotenv(".env-credentials", override=True)

# litellm complains without any OpenAI-ish key even
# when the agent uses Azure/Vertex.
if not os.environ.get("AZURE_API_KEY") and not os.environ.get("OPENAI_API_KEY"):
    os.environ["OPENAI_API_KEY"] = "fake"

logger = logging.getLogger(__name__)


def feedback_callback(
    accumulator: Any,
    output: Any,
    _: Any,
) -> None:
    """Log + append authorization feedback to the agent response."""
    if accumulator.has_denials():
        feedback_msg = accumulator.format_for_llm()
        logger.warning("POLICY VIOLATION DETECTED:\n%s", feedback_msg)
        if output is not None:
            original = output.content or ""
            output.content = original + f"\n\n{feedback_msg}"


def run() -> None:
    """Entry point for the instrumented tau2 CLI (cloud-backed)."""
    os.environ["TAU2_SKIP_NL_POLICY"] = "1"

    api_key = os.environ.get("SASY_API_KEY")
    if not api_key:
        suffix = os.environ.get("SASY_API_KEY_SUFFIX", "")
        if not suffix:
            raise RuntimeError(
                "Set SASY_API_KEY or SASY_API_KEY_SUFFIX"
            )
        api_key = f"demo-key-{suffix}"

    sasy_url = os.environ.get("SASY_URL", "sasy.fly.dev:443")

    from sasy.auth.hooks import APIKeyAuthHook
    from sasy.config import configure as sasy_configure

    sasy_configure(
        url=sasy_url,
        ca_path="",
        cert_path="",
        key_path="",
        auth_hook=APIKeyAuthHook(api_key=api_key),
    )

    import sasy.instrumentation as instrumentation
    instrumentation.configure(
        log_denials=True,
        log_policy_decisions=True,
        feedback_callback=feedback_callback,
    )
    instrumentation.instrument(tau2=True, http=False)

    from tau2.cli import main
    main()


if __name__ == "__main__":
    run()
