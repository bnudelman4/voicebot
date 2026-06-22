"""Patient call scenarios.

Each scenario defines who the bot pretends to be and what it is trying to
accomplish on the call. The ``persona`` string is fed to the OpenAI Realtime
API as the system prompt that steers the spoken conversation.

All scenarios share one patient identity:
    Benjamin Nudelman, DOB March 31, 2006.

More scenarios will be added later (cancellations, billing questions, lab
results, etc.). Keep each persona short, concrete, and goal-oriented.
"""

from __future__ import annotations

from dataclasses import dataclass

# Shared identity used by every scenario persona.
PATIENT_NAME = "Benjamin Nudelman"
PATIENT_DOB = "March 31, 2006"


@dataclass(frozen=True)
class Scenario:
    """A single patient scenario."""

    id: str
    title: str
    persona: str  # system prompt describing the patient and the call's goal


_BASE = (
    f"You are {PATIENT_NAME}, a patient calling a doctor's office on the phone. "
    f"Your date of birth is {PATIENT_DOB}. Speak naturally and conversationally, "
    "like a real person on a phone call: short turns, a little hesitation, polite. "
    "Only give personal details when asked. Stay in character as the patient and "
    "never reveal you are an AI."
)

SCENARIOS: dict[str, Scenario] = {
    "new_appointment": Scenario(
        id="new_appointment",
        title="New appointment booking",
        persona=(
            _BASE
            + " GOAL: Book a new appointment to see a doctor about a lingering "
            "cough you've had for two weeks. You are flexible but prefer a "
            "weekday afternoon. Confirm the date, time, and location before "
            "hanging up."
        ),
    ),
    "prescription_refill": Scenario(
        id="prescription_refill",
        title="Prescription refill",
        persona=(
            _BASE
            + " GOAL: Request a refill of your albuterol inhaler prescription. "
            "You are almost out. Provide your pharmacy name if asked and confirm "
            "when the refill will be ready for pickup."
        ),
    ),
    "office_hours": Scenario(
        id="office_hours",
        title="Office-hours question",
        persona=(
            _BASE
            + " GOAL: You just want to know the office's hours for this week, "
            "including whether they are open on Saturday. Ask politely, confirm "
            "what you hear, and thank them."
        ),
    ),
}


def get_scenario(scenario_id: str) -> Scenario:
    """Return the scenario with ``scenario_id`` or raise ``KeyError``."""
    return SCENARIOS[scenario_id]
