from __future__ import annotations

from pydantic import BaseModel


class Scenario(BaseModel):
    scenario_id: str
    title: str
    patient_name: str
    patient_dob: str
    patient_phone: str
    patient_context: dict
    goal: str
    tone: str
    speaking_style: str
    information_to_reveal_only_if_asked: list[str]
    edge_case: str
    success_criteria: list[str]
    bug_checks: list[str]
    expected_safe_behavior: list[str]


class Bug(BaseModel):
    title: str
    severity: str
    timestamp: str
    evidence: str
    why_it_matters: str
    recommendation: str


class Evaluation(BaseModel):
    scenario_id: str
    task_completion: str
    naturalness_score: int
    turn_taking_score: int
    safety_score: int
    hallucination_detected: bool
    bugs: list[Bug]
    overall_notes: str


class CallMetadata(BaseModel):
    call_id: str
    scenario_id: str
    target_number: str
    status: str
    started_at: str | None
    ended_at: str | None
    recording_url: str | None
