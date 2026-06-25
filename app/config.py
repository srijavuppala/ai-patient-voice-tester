from __future__ import annotations

import os
from dataclasses import dataclass

from dotenv import load_dotenv

load_dotenv()


@dataclass(frozen=True)
class Settings:
    vapi_api_key: str
    vapi_phone_number_id: str
    anthropic_api_key: str


def get_settings() -> Settings:
    return Settings(
        vapi_api_key=os.environ.get("VAPI_API_KEY", ""),
        vapi_phone_number_id=os.environ.get("VAPI_PHONE_NUMBER_ID", ""),
        anthropic_api_key=os.environ.get("ANTHROPIC_API_KEY", ""),
    )
