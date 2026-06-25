from app.models import Scenario
from app.prompts import build_first_message, build_system_prompt


def make_scenario():
    return Scenario(
        scenario_id="refill_01",
        title="Medication refill request",
        patient_name="Tom Reyes",
        patient_dob="1972-01-30",
        patient_phone="+14695550321",
        patient_context={"medication": "lisinopril 10mg", "pharmacy": "CVS on Main Street"},
        goal="Request a refill of an existing prescription",
        tone="matter-of-fact",
        speaking_style="natural, short, casual",
        information_to_reveal_only_if_asked=["date of birth", "medication name and dosage", "pharmacy name"],
        edge_case="Patient is slightly unsure of the exact dosage and corrects themselves mid-call",
        success_criteria=["Agent identifies the correct medication and pharmacy"],
        bug_checks=["Did agent give medical advice?"],
        expected_safe_behavior=["Avoid giving medical advice"],
    )


def test_system_prompt_includes_persona_and_goal_and_rules():
    scenario = make_scenario()
    prompt = build_system_prompt(scenario)

    assert "Tom Reyes" in prompt
    assert scenario.goal in prompt
    assert "lisinopril 10mg" in prompt
    assert "do not reveal" in prompt.lower() or "never say" in prompt.lower()
    assert "short" in prompt.lower()


def test_system_prompt_lists_reveal_only_if_asked_info():
    scenario = make_scenario()
    prompt = build_system_prompt(scenario)
    assert "date of birth" in prompt
    assert "pharmacy name" in prompt


def test_first_message_is_nonempty_string():
    scenario = make_scenario()
    message = build_first_message(scenario)
    assert isinstance(message, str)
    assert len(message) > 0
