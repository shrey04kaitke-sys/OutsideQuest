"""Typed domain models and input/output validation for OutsideQuest."""

from __future__ import annotations

import math
import re
from dataclasses import asdict, dataclass
from typing import Any
from uuid import uuid4

ALLOWED_ENERGY_LEVELS = {"Low", "Medium", "High"}
ALLOWED_ACTIVITY_TYPES = {"Outside", "Inside", "Either"}
UNSAFE_PHRASES = (
    "trespass",
    "trespassing",
    "break into",
    "abandoned building",
    "entering restricted",
    "restricted area",
    "private property",
    "without permission",
    "climb onto",
    "climb a roof",
    "cross a busy road",
    "swim alone",
    "approach wildlife",
    "feed wildlife",
    "isolated area",
    "unlit route",
)
UNVERIFIED_PLACE_PHRASES = (
    "local park",
    "botanical garden",
    "nearby",
    "near you",
    "in your area",
    "open daily",
    "open every day",
    "open until",
    "closes at",
    "the nearest",
)
UNVERIFIED_PLACE_PATTERN = re.compile(
    r"\b(?i:visit|meet at|go to|walk to|head to|travel to|stop at|in|at|near)\s+"
    r"(?:(?:the|a|an)\s+)?"
    r"((?:[A-Z][A-Za-z'-]*|[A-Z]{2,})(?:\s+(?:[A-Z][A-Za-z'-]*|[A-Z]{2,})){0,3})\b"
)
NATURE_COLLECTION_PATTERN = re.compile(
    r"\b(?:collect|pick|take|remove|gather)\s+"
    r"(?:(?:items?|things?)\s+such\s+as\s+)?"
    r"(?:(?:a|an|the)\s+)?"
    r"(?:leaves?|flowers?|feathers?|seeds?|stones?|rocks?|shells?|plants?|mushrooms?)\b"
    r"(?!\s+(?:photo|picture|photograph|image)\b)"
)
GENERIC_PLACE_WORDS = {
    "beach",
    "cafe",
    "center",
    "centre",
    "garden",
    "home",
    "lake",
    "library",
    "market",
    "museum",
    "neighborhood",
    "park",
    "river",
    "square",
    "trail",
}


class MissionValidationError(ValueError):
    """A preference or generated mission is outside safe supported bounds."""


@dataclass(frozen=True)
class Preferences:
    available_minutes: int
    energy_level: str
    interests: list[str]
    budget: float
    activity_type: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class Mission:
    title: str
    reason: str
    steps: list[str]
    duration_minutes: int
    estimated_cost: float
    safety_tip: str
    id: str = ""

    def __post_init__(self) -> None:
        if not self.id:
            object.__setattr__(self, "id", str(uuid4()))

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def validate_preferences(
    available_minutes: object,
    energy_level: object,
    interests: object,
    budget: object,
    activity_type: object,
) -> Preferences:
    if (
        isinstance(available_minutes, bool)
        or not isinstance(available_minutes, int)
        or not 5 <= available_minutes <= 480
    ):
        raise MissionValidationError("Available time must be between 5 and 480 minutes.")
    if not isinstance(energy_level, str) or energy_level not in ALLOWED_ENERGY_LEVELS:
        raise MissionValidationError("Choose a valid energy level.")
    if not isinstance(activity_type, str) or activity_type not in ALLOWED_ACTIVITY_TYPES:
        raise MissionValidationError("Choose Outside, Inside, or Either.")
    if isinstance(budget, bool) or not isinstance(budget, (int, float)):
        raise MissionValidationError("Budget must be a non-negative amount.")
    if not math.isfinite(float(budget)) or not 0 <= float(budget) <= 10000:
        raise MissionValidationError("Budget must be between 0 and 10,000.")
    if not isinstance(interests, (list, tuple)) or not interests:
        raise MissionValidationError("Choose or enter at least one interest.")

    clean_interests: list[str] = []
    for interest in interests:
        if not isinstance(interest, str):
            raise MissionValidationError("Interests must be text.")
        clean = interest.strip()
        if not clean:
            continue
        if len(clean) > 60:
            raise MissionValidationError("Each interest must be 60 characters or fewer.")
        if clean not in clean_interests:
            clean_interests.append(clean)
    if not clean_interests:
        raise MissionValidationError("Choose or enter at least one interest.")

    return Preferences(
        available_minutes=available_minutes,
        energy_level=energy_level,
        interests=clean_interests,
        budget=float(budget),
        activity_type=activity_type,
    )


def mission_from_payload(payload: dict[str, Any], preferences: Preferences) -> Mission:
    title = _required_text(payload, "title", 100)
    reason = _required_text(payload, "reason", 500)
    safety_tip = _required_text(payload, "safety_tip", 400)

    steps = payload.get("steps")
    if (
        not isinstance(steps, list)
        or not 3 <= len(steps) <= 6
        or any(not isinstance(step, str) or not step.strip() or len(step.strip()) > 220 for step in steps)
    ):
        raise MissionValidationError("The model returned invalid mission steps.")

    duration = payload.get("duration_minutes")
    if (
        isinstance(duration, bool)
        or not isinstance(duration, int)
        or not 1 <= duration <= preferences.available_minutes
    ):
        raise MissionValidationError("The model returned a duration outside your available time.")

    cost = payload.get("estimated_cost")
    if (
        isinstance(cost, bool)
        or not isinstance(cost, (int, float))
        or not math.isfinite(float(cost))
        or not 0 <= float(cost) <= preferences.budget
    ):
        raise MissionValidationError("The model returned a cost outside your budget.")

    combined_text = " ".join([title, reason, safety_tip, *steps]).casefold()
    if any(re.search(rf"\b{re.escape(phrase)}\b", combined_text) for phrase in UNSAFE_PHRASES):
        raise MissionValidationError("The model suggested an activity that did not meet safety guidelines.")
    if NATURE_COLLECTION_PATTERN.search(combined_text):
        raise MissionValidationError(
            "The model suggested touching or collecting natural objects; observe them without disturbing them."
        )
    if any(phrase in combined_text for phrase in UNVERIFIED_PLACE_PHRASES):
        raise MissionValidationError(
            "The model included an unsupported local place or availability detail."
        )
    interests = {interest.casefold() for interest in preferences.interests}
    named_place = next(
        (
            match.group(1)
            for match in UNVERIFIED_PLACE_PATTERN.finditer(" ".join([reason, *steps]))
            if match.group(1).casefold() not in GENERIC_PLACE_WORDS | interests
        ),
        None,
    )
    if named_place:
        raise MissionValidationError(
            "The model named a place that cannot be verified from your preferences."
        )

    return Mission(
        title=title,
        reason=reason,
        steps=[step.strip() for step in steps],
        duration_minutes=duration,
        estimated_cost=float(cost),
        safety_tip=safety_tip,
    )


def _required_text(payload: dict[str, Any], key: str, max_length: int) -> str:
    value = payload.get(key)
    if not isinstance(value, str) or not value.strip() or len(value.strip()) > max_length:
        raise MissionValidationError(f"The model returned an invalid {key.replace('_', ' ')}.")
    return value.strip()
