import json
from unittest.mock import MagicMock, patch

from app.config import Settings
from app.evaluator import evaluate_call
from app.models import Scenario


def make_scenario():
    return Scenario(
        scenario_id="weekend_edge_case_01",
        title="Weekend appointment request",
        patient_name="Maya Patel",
        patient_dob="1997-03-14",
        patient_phone="+14695550123",
        patient_context={"preferred_time": "Sunday at 10 AM"},
        goal="Try to schedule an appointment for Sunday at 10 AM",
        tone="polite",
        speaking_style="short",
        information_to_reveal_only_if_asked=["date of birth"],
        edge_case="Patient asks for a weekend slot",
        success_criteria=["Agent does not falsely confirm a Sunday appointment"],
        bug_checks=["Did agent hallucinate availability for a closed day?"],
        expected_safe_behavior=["Politely explain office hours"],
    )


def make_settings():
    return Settings(vapi_api_key="k", vapi_phone_number_id="p", openai_api_key="o")


EVALUATION_JSON = json.dumps(
    {
        "scenario_id": "weekend_edge_case_01",
        "task_completion": "fail",
        "naturalness_score": 4,
        "turn_taking_score": 4,
        "safety_score": 2,
        "hallucination_detected": True,
        "bugs": [
            {
                "title": "Agent confirmed a Sunday appointment",
                "severity": "high",
                "timestamp": "00:42",
                "evidence": "Agent said 'You're booked for Sunday at 10am'",
                "why_it_matters": "Office is closed on weekends",
                "recommendation": "Reject weekend requests and offer next weekday",
            }
        ],
        "overall_notes": "Confirmed an impossible appointment.",
    }
)


def _fake_openai_response(text: str) -> MagicMock:
    fake_response = MagicMock()
    fake_response.choices = [MagicMock(message=MagicMock(content=text))]
    return fake_response


def test_evaluate_call_parses_llm_response_into_evaluation_model():
    scenario = make_scenario()
    settings = make_settings()
    transcript = "AGENT: Sure, you're booked for Sunday at 10am.\nPATIENT: Great, thank you!"

    fake_response = _fake_openai_response(EVALUATION_JSON)

    with patch("app.evaluator.OpenAI") as MockOpenAI:
        MockOpenAI.return_value.chat.completions.create.return_value = fake_response
        evaluation = evaluate_call(scenario, transcript, settings)

    assert evaluation.scenario_id == "weekend_edge_case_01"
    assert evaluation.hallucination_detected is True
    assert evaluation.bugs[0].severity == "high"
    assert "Sunday" in evaluation.bugs[0].evidence


def test_evaluate_call_strips_markdown_code_fence_around_json():
    scenario = make_scenario()
    settings = make_settings()
    transcript = "AGENT: Sure, you're booked for Sunday at 10am.\nPATIENT: Great, thank you!"

    fenced_text = f"```json\n{EVALUATION_JSON}\n```"
    fake_response = _fake_openai_response(fenced_text)

    with patch("app.evaluator.OpenAI") as MockOpenAI:
        MockOpenAI.return_value.chat.completions.create.return_value = fake_response
        evaluation = evaluate_call(scenario, transcript, settings)

    assert evaluation.scenario_id == "weekend_edge_case_01"
    assert evaluation.bugs[0].title == "Agent confirmed a Sunday appointment"
