"""Core agent loop for the airline demo.

Uses the OpenAI SDK directly (no litellm) with SASY
reference-monitor authorization checks on every tool call.
This file is a **manual** instrumentation example —
dependency edges, event recording, and
`check_tool_call()` are wired by hand so you can see
exactly what SASY needs from an agent. For the
framework-instrumented path (one import + one call to
`sasy.instrumentation.instrument(tau2=True, ...)`
handles all of this), see
`tau2-examples/tau2_examples/cli.py` and the
tau2-airline benchmark.
"""

from __future__ import annotations

import json
import logging
from typing import Any
from uuid import uuid4

from openai import OpenAI
from openai.types.chat import (
    ChatCompletionMessage,
    ChatCompletionMessageToolCall,
)

from .config import OPENAI_MODEL
from sasy.observability.api import (
    record_events,
    record_events_with_dependencies,
)
from sasy.proto.observability_pb2 import (
    Edge,
    Event,
    Role,
    Tool,
)
from sasy.reference_monitor import check_tool_call

from .display import (
    display_agent,
    display_policy_allowed,
    display_policy_denied,
    display_scenario_header,
    display_summary,
    display_tool_call,
    display_tool_error,
    display_tool_result,
    display_user,
)
from .scenarios import Scenario
from .tools import AirlineTools

logger = logging.getLogger(__name__)

AGENT_SYSTEM_PROMPT = """\
You are a helpful customer service agent for an airline.
Use the tools available to you to help the customer with
their request. Look up reservation details, process
cancellations, modifications, and bookings as requested.

In each turn you can either:
- Send a message to the user
- Make one or more tool calls
You cannot do both at the same time.

The current time is 2024-05-15 15:00:00 EST.
"""


# ── Public API ───────────────────────────────────────────


def run_scenario(
    scenario: Scenario,
    airline_tools: AirlineTools,
    openai_tools: list[dict[str, Any]],
    model: str = OPENAI_MODEL,
    max_steps: int = 30,
) -> list[tuple[str, bool]]:
    """Run a single demo scenario end-to-end.

    Drives an OpenAI chat-completion agent through a
    multi-turn conversation with a simulated customer,
    checking every tool call against the SASY reference
    monitor.

    Args:
        scenario: The scenario to run.
        airline_tools: Toolkit with all airline methods.
        openai_tools: OpenAI function-calling schemas.
        model: OpenAI model identifier.
        max_steps: Maximum number of agent turns.

    Returns:
        A list of ``(tool_name, authorized)`` pairs
        summarising every tool call that was attempted.
    """
    client = OpenAI()
    display_scenario_header(scenario)

    system_msg = AGENT_SYSTEM_PROMPT
    messages: list[dict[str, Any]] = [
        {"role": "system", "content": system_msg},
        {
            "role": "user",
            "content": scenario.first_user_message,
        },
    ]
    display_user(scenario.first_user_message)

    tool_results: list[tuple[str, bool]] = []

    # Track graph event IDs for causal linking
    event_ids: list[str] = []

    def _record_msg(
        text: str,
        role: "Role",
        agent: str = "LLMAgent",
        derived_from_tool: Tool | None = None,
    ) -> str:
        """Record a message event in the graph."""
        eid = str(uuid4())
        kwargs: dict[str, Any] = dict(
            text=text, role=role, agent=agent, id=eid,
        )
        if derived_from_tool is not None:
            kwargs["derived_from"] = derived_from_tool
        ev = Event(**kwargs)
        if event_ids:
            edge = Edge(
                source=event_ids[-1],
                destination=eid,
                proximal=True,
            )
            record_events_with_dependencies([ev], [edge])
        else:
            record_events([ev])
        event_ids.append(eid)
        return eid

    # Record the first user message
    _record_msg(
        scenario.first_user_message, Role.USER
    )

    for _step in range(max_steps):
        response = client.chat.completions.create(
            model=model,
            messages=messages,
            tools=openai_tools,
        )
        choice = response.choices[0]
        assistant_msg = choice.message

        if assistant_msg.tool_calls:
            # ── Handle tool calls ────────────────────
            messages.append(
                _serialize_assistant(assistant_msg)
            )
            for tc in assistant_msg.tool_calls:
                fn_name = tc.function.name
                args_json = tc.function.arguments
                display_tool_call(fn_name, args_json)

                # Record agent tool-call event
                tc_eid = str(uuid4())
                tc_ev = Event(
                    text="",
                    role=Role.LLM,
                    agent="LLMAgent",
                    id=tc_eid,
                    tools=[
                        Tool(
                            name=fn_name,
                            arguments=args_json,
                        )
                    ],
                )
                if event_ids:
                    edge = Edge(
                        source=event_ids[-1],
                        destination=tc_eid,
                        proximal=True,
                    )
                    record_events_with_dependencies(
                        [tc_ev], [edge]
                    )
                else:
                    record_events([tc_ev])
                event_ids.append(tc_eid)

                # Check with policy engine
                logger.info(
                    "check_tool_call: %s "
                    "input_node_ids=%s",
                    fn_name, event_ids,
                )
                auth = check_tool_call(
                    fn_name, args_json, event_ids
                )

                if not auth.authorized:
                    denial_msg, suggestions = (
                        _extract_denial(auth)
                    )
                    display_policy_denied(
                        fn_name,
                        denial_msg,
                        suggestions,
                    )
                    content = (
                        f"[BLOCKED] {fn_name}: "
                        f"{denial_msg}"
                    )
                    tool_results.append(
                        (fn_name, False)
                    )
                else:
                    result = execute_tool(
                        airline_tools,
                        fn_name,
                        args_json,
                    )
                    display_policy_allowed(fn_name)
                    display_tool_result(result)
                    content = result
                    tool_results.append(
                        (fn_name, True)
                    )

                # Record tool result event (with
                # derived_from so ToolResult relation
                # is populated in the policy engine)
                _record_msg(
                    content,
                    Role.AGENT,
                    derived_from_tool=Tool(
                        name=fn_name,
                        arguments=args_json,
                    ),
                )

                messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": tc.id,
                        "content": content,
                    }
                )
        else:
            # ── Handle text response ─────────────────
            text = assistant_msg.content or ""
            display_agent(text)
            messages.append(
                {"role": "assistant", "content": text}
            )
            _record_msg(text, Role.LLM)

            user_reply = run_user_sim(
                client, scenario, messages, model=model
            )
            if "###STOP###" in user_reply:
                break
            display_user(user_reply)
            messages.append(
                {"role": "user", "content": user_reply}
            )
            _record_msg(user_reply, Role.USER)

    if scenario.expected_denial is not None:
        # Check if the expected tool was denied
        had_denial = any(
            fn == scenario.expected_denial and not auth
            for fn, auth in tool_results
        )
    else:
        # Check if any tool was denied WITHOUT a later
        # successful retry of the same tool
        denied_tools = set()
        allowed_tools = set()
        for fn, auth in tool_results:
            if auth:
                allowed_tools.add(fn)
            else:
                denied_tools.add(fn)
        # A tool that was denied then later allowed
        # (guard rule → retry) is not a real denial
        had_denial = bool(
            denied_tools - allowed_tools
        )
    display_summary(scenario, had_denial)
    return tool_results


# ── User simulator ───────────────────────────────────────


_USER_SIM_SYSTEM = """\
You are simulating a customer calling an airline.
{instructions}

Respond naturally as the customer would. \
Keep responses concise.
If your issue is resolved or the agent cannot help, \
respond with ###STOP###.
"""


def run_user_sim(
    client: OpenAI,
    scenario: Scenario,
    messages: list[dict[str, Any]],
    model: str = OPENAI_MODEL,
) -> str:
    """Generate the next user message via an LLM sim.

    Flips conversation roles so the simulator sees agent
    messages as ``user`` and its own prior replies as
    ``assistant``.

    Args:
        client: OpenAI client instance.
        scenario: Current scenario (for sim instructions).
        messages: Full conversation history so far.
        model: OpenAI model identifier.

    Returns:
        The simulated customer's next message.
    """
    sim_system = _USER_SIM_SYSTEM.format(
        instructions=scenario.user_sim_instructions,
    )
    sim_messages: list[dict[str, Any]] = [
        {"role": "system", "content": sim_system},
    ]

    for msg in messages:
        role = msg.get("role")
        content = msg.get("content") or ""
        if not content:
            continue  # Skip tool calls, system, empty
        if role == "assistant":
            sim_messages.append(
                {"role": "user", "content": content}
            )
        elif role == "user":
            sim_messages.append(
                {
                    "role": "assistant",
                    "content": content,
                }
            )

    response = client.chat.completions.create(
        model=model,
        messages=sim_messages,
        temperature=0.3,
    )
    return response.choices[0].message.content or ""


# ── Tool execution ───────────────────────────────────────


def execute_tool(
    airline_tools: AirlineTools,
    fn_name: str,
    args_json: str,
) -> str:
    """Deserialise arguments, call the tool, return JSON.

    Args:
        airline_tools: Toolkit instance.
        fn_name: Name of the method to call.
        args_json: JSON-encoded keyword arguments.

    Returns:
        JSON-serialised tool result.
    """
    args: dict[str, Any] = json.loads(args_json)
    method = getattr(airline_tools, fn_name)
    try:
        result = method(**args)
    except Exception as exc:
        # Tool-side failures (bad input, unavailable seat, missing
        # record, …) shouldn't crash the scenario runner. Surface the
        # error visibly to the reader, then hand a structured error
        # back to the LLM so it can recover (try a different cabin,
        # pick another flight, tell the customer, …).
        error_msg = str(exc)
        display_tool_error(fn_name, error_msg)
        return json.dumps(
            {
                "error": type(exc).__name__,
                "message": error_msg,
            }
        )
    # Pydantic models must be serialized as proper JSON
    # (not repr) so policy functors like @extract_cabin
    # can parse tool result contents.
    if hasattr(result, "model_dump_json"):
        return result.model_dump_json()
    if isinstance(result, list):
        parts = []
        for item in result:
            if hasattr(item, "model_dump_json"):
                parts.append(
                    json.loads(item.model_dump_json())
                )
            else:
                parts.append(item)
        return json.dumps(parts, default=str)
    return json.dumps(result, default=str)


# ── Internal helpers ─────────────────────────────────────


def _extract_denial(
    response: Any,
) -> tuple[str, list[str]]:
    """Pull a human-readable message from a denial trace.

    Args:
        response: ``ToolCallResponse`` protobuf.

    Returns:
        A ``(message, suggestions)`` tuple.
    """
    msg = "Authorization denied"
    suggestions: list[str] = []
    if response.denial_trace:
        msg = response.denial_trace.action_description
        if response.denial_trace.reasons:
            parts = [
                r.details or str(r.reason_type)
                for r in response.denial_trace.reasons
            ]
            msg += ": " + "; ".join(parts)
        suggestions = list(
            response.denial_trace.suggested_fixes
        )
    return msg, suggestions


def _serialize_assistant(
    msg: ChatCompletionMessage,
) -> dict[str, Any]:
    """Convert an assistant message to a dict for history.

    Args:
        msg: The assistant ``ChatCompletionMessage``.

    Returns:
        A dict suitable for the messages list.
    """
    result: dict[str, Any] = {
        "role": "assistant",
        "content": msg.content,
    }
    if msg.tool_calls:
        result["tool_calls"] = [
            _serialize_tool_call(tc)
            for tc in msg.tool_calls
        ]
    return result


def _serialize_tool_call(
    tc: ChatCompletionMessageToolCall,
) -> dict[str, Any]:
    """Convert a tool call object to a plain dict.

    Args:
        tc: An OpenAI tool call object.

    Returns:
        A dict matching the expected message format.
    """
    return {
        "id": tc.id,
        "type": "function",
        "function": {
            "name": tc.function.name,
            "arguments": tc.function.arguments,
        },
    }
