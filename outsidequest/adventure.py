"""Mission generation through Ollama, with a safe built-in fallback."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from typing import Any

import requests

from outsidequest.models import (
    Mission,
    MissionValidationError,
    Preferences,
    mission_from_payload,
)

DEFAULT_OLLAMA_URL = "http://localhost:11434"
DEFAULT_MODEL = "qwen2.5:3b"
SYSTEM_PROMPT = (
    "You are OutsideQuest, a careful real-world adventure planner. Return only one JSON "
    "object with exactly these keys: title (string), reason (string), steps (array of 3 to "
    "6 concise strings), duration_minutes (integer), estimated_cost (number), and "
    "safety_tip (string). Never name a venue, route, street, business, landmark, or other "
    "specific place. Never state or imply that a place is nearby, open, accessible, or "
    "available. Do not use phrases such as 'local park' or 'nearby park'. When needed, "
    "say only 'a familiar public place the user chooses'. "
    "Never invent local conditions, weather, or opening hours. Never suggest trespassing, "
    "entering restricted/private/abandoned places, risky climbing, unsafe roads, interacting "
    "with wildlife, or going somewhere isolated. Prefer gentle, permitted activities; for "
    "low energy, choose a gentle or seated activity. Follow the user's available time and "
    "budget exactly. Keep the response concise and practical."
)


class OllamaError(RuntimeError):
    """An actionable error communicating with or interpreting Ollama."""


@dataclass(frozen=True)
class GenerationResult:
    mission: Mission
    source: str
    notice: str | None = None


class OllamaClient:
    def __init__(
        self,
        base_url: str = DEFAULT_OLLAMA_URL,
        model: str = DEFAULT_MODEL,
        timeout: tuple[float, float] = (3.0, 45.0),
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.timeout = timeout

    @classmethod
    def from_environment(cls) -> OllamaClient:
        return cls(
            base_url=os.getenv("OUTSIDEQUEST_OLLAMA_URL", DEFAULT_OLLAMA_URL),
            model=os.getenv("OUTSIDEQUEST_OLLAMA_MODEL", DEFAULT_MODEL),
        )

    def generate(self, preferences: Preferences) -> Mission:
        prompt = _build_prompt(preferences)
        try:
            response = requests.post(
                f"{self.base_url}/api/generate",
                json={
                    "model": self.model,
                    "prompt": prompt,
                    "system": SYSTEM_PROMPT,
                    "stream": False,
                    "format": "json",
                    "options": {"temperature": 0.2},
                },
                timeout=self.timeout,
            )
            response.raise_for_status()
        except requests.RequestException as exc:
            raise OllamaError(
                "Ollama could not be reached or did not finish in time. "
                "Check that Ollama is running and the selected model is installed."
            ) from exc

        try:
            body = response.json()
        except requests.exceptions.JSONDecodeError as exc:
            raise OllamaError("Ollama returned an invalid response.") from exc

        if not isinstance(body, dict) or not isinstance(body.get("response"), str):
            raise OllamaError("Ollama's response did not contain generated text.")

        try:
            payload = json.loads(body["response"])
        except json.JSONDecodeError as exc:
            raise OllamaError("The model did not return the requested JSON format.") from exc

        if not isinstance(payload, dict):
            raise OllamaError("The model returned a mission in an unexpected format.")
        return mission_from_payload(payload, preferences)


def generate_adventure(
    preferences: Preferences,
    client: OllamaClient | None = None,
    fallback_variant: int = 0,
) -> GenerationResult:
    """Use Ollama when possible; identify every built-in result as fallback."""
    ollama = client or OllamaClient.from_environment()
    try:
        return GenerationResult(mission=ollama.generate(preferences), source="ollama")
    except (OllamaError, MissionValidationError) as exc:
        return GenerationResult(
            mission=create_fallback_mission(preferences, fallback_variant),
            source="fallback",
            notice=str(exc),
        )


def create_fallback_mission(preferences: Preferences, variant: int = 0) -> Mission:
    interest = preferences.interests[0] if preferences.interests else "curiosity"
    if preferences.activity_type == "Outside":
        ideas = [
            (
                "Follow a familiar path with fresh eyes",
                "Take a gentle walk on a route you already know, and notice three details "
                f"connected to {interest}. Choose a public, open route and turn back whenever "
                "you like.",
                [
                    "Pick a familiar public route that feels comfortable today.",
                    f"Walk at an easy pace and look for three small details related to {interest}.",
                    "Pause somewhere safe to jot down or remember your favorite detail.",
                ],
                "Stay on public paths, check local conditions, and head home if the route "
                "or weather feels uncomfortable.",
            ),
            (
                "Take a five-senses fresh-air break",
                "A low-pressure outdoor reset can make an ordinary day feel more vivid, "
                f"with a little attention to {interest}.",
                [
                    "Choose a familiar outdoor spot that is open to visitors.",
                    "Notice one thing you can see, hear, smell, and feel without touching plants or wildlife.",
                    "Finish with a comfortable stroll back the way you came.",
                ],
                "Use a public, well-used route, keep a comfortable distance from wildlife, "
                "and follow posted guidance.",
            ),
        ]
    elif preferences.activity_type == "Inside":
        ideas = [
            (
                "Make a tiny at-home discovery",
                f"Turn {interest} into a relaxed mini-project using things you already have.",
                [
                    f"Choose one small question or idea about {interest} to explore.",
                    "Spend a few minutes sketching, reading, organizing, or making something with supplies on hand.",
                    "Write down one thing you would like to try next time.",
                ],
                "Use familiar household supplies safely, and skip anything that needs special tools or purchases.",
            ),
            (
                "Build a cozy curiosity playlist",
                f"Explore {interest} without leaving home or needing to spend anything.",
                [
                    f"Pick three songs, short readings, or saved resources connected to {interest}.",
                    "Enjoy them away from your usual scrolling spot.",
                    "Save one favorite idea in your journal for another day.",
                ],
                "Keep the activity comfortable and take a screen break whenever you need one.",
            ),
        ]
    else:
        ideas = [
            (
                "Notice a small wonder, anywhere",
                f"Find a simple, screen-free moment around {interest}, at home or somewhere public.",
                [
                    "Choose a comfortable place you already have permission to use.",
                    f"Spend a few minutes noticing one detail connected to {interest}.",
                    "Make a quick note or sketch about what caught your attention.",
                ],
                "Stay in familiar, permitted spaces and avoid approaching wildlife or entering restricted areas.",
            ),
            (
                "Take your curiosity on a short loop",
                f"Give {interest} a little space in your day with an easy activity that works indoors or out.",
                [
                    "Pick a familiar, comfortable spot indoors or on an open public route.",
                    f"Look for a small detail related to {interest}, without needing to buy anything.",
                    "Pause and capture the moment in a sentence or quick sketch.",
                ],
                "Choose a setting that feels safe and accessible; follow posted rules and turn back whenever you want.",
            ),
        ]

    title, reason, steps, safety_tip = ideas[variant % len(ideas)]
    duration = min(preferences.available_minutes, 30)
    return Mission(
        title=title,
        reason=reason,
        steps=steps,
        duration_minutes=duration,
        estimated_cost=0.0,
        safety_tip=safety_tip,
    )


def _build_prompt(preferences: Preferences) -> str:
    safe_preferences: dict[str, Any] = {
        "available_minutes": preferences.available_minutes,
        "energy_level": preferences.energy_level,
        "interests": preferences.interests,
        "budget": preferences.budget,
        "activity_type": preferences.activity_type,
    }
    return (
        "Create one short, practical, enjoyable real-world adventure mission for the user. "
        "Estimated cost is in the user's local currency units. Fit the energy, interests, "
        "budget and activity preference exactly. "
        f"The user has exactly {preferences.available_minutes} minutes and a budget of "
        f"{preferences.budget:g}; duration_minutes must be a whole number from 1 to "
        f"{preferences.available_minutes}, and estimated_cost must not exceed "
        f"{preferences.budget:g}. "
        f"User preferences: {json.dumps(safe_preferences, ensure_ascii=False)}"
    )
