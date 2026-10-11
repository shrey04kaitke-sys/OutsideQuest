"""Small local JSON store for completed adventures and reflections."""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4

from outsidequest.models import Mission

DEFAULT_DATA_PATH = Path(
    os.getenv(
        "OUTSIDEQUEST_DATA_PATH",
        str(Path(__file__).resolve().parent.parent / "data" / "user_data.json"),
    )
).expanduser()
EMPTY_DATA: dict[str, list[dict[str, Any]]] = {
    "completed_missions": [],
    "journal_entries": [],
}


class StorageError(RuntimeError):
    """Local progress could not be read or safely written."""


def load_data(path: Path = DEFAULT_DATA_PATH) -> dict[str, list[dict[str, Any]]]:
    try:
        raw = path.read_text(encoding="utf-8")
    except FileNotFoundError:
        return {"completed_missions": [], "journal_entries": []}
    except OSError as exc:
        raise StorageError(f"Could not read local progress at {path}: {exc}") from exc

    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise StorageError(
            f"Local progress at {path} is not valid JSON. Preserve a copy, then repair or remove it."
        ) from exc

    if (
        not isinstance(data, dict)
        or not isinstance(data.get("completed_missions"), list)
        or not isinstance(data.get("journal_entries"), list)
        or any(not isinstance(entry, dict) for entry in data["completed_missions"])
        or any(not isinstance(entry, dict) for entry in data["journal_entries"])
    ):
        raise StorageError(f"Local progress at {path} has an unsupported data format.")
    return data


def save_data(data: dict[str, list[dict[str, Any]]], path: Path = DEFAULT_DATA_PATH) -> None:
    if (
        not isinstance(data.get("completed_missions"), list)
        or not isinstance(data.get("journal_entries"), list)
    ):
        raise StorageError("Progress data has an unsupported format and was not saved.")
    temporary_path = path.with_name(f"{path.name}.tmp")
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary_path.write_text(
            json.dumps(data, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        temporary_path.replace(path)
    except OSError as exc:
        raise StorageError(f"Could not save local progress at {path}: {exc}") from exc


def complete_mission(
    mission: Mission,
    path: Path = DEFAULT_DATA_PATH,
) -> dict[str, list[dict[str, Any]]]:
    data = load_data(path)
    if any(item.get("id") == mission.id for item in data["completed_missions"]):
        return data
    data["completed_missions"].append(
        {
            **mission.to_dict(),
            "completed_at": datetime.now(timezone.utc).isoformat(),
        }
    )
    save_data(data, path)
    return data


def add_journal_entry(
    text: str,
    mission_title: str | None = None,
    path: Path = DEFAULT_DATA_PATH,
) -> dict[str, list[dict[str, Any]]]:
    clean_text = text.strip()
    if not clean_text:
        raise ValueError("A reflection cannot be empty.")
    if len(clean_text) > 2000:
        raise ValueError("A reflection must be 2,000 characters or fewer.")
    data = load_data(path)
    data["journal_entries"].append(
        {
            "id": str(uuid4()),
            "text": clean_text,
            "mission_title": mission_title,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
    )
    save_data(data, path)
    return data
