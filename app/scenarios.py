from __future__ import annotations

from pathlib import Path

import yaml
from pydantic import ValidationError

from app.models import Scenario


class ScenarioLoadError(Exception):
    pass


def load_scenarios(directory: Path) -> list[Scenario]:
    scenarios: list[Scenario] = []
    for path in sorted(Path(directory).glob("*.yaml")):
        raw = yaml.safe_load(path.read_text())
        try:
            scenarios.append(Scenario(**raw))
        except ValidationError as exc:
            raise ScenarioLoadError(f"{path.name}: {exc}") from exc
    return scenarios
