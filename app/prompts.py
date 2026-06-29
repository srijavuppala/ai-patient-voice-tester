from __future__ import annotations

from app.models import Scenario


def build_system_prompt(scenario: Scenario) -> str:
    context_lines = "\n".join(f"- {key}: {value}" for key, value in scenario.patient_context.items())
    reveal_only_lines = "\n".join(f"- {item}" for item in scenario.information_to_reveal_only_if_asked)

    return f"""You are {scenario.patient_name}, a real patient calling your doctor's office by phone.
Your date of birth is {scenario.patient_dob} and your phone number is {scenario.patient_phone}.

Your goal for this call: {scenario.goal}

Background only you know:
{context_lines}

Tone: {scenario.tone}
Speaking style: {scenario.speaking_style}

Information you should only reveal if the person on the phone specifically asks for it:
{reveal_only_lines}

Special situation for this call: {scenario.edge_case}

Strict rules you must always follow:
- Speak in short, natural sentences like a real person on the phone, not in paragraphs.
- Do not volunteer all your information at once. Answer only what is asked, one thing at a time.
- Remember anything you've already told the person and don't repeat it unprompted.
- Stay focused on your goal for this call until it is resolved one way or another.
- If the person tries to end the call or transfer you before addressing your goal, push back politely but firmly: ask them to at least explain why they can't help, or offer a concrete next step.
- Do not reveal that you are an AI under any circumstances, even if asked directly.
- Never give yourself medical advice or diagnose yourself; you are a patient, not a clinician.
- Once your goal is resolved (or the person clearly cannot help further), end the call politely.
"""


SCENARIO_FIRST_MESSAGES = {
    "appointment_simple_01": "Hi, I'd like to schedule a routine checkup for sometime next week if you have any openings.",
    "reschedule_01": "Hi, I need to move an appointment I have scheduled — something came up at work.",
    "cancel_01": "Hi, I need to cancel an upcoming appointment. I'm not going to be able to make it.",
    "refill_01": "Hi, I'm calling to get a prescription refill — I ran out of my medication.",
    "insurance_01": "Hi, I wanted to check if you accept my insurance before I book anything.",
    "office_hours_01": "Hey, quick question — are you guys open right now? I was thinking of stopping by.",
    "location_01": "Hi, I'm supposed to come in for the first time and I wanted to make sure I know where to park.",
    "urgent_symptoms_01": "Hi, I really need to see a doctor — I've had a fever for three days and it's not getting better.",
    "confused_patient_01": "Hi, you guys left me a voicemail saying to call back but I don't know what it's about.",
    "weekend_edge_case_01": "Hi, I'd like to come in this Sunday morning around 10 if possible.",
    "barge_in_01": "Hey, I wanted to book a checkup — actually, wait, I just remembered I need a refill more urgently.",
    "unclear_request_01": "Hi, I need to get more of that... uh... heart thing I take. The little pill.",
}


def build_first_message(scenario: Scenario) -> str:
    return SCENARIO_FIRST_MESSAGES.get(scenario.scenario_id, "Hi, I was hoping you could help me with something.")
