# Architecture

This is a scenario-driven AI patient simulator: instead of scripting exact dialogue,
each YAML file in `scenarios/` describes a patient persona, a goal, and what to check
for, and Vapi's own assistant improvises a natural phone conversation from that
persona. Vapi owns the entire voice pipeline for the simulated patient — speech-to-text,
the conversational LLM, text-to-speech, turn-taking, call recording, and transcription —
so this project's code is pure orchestration: build the per-scenario system prompt,
place the outbound call via Vapi's REST API, poll until it ends, and save whatever
Vapi hands back. A hard-coded safety check in `app/caller.py` (`ALLOWED_TARGET_NUMBER`)
ensures the tool can never place a call to any number other than the assigned test
line, regardless of what's in configuration.

After each call, a second and independent LLM pass (`app/evaluator.py`, using
Claude) reads the saved transcript against that scenario's specific `bug_checks` and
the general rubric (task completion, naturalness, turn-taking, hallucination, safety,
medical-advice issues, scheduling/insurance/hours correctness) and emits structured
JSON findings. `app/report_generator.py` then scans every call's `evaluation.json`
under `runs/` and renders one consolidated `BUG_REPORT.md`. There is no persistent
server or webhook receiver — `run_calls.py` is a single synchronous batch script
(place call → poll → save → evaluate → next scenario), which matches what this
project actually is: a one-off batch of test calls, not a production service.
