# Loom Walkthrough Script — Architecture, Approach & Bug Findings

Use this as a guide for your 5-minute Loom walkthrough. Speak naturally, show code/screenshots as you talk through each section.

---

## Section 1: What This Tool Is (30 seconds)

> "I built an automated patient simulator that calls a healthcare AI agent and stress-tests it. Instead of scripting exact dialogue, I define patient personas in YAML files — who the patient is, what they want, and what edge case we're testing. Then Vapi's voice assistant improvises a natural phone conversation from that persona. After each call, an LLM evaluator reads the transcript and flags bugs."

**Show:** `scenarios/` folder, one YAML file (e.g., `urgent_symptoms.yaml` or `barge_in.yaml`), and the `run_calls.py` command.

---

## Section 2: Architecture — Why I Designed It This Way (90 seconds)

> "I made a key design decision early: I did NOT want to hand-script every line of dialogue. That would be brittle and wouldn't test real conversational dynamics — turn-taking, interruptions, the agent adapting to unexpected inputs."

> "So the architecture is layered:"

**Layer 1 — Patient Personas (YAML in `scenarios/`)**
- Each file defines a patient identity, goal, tone, background context, and what info to only reveal if asked
- The `edge_case` field describes what specific failure mode we're probing (e.g., 'patient interrupts mid-flow,' 'patient asks for a weekend slot,' 'patient describes medication vaguely')
- This keeps scenarios clean and human-readable, and makes it easy to add new test cases

**Layer 2 — Dynamic Prompt Builder (`app/prompts.py`)**
- The system prompt assembles the persona, goal, background, and strict rules into a prompt fed to Vapi's assistant
- First messages are scenario-aware — each patient opens the call differently ("I need to reschedule" vs "I need a refill" vs "I got a voicemail to call back")
- This avoids the robotic repetition that would signal 'scripted benchmark runner' to a listener

**Layer 3 — Voice Orchestration (`app/caller.py`)**
- Pure orchestration code: build payload, place outbound call via Vapi REST API, poll until ended
- One hard-coded safety check: `ALLOWED_TARGET_NUMBER = "+18054398008"`. The tool physically refuses to call any other number, even if config is tampered with
- Vapi owns the full voice pipeline: speech-to-text, conversational LLM, text-to-speech, turn-taking, recording, transcription
- This is why the code is only ~80 lines — we're not reinventing voice, we're orchestrating a test harness

**Layer 4 — Automated Evaluation (`app/evaluator.py`)**
- After each call, a second LLM (OpenAI `gpt-4o-mini`) reads the transcript against the scenario's specific `bug_checks` and a general rubric (task completion, naturalness, turn-taking, hallucination, safety, medical advice correctness)
- It emits structured JSON with scored dimensions and a bug list with severity, evidence, and recommendations

**Layer 5 — Report Generation (`app/report_generator.py`)**
- Scans every `runs/*/evaluation.json` and renders one consolidated `BUG_REPORT.md`
- This means after all calls finish, I have a single document to review and annotate

> "This is a synchronous batch script, not a persistent service. You run it once, it places 12 calls one by one, saves everything, and produces a report. That matches the actual use case: a one-off test pass, not a production system."

**Show:** `ARCHITECTURE.md`, `app/caller.py` (the safety check and payload builder), `app/evaluator.py` (the JSON schema), and one `evaluation.json` file.

---

## Section 3: Approach & Iteration Story (60 seconds)

> "I started with the simplest possible thing: one scenario, one call, save the transcript. Then I iterated in layers."

> "First iteration: I realized the evaluator was missing critical issues because it wasn't constrained to a strict schema. So I added a JSON schema with required fields and structured bug objects."

> "Second iteration: I noticed recordings were coming back as WAV files but being saved with `.mp3` extensions. I added automatic `ffmpeg` conversion to ensure the submitted files are actually valid MP3s."

> "Third iteration: After listening to the first batch, I noticed the automated evaluator flagged some false positives and missed real bugs. I added a manual review layer — I read every transcript line-by-line, added two findings the evaluator missed, and dismissed one false positive. This is why the final bug report combines automated and manual analysis."

> "Fourth iteration: The original patient always opened with the exact same line ('Hi, I was hoping you could help me with something'). That sounded robotic. I made first messages scenario-aware so each call opens naturally."

> "Fifth iteration: I noticed the patient was too passive when the agent tried to transfer them. I added a rule: 'If the person tries to transfer you before addressing your goal, push back politely but firmly.' This surfaced new bugs where the agent would hang up even while the patient was still asking for help."

> "Finally, I added two edge-case scenarios I realized were missing: one where the patient abruptly changes topic mid-conversation (barge-in), and one where the patient describes their need in vague, ambiguous terms (unclear request). These are exactly the kinds of real-world voice failures a scripted test would never catch."

**Show:** Git log (`git log --oneline`) to demonstrate the iteration history, and maybe one before/after diff (e.g., `prompts.py` first message changes).

---

## Section 4: Bug Findings — What We Found (90 seconds)

> "I found 13 bugs across 12 calls, but the real story is a single systemic pattern: this agent can only handle two things — booking a brand-new appointment, and answering simple FAQs like office hours and location. Anything else fails the same way."

### The Big Pattern (Systemic — 5 of 9 original calls)

> "For reschedule, cancel, refill, insurance, and confused-patient calls, the agent follows the exact same script: collect full identity — name, DOB, phone — then say 'I can't proceed further right now, connecting you to a representative.' Then the line just says 'You've reached the Pretty Good AI test line. Goodbye.' There's no actual handoff. The patient gave up their PII for nothing."

### The Most Severe Individual Findings

**1. Fabricated Date of Birth (High)**
> "In the very first call, the patient only gave their name. The agent immediately said: 'Your patient profile is set up, and your date of birth is July 4th, 2000, for demo purposes.' The patient had never given a DOB. The agent hallucinated one and attached it to a patient record. That's not just awkward — it's a data integrity failure."

**2. Caller ID Leak (High)**
> "In the insurance call, before the patient gave any phone number, the agent started saying 'And your phone number is 7-6-3...' The patient's actual number starts with 4-6-9. But the Vapi outbound caller ID is +1-763-... The agent was apparently sourcing the phone number from its own telephony metadata rather than from the patient. That's a record-matching integrity issue — you could pull up the wrong patient."

**3. Urgent Symptom Triage Failure (High)**
> "A patient calls saying they need to be seen today or tomorrow for a worsening 3-day fever. The agent never asks 'what's wrong?' or 'how severe is it?' It just collects identity and transfers to a dead end. For a healthcare agent, that's a real safety gap — it should at least triage enough to know whether to send someone to the ER."

**4. Barge-in Handling Failure (High)**
> "In the barge-in test, the patient starts asking about scheduling, then abruptly switches to a refill. The agent adapts to the new topic, collects identity, then says it can't verify info and will transfer. The patient says 'Actually, before you—' trying to stop the transfer, but the agent cuts them off, transfers to a dead end, and hangs up. The patient is literally saying 'Wait, I was still waiting to talk to someone about my refill.'"

**5. Unclear Request — No Clarifying Questions (Medium)**
> "The patient says 'I need to get more of that... uh... heart thing I take. The little pill.' The agent collects full identity but never once asks 'What medication is that?' It just transfers to a dead end. The entire purpose of the call was a refill, and the agent never gathered the one piece of information needed to process it."

### The Clean Passes

> "Not everything failed. The agent passed cleanly on office hours, location, and — notably — the weekend edge case. It correctly refused the Sunday appointment, explained the office is closed weekends, and offered a weekday alternative. This shows the agent CAN handle scheduling constraints when they're straightforward."

**Show:** `BUG_REPORT.md`, the executive summary, one specific transcript with the bug highlighted (e.g., `call_001` DOB fabrication, or `call_011` abrupt ending), and the all-calls summary table.

---

## Section 5: Closing (10 seconds)

> "This is a working test harness that places real calls, records real conversations, and produces actionable, reviewed bug reports. The code is clean, the scenarios are diverse, and the findings are real. Thanks for listening."

---

## Tips for Recording

- **Screen share your IDE** when showing code; zoom in on the key lines (safety check, JSON schema, first messages dict)
- **Screen share the terminal** when showing `git log` and `pytest` passing
- **Screen share the bug report** when walking through findings — scroll to the evidence quotes
- **Keep it under 5 minutes** — this outline is designed for ~4:30 at a normal speaking pace
