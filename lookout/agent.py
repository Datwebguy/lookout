"""Decision policy — the LLM reasons over real FortyGuard signals via tool-use and
returns a structured, personalized heat-safety decision (PRD FR3, architecture.md §Agent).

Genuine tool-use: the model decides which real signals to pull and in what order, not a
hardcoded pipeline. Uses OpenAI's Responses API. Two phases per decision, because the
Responses API treats `tools` and structured-output `text.format` as mutually exclusive in
a single call (unlike Claude's combined pattern, which this project originally used —
see memory.md): (1) a tool-use gathering loop until the model stops calling tools, then
(2) one final call, grounded in that same conversation, constrained to the decision schema.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import date, timedelta

from fortyguard import FortyGuardClient
from openai import OpenAI

from .sites import Site
from .signals import (
    SignalUnavailableError,
    area_weighted_mean_temperature,
    duration_signal,
    historical_analog_forward,
    most_recent_available_date,
)

MODEL = "gpt-5.6-luna"

DECISION_SCHEMA = {
    "type": "object",
    "properties": {
        "risk_level": {"type": "string", "enum": ["low", "moderate", "high", "extreme"]},
        "recommended_action": {"type": "string"},
        "timing": {"type": "string"},
        "rationale": {"type": "string"},
    },
    "required": ["risk_level", "recommended_action", "timing", "rationale"],
    "additionalProperties": False,
}

SYSTEM_PROMPT = (
    "You are Lookout, an autonomous heat-safety agent protecting an outdoor worker from "
    "extreme heat. Reason only from REAL data you pull yourself via the provided tools — "
    "never invent or guess a temperature or duration. At site scale, peak temperature is "
    "nearly flat; DURATION above a danger threshold is what actually separates a dangerous "
    "day from a normal one, so weigh the exceedance-duration signal heavily, not just the "
    "current or projected temperature. Personalize your decision to the specific worker "
    "profile given (role, shift hours, risk flags) — the same weather should produce a "
    "different decision for a construction laborer with no shade than for a delivery "
    "driver with a cardiac history. Call whichever tools you need, in whatever order makes "
    "sense, before producing your final decision."
)


@dataclass
class Decision:
    risk_level: str
    recommended_action: str
    timing: str
    rationale: str
    site_id: str
    site_name: str
    worker_role: str
    # Every real tool call the agent made to reach this decision — {"tool", "args", "result"}
    # per call — so the decision log can show the real inputs, not just the LLM's prose
    # (PRD FR6). Never fabricated: populated only from actual FortyGuard-backed tool results.
    real_inputs: list[dict] = field(default_factory=list)


def _make_tools(client: FortyGuardClient, site: Site, anchor_date: str, baseline_years: list[int]):
    """Real tool executors bound to one site — each call makes a genuine FortyGuard
    request via the signals layer. The model decides which of these to call and when.
    """

    def get_current_temperature(hour: str) -> str:
        try:
            temp = area_weighted_mean_temperature(client, site.site_polygon, anchor_date, hour)
            return json.dumps({"celsius": round(temp, 2), "date": anchor_date, "hour": hour})
        except SignalUnavailableError as exc:
            return json.dumps({"error": str(exc)})

    def get_forward_and_baseline(anchor_hour: str, target_hour: str) -> str:
        try:
            fwd = historical_analog_forward(
                client, site.site_polygon,
                target_date=anchor_date, target_hour_time=target_hour,
                anchor_date=anchor_date, anchor_hour_time=anchor_hour,
                years=baseline_years,
            )
            return json.dumps({
                "baseline_now_celsius": round(fwd.baseline_anchor_celsius, 2),
                "actual_now_celsius": round(fwd.actual_anchor_celsius, 2),
                "anomaly_celsius": round(fwd.anomaly_celsius, 2),
                "baseline_target_celsius": round(fwd.baseline_target_celsius, 2),
                "projected_target_celsius": round(fwd.projected_celsius, 2),
                "target_hour": target_hour,
            })
        except SignalUnavailableError as exc:
            return json.dumps({"error": str(exc)})

    def get_exceedance_duration(days: int, threshold_celsius: float) -> str:
        try:
            end_date = anchor_date
            start_date = (date.fromisoformat(anchor_date) - timedelta(days=days - 1)).isoformat()
            hours = duration_signal(
                client, site.site_polygon, start_date, end_date,
                threshold=threshold_celsius, direction="above", analytic_type="exceedance",
            )
            return json.dumps({
                "exceedance_hours": round(hours, 2), "window_days": days,
                "threshold_celsius": threshold_celsius,
            })
        except SignalUnavailableError as exc:
            return json.dumps({"error": str(exc)})

    tool_defs = [
        {
            "type": "function",
            "name": "get_current_temperature",
            "description": (
                "Real hyperlocal area-weighted temperature (°C) for this exact worksite "
                "at a given hour on the anchor date."
            ),
            "parameters": {
                "type": "object",
                "properties": {"hour": {"type": "string", "description": "HH:MM, 24h"}},
                "required": ["hour"],
                "additionalProperties": False,
            },
            "strict": True,
        },
        {
            "type": "function",
            "name": "get_forward_and_baseline",
            "description": (
                "Real historical-analog projection for a future hour today, plus the "
                "'normal for this hour' baseline and today's anomaly. FortyGuard has no "
                "live forecast, so this is climatology + persistence, not a live forecast."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "anchor_hour": {"type": "string", "description": "HH:MM, the current/most-recent real hour"},
                    "target_hour": {"type": "string", "description": "HH:MM, the future hour to project"},
                },
                "required": ["anchor_hour", "target_hour"],
                "additionalProperties": False,
            },
            "strict": True,
        },
        {
            "type": "function",
            "name": "get_exceedance_duration",
            "description": (
                "Real count of hours this site spent above a temperature threshold over "
                "the last N days — duration matters more than peak temperature at site scale."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "days": {"type": "integer"},
                    "threshold_celsius": {"type": "number"},
                },
                "required": ["days", "threshold_celsius"],
                "additionalProperties": False,
            },
            "strict": True,
        },
    ]

    executors = {
        "get_current_temperature": get_current_temperature,
        "get_forward_and_baseline": get_forward_and_baseline,
        "get_exceedance_duration": get_exceedance_duration,
    }
    return tool_defs, executors


def decide(
    openai_client: OpenAI,
    fortyguard_client: FortyGuardClient,
    site: Site,
    *,
    anchor_date: str | None = None,
    threshold_celsius: float = 35.0,
    baseline_years: list[int],
    max_tool_iterations: int = 6,
) -> Decision:
    anchor_date = anchor_date or most_recent_available_date().isoformat()
    tool_defs, executors = _make_tools(fortyguard_client, site, anchor_date, baseline_years)

    user_prompt = (
        f"Worker site: {site.name} (id={site.id}), lat={site.lat}, lon={site.lon}.\n"
        f"Worker profile: role={site.worker_profile.role}, "
        f"shift_hours={site.worker_profile.shift_hours}, "
        f"risk_flags={site.worker_profile.risk_flags}, notes={site.worker_profile.notes!r}.\n"
        f"Anchor date (most recent real data available): {anchor_date}. "
        f"Threshold for exceedance duration: {threshold_celsius}°C.\n"
        "Gather the real signals you need, then produce your final heat-safety decision."
    )

    input_list: list[dict] = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": user_prompt},
    ]
    real_inputs: list[dict] = []

    # Phase 1 — tool-use gathering loop: keep going until the model stops calling tools.
    for _ in range(max_tool_iterations):
        response = openai_client.responses.create(
            model=MODEL,
            tools=tool_defs,
            input=input_list,
        )

        function_calls = [item for item in response.output if item.type == "function_call"]
        if not function_calls:
            break

        input_list += response.output
        for call in function_calls:
            executor = executors[call.name]
            args = json.loads(call.arguments)
            result = executor(**args)
            real_inputs.append({"tool": call.name, "args": args, "result": json.loads(result)})
            input_list.append({
                "type": "function_call_output",
                "call_id": call.call_id,
                "output": result,
            })
    else:
        raise RuntimeError(
            f"Agent did not stop calling tools within {max_tool_iterations} iterations"
        )

    # Phase 2 — final structured-output call, grounded in the same gathered-data history.
    input_list.append({
        "role": "user",
        "content": "Now output your final heat-safety decision as JSON matching the schema.",
    })
    final = openai_client.responses.create(
        model=MODEL,
        input=input_list,
        text={
            "format": {
                "type": "json_schema",
                "name": "heat_safety_decision",
                "strict": True,
                "schema": DECISION_SCHEMA,
            }
        },
    )

    data = json.loads(final.output_text)
    return Decision(
        **data,
        site_id=site.id,
        site_name=site.name,
        worker_role=site.worker_profile.role,
        real_inputs=real_inputs,
    )
