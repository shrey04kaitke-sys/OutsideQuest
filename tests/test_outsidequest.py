from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

import requests

from outsidequest.adventure import (
    OllamaClient,
    OllamaError,
    create_fallback_mission,
    generate_adventure,
)
from outsidequest.models import (
    MissionValidationError,
    mission_from_payload,
    validate_preferences,
)
from outsidequest.storage import (
    StorageError,
    add_journal_entry,
    complete_mission,
    load_data,
)


def preferences(**overrides: object):
    values: dict[str, object] = {
        "available_minutes": 30,
        "energy_level": "Medium",
        "interests": ["Nature"],
        "budget": 0,
        "activity_type": "Outside",
    }
    values.update(overrides)
    return validate_preferences(**values)


def valid_mission(**overrides: object) -> dict[str, object]:
    payload: dict[str, object] = {
        "title": "Notice the little things",
        "reason": "A calm, simple way to reset.",
        "steps": ["Choose a familiar spot.", "Notice three details.", "Write one down."],
        "duration_minutes": 20,
        "estimated_cost": 0,
        "safety_tip": "Stay in public places and follow posted guidance.",
    }
    payload.update(overrides)
    return payload


class PreferenceValidationTests(unittest.TestCase):
    def test_accepts_clean_preferences(self) -> None:
        result = preferences(interests=[" Nature ", "Nature", "Sketching"])
        self.assertEqual(result.interests, ["Nature", "Sketching"])

    def test_rejects_time_outside_supported_range(self) -> None:
        with self.assertRaises(MissionValidationError):
            preferences(available_minutes=0)

    def test_rejects_empty_interests_and_invalid_budget(self) -> None:
        with self.assertRaises(MissionValidationError):
            preferences(interests=[" ", ""])
        with self.assertRaises(MissionValidationError):
            preferences(budget=float("inf"))


class MissionValidationTests(unittest.TestCase):
    def test_accepts_mission_within_preferences(self) -> None:
        mission = mission_from_payload(valid_mission(), preferences())
        self.assertEqual(mission.duration_minutes, 20)

    def test_rejects_over_budget_and_unsafe_missions(self) -> None:
        with self.assertRaises(MissionValidationError):
            mission_from_payload(valid_mission(estimated_cost=1), preferences())
        with self.assertRaises(MissionValidationError):
            mission_from_payload(
                valid_mission(steps=["Trespass into a closed park.", "Notice three details.", "Write one down."]),
                preferences(),
            )

    def test_rejects_invented_venue_availability(self) -> None:
        with self.assertRaisesRegex(MissionValidationError, "unsupported local place"):
            mission_from_payload(
                valid_mission(steps=["Visit a local park open daily.", "Notice three details.", "Write one down."]),
                preferences(),
            )

    def test_rejects_named_unverified_venue_but_allows_generic_park(self) -> None:
        with self.assertRaisesRegex(MissionValidationError, "named a place"):
            mission_from_payload(
                valid_mission(steps=["Visit Golden Gate Park.", "Notice three details.", "Write one down."]),
                preferences(),
            )
        mission_from_payload(
            valid_mission(steps=["Walk in the park.", "Notice three details.", "Write one down."]),
            preferences(),
        )


class OllamaTests(unittest.TestCase):
    @patch("outsidequest.adventure.requests.post")
    def test_generates_mission_from_local_ollama_response(self, post: Mock) -> None:
        post.return_value.json.return_value = {"response": json.dumps(valid_mission())}
        post.return_value.raise_for_status.return_value = None
        mission = OllamaClient().generate(preferences())
        self.assertEqual(mission.title, "Notice the little things")
        self.assertIn("/api/generate", post.call_args.args[0])

    @patch("outsidequest.adventure.requests.post", side_effect=requests.ConnectionError("offline"))
    def test_unavailable_ollama_returns_explicit_fallback(self, _post: Mock) -> None:
        result = generate_adventure(preferences())
        self.assertEqual(result.source, "fallback")
        self.assertIn("could not be reached", result.notice or "")
        self.assertEqual(result.mission.estimated_cost, 0)

    @patch("outsidequest.adventure.requests.post")
    def test_unsafe_model_output_uses_explicit_fallback(self, post: Mock) -> None:
        post.return_value.json.return_value = {
            "response": json.dumps(
                valid_mission(steps=["Enter a restricted area.", "Notice details.", "Write one down."])
            )
        }
        post.return_value.raise_for_status.return_value = None
        result = generate_adventure(preferences())
        self.assertEqual(result.source, "fallback")
        self.assertIn("safety guidelines", result.notice or "")

    def test_fallback_variants_are_distinct(self) -> None:
        first = create_fallback_mission(preferences(), 0)
        second = create_fallback_mission(preferences(), 1)
        self.assertNotEqual(first.title, second.title)


class LocalStorageTests(unittest.TestCase):
    def test_saves_completed_missions_and_journal_entries(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "data" / "progress.json"
            mission = create_fallback_mission(preferences())
            complete_mission(mission, path)
            complete_mission(mission, path)
            add_journal_entry("I noticed a new detail.", mission.title, path)
            data = load_data(path)
            self.assertEqual(len(data["completed_missions"]), 1)
            self.assertEqual(data["journal_entries"][0]["text"], "I noticed a new detail.")

    def test_corrupt_progress_is_reported_not_silently_replaced(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "progress.json"
            path.write_text("{broken", encoding="utf-8")
            with self.assertRaises(StorageError):
                load_data(path)


if __name__ == "__main__":
    unittest.main()
