"""Milestone 4 — decision policy live proof.

Runs the real LLM decision agent (lookout/agent.py) against real FortyGuard signals for
registered sites, then proves the core hackathon claim: the SAME site yields a different
decision for a different worker profile. Run with:
    PYTHONPATH=<repo root> python scripts/milestone4_agent_proof.py
"""

from __future__ import annotations

import copy
import sys
from dataclasses import asdict
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

from fortyguard import FortyGuardClient  # noqa: E402
from fortyguard.exceptions import FortyGuardError  # noqa: E402
from openai import OpenAI  # noqa: E402
from lookout.agent import Decision, decide  # noqa: E402
from lookout.sites import load_sites  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parent.parent
SITES_PATH = REPO_ROOT / "lookout" / "data" / "sites.json"

BASELINE_YEARS = [2024, 2025]  # trimmed from full 2021-present to bound demo API credits


def section(title: str) -> None:
    print("\n" + "=" * 70)
    print(title)
    print("=" * 70)


def print_decision(label: str, decision: Decision) -> None:
    print(f"\n{label}")
    print(f"  site: {decision.site_name} ({decision.site_id})")
    print(f"  worker_role: {decision.worker_role}")
    print(f"  risk_level: {decision.risk_level}")
    print(f"  recommended_action: {decision.recommended_action}")
    print(f"  timing: {decision.timing}")
    print(f"  rationale: {decision.rationale}")


def main() -> int:
    try:
        fg_client = FortyGuardClient()
    except FortyGuardError as exc:
        print(f"FAIL: could not construct FortyGuard client — {exc}", file=sys.stderr)
        return 1

    openai_client = OpenAI()  # reads OPENAI_API_KEY

    sites = load_sites(SITES_PATH)
    site_construction = next(s for s in sites if s.id == "phx-construction-01")
    site_delivery = next(s for s in sites if s.id == "phx-delivery-01")

    section("TEST A — construction site, its own real worker profile")
    decision_a = decide(
        openai_client, fg_client, site_construction,
        baseline_years=BASELINE_YEARS,
    )
    print_decision("Decision A", decision_a)

    section("TEST B — SAME construction site polygon, delivery driver's profile swapped in")
    swapped_site = copy.deepcopy(site_construction)
    swapped_site.worker_profile = site_delivery.worker_profile
    decision_b = decide(
        openai_client, fg_client, swapped_site,
        baseline_years=BASELINE_YEARS,
    )
    print_decision("Decision B (same location as A, different profile)", decision_b)

    section("TEST C — delivery site, its own real worker profile (second real site)")
    decision_c = decide(
        openai_client, fg_client, site_delivery,
        baseline_years=BASELINE_YEARS,
    )
    print_decision("Decision C", decision_c)

    section("COMPARISON — A vs B (same site, different profile)")
    same_risk = decision_a.risk_level == decision_b.risk_level
    same_action = decision_a.recommended_action.strip().lower() == decision_b.recommended_action.strip().lower()
    print(f"risk_level:           A={decision_a.risk_level!r}  B={decision_b.risk_level!r}  {'SAME' if same_risk else 'DIFFERENT'}")
    print(f"recommended_action:   {'SAME text' if same_action else 'DIFFERENT text'}")
    if same_risk and same_action:
        print(
            "WARNING: A and B are identical on both fields — personalization may not be "
            "taking effect. Inspect the rationale text above.",
            file=sys.stderr,
        )
    else:
        print("CONFIRMED: the same site produced a different decision for a different worker profile.")

    section("DONE")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
