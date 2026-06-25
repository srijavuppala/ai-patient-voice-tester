from __future__ import annotations

import time

import requests

from app.config import Settings
from app.models import Scenario
from app.prompts import build_first_message, build_system_prompt

VAPI_BASE_URL = "https://api.vapi.ai"
ALLOWED_TARGET_NUMBER = "+18054398008"


class CallError(Exception):
    pass


def _headers(settings: Settings) -> dict:
    return {"Authorization": f"Bearer {settings.vapi_api_key}", "Content-Type": "application/json"}


def place_call(scenario: Scenario, settings: Settings, target_number: str) -> str:
    if target_number != ALLOWED_TARGET_NUMBER:
        raise CallError(
            f"Refusing to place call: this tool may only call {ALLOWED_TARGET_NUMBER}, got {target_number!r}"
        )

    payload = {
        "phoneNumberId": settings.vapi_phone_number_id,
        "customer": {"number": target_number},
        "assistant": {
            "firstMessage": build_first_message(scenario),
            "model": {
                "provider": "openai",
                "model": "gpt-4o-mini",
                "messages": [{"role": "system", "content": build_system_prompt(scenario)}],
            },
            "voice": {"provider": "vapi", "voiceId": "Elliot"},
            "transcriber": {"provider": "deepgram", "model": "nova-2"},
        },
    }
    response = requests.post(f"{VAPI_BASE_URL}/call", json=payload, headers=_headers(settings), timeout=30)
    response.raise_for_status()
    return response.json()["id"]


def _extract_transcript(call_data: dict) -> str:
    return call_data.get("transcript") or call_data.get("artifact", {}).get("transcript", "")


def _extract_recording_url(call_data: dict) -> str | None:
    return call_data.get("recordingUrl") or call_data.get("artifact", {}).get("recordingUrl")


def poll_call(call_id: str, settings: Settings, interval: float = 5.0, timeout: float = 300.0) -> dict:
    deadline = time.monotonic() + timeout
    while True:
        response = requests.get(f"{VAPI_BASE_URL}/call/{call_id}", headers=_headers(settings), timeout=30)
        response.raise_for_status()
        call_data = response.json()

        if call_data.get("status") == "ended":
            return {
                "call_id": call_id,
                "status": "ended",
                "started_at": call_data.get("startedAt"),
                "ended_at": call_data.get("endedAt"),
                "transcript": _extract_transcript(call_data),
                "recording_url": _extract_recording_url(call_data),
            }

        if time.monotonic() >= deadline:
            raise CallError(
                f"Polling call {call_id} timed out after {timeout}s, last status: {call_data.get('status')}"
            )

        time.sleep(interval)


def run_scenario_call(scenario: Scenario, settings: Settings) -> dict:
    call_id = place_call(scenario, settings, target_number=ALLOWED_TARGET_NUMBER)
    return poll_call(call_id, settings)
