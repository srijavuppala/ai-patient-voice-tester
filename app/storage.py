from __future__ import annotations

import json
import subprocess
import tempfile
from pathlib import Path

import requests
import yaml

from app.models import Scenario

DIRECT_SAVE_EXTENSIONS = {"mp3", "ogg"}


def next_call_dir(base: Path = Path("runs")) -> Path:
    base = Path(base)
    base.mkdir(parents=True, exist_ok=True)
    existing = [p for p in base.iterdir() if p.is_dir() and p.name.startswith("call_")]
    numbers = [int(p.name.split("_")[1]) for p in existing if p.name.split("_")[1].isdigit()]
    next_number = max(numbers, default=0) + 1
    return base / f"call_{next_number:03d}"


def _source_extension(recording_url: str) -> str:
    suffix = Path(recording_url).suffix.lower().lstrip(".")
    return suffix or "wav"


def _convert_to_mp3(source_path: Path, dest_path: Path) -> None:
    subprocess.run(
        ["ffmpeg", "-y", "-i", str(source_path), str(dest_path)],
        check=True,
        capture_output=True,
    )


def _save_recording(call_dir: Path, recording_url: str) -> None:
    response = requests.get(recording_url, timeout=60)
    response.raise_for_status()

    source_extension = _source_extension(recording_url)
    if source_extension in DIRECT_SAVE_EXTENSIONS:
        (call_dir / f"recording.{source_extension}").write_bytes(response.content)
        return

    with tempfile.NamedTemporaryFile(suffix=f".{source_extension}") as tmp:
        tmp.write(response.content)
        tmp.flush()
        _convert_to_mp3(Path(tmp.name), call_dir / "recording.mp3")


def save_call(call_dir: Path, scenario: Scenario, call_result: dict) -> None:
    call_dir = Path(call_dir)
    call_dir.mkdir(parents=True, exist_ok=True)

    (call_dir / "scenario.yaml").write_text(yaml.safe_dump(scenario.model_dump()))
    (call_dir / "transcript.txt").write_text(call_result.get("transcript", ""))

    metadata = {
        "call_id": call_result.get("call_id"),
        "scenario_id": scenario.scenario_id,
        "status": call_result.get("status"),
        "started_at": call_result.get("started_at"),
        "ended_at": call_result.get("ended_at"),
        "recording_url": call_result.get("recording_url"),
    }
    (call_dir / "metadata.json").write_text(json.dumps(metadata, indent=2))

    recording_url = call_result.get("recording_url")
    if recording_url:
        _save_recording(call_dir, recording_url)
