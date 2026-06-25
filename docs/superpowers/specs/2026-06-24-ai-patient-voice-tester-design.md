# AI Patient Voice Tester — Design

## Purpose

A Python CLI tool that places outbound voice calls (via Vapi) to a fixed healthcare
AI test line (+1-805-439-8008), where Vapi's own assistant plays a realistic patient
persona defined per-scenario. After each call, the tool retrieves the recording and
transcript, runs an LLM-based evaluation pass, and produces a consolidated bug report.
Built for a take-home AI engineering assessment: minimum 10 calls across 10 distinct
scenarios, each a full natural conversation, with transcripts/recordings/evaluations/
bug report as deliverables.

## Architecture

Vapi owns the entire voice pipeline for both call legs — STT, LLM, TTS, turn-taking,
recording, and transcription — for the simulated-patient side. The project's own code
is pure orchestration: build a per-scenario assistant config (system prompt = patient
persona + goal + constraints), trigger an outbound call via Vapi's REST API, poll for
completion, and persist whatever Vapi returns (recording URL, transcript, call
metadata). A second, independent LLM pass (the "evaluator," using Claude or
GPT-4o-mini) reads each saved transcript against scenario-specific bug checks and
emits structured JSON findings. A final script aggregates all evaluation JSON files
into one `BUG_REPORT.md`.

No persistent server, no webhook receiver, no tunnel — `run_calls.py` is the single
entry point and the whole system is a synchronous batch script: place call → poll
until ended → save artifacts → next scenario. This trades the production-realism of
the webhook approach (used in the author's prior lead-qual project) for an honest
match to what this task is: a one-off batch of test calls, not a service that needs
to keep running.

## Components

- **`scenarios/*.yaml`** — 10 files, one per scenario (appointment_simple, reschedule,
  cancel, refill, insurance, office_hours, location, urgent_symptoms,
  confused_patient, weekend_edge_case). Each follows the field schema the user
  specified: `scenario_id`, `title`, `patient_name`, `patient_dob`, `patient_phone`,
  `patient_context`, `goal`, `tone`, `speaking_style`,
  `information_to_reveal_only_if_asked`, `edge_case`, `success_criteria`,
  `bug_checks`, `expected_safe_behavior`.

- **`app/config.py`** — loads `.env` (API keys, target number, assistant id) via
  `python-dotenv`; central place all other modules import settings from.

- **`app/models.py`** — typed dataclasses/Pydantic models for `Scenario`,
  `CallMetadata`, `Evaluation`, `Bug` — shared shapes used across modules so
  `caller.py`, `evaluator.py`, and `report_generator.py` agree on structure.

- **`app/scenarios.py`** — scenario loader: reads all YAML files in `scenarios/`,
  validates required fields are present, returns a list of `Scenario` objects. Fails
  loudly (raises) on a missing required field rather than silently skipping it.

- **`app/prompts.py`** — turns a `Scenario` into the Vapi assistant's system prompt:
  persona description, goal, tone/speaking-style instructions, the
  "reveal-only-if-asked" info as facts the persona knows but won't volunteer, and the
  standing behavior rules (short replies, no info-dumping, never reveal it's an AI,
  never give medical advice, end politely once goal is met).

- **`app/caller.py`** — places the outbound call: `POST /call` to Vapi with an
  inline `assistantOverrides` (model/voice/transcriber/systemPrompt from
  `prompts.py`) and `customer.number`. **Hard safety check**: rejects any call
  request whose target number isn't exactly `+18054398008`, regardless of what's in
  config — this is the one invariant that must never be bypassable by a bad env var
  or scenario file. Polls `GET /call/{id}` on an interval until `status == "ended"`
  (with a timeout), then returns the call's recording URL + transcript + raw
  metadata.

- **`app/storage.py`** — owns the `runs/call_NNN/` layout: creates the next call
  directory, writes `scenario.yaml` (copy of the scenario used), `transcript.txt`,
  downloads `recording.mp3`, and writes `metadata.json` (call id, timestamps,
  duration, scenario id).

- **`app/evaluator.py`** — given a `Scenario` + transcript, prompts an LLM to
  evaluate against that scenario's `bug_checks` and the general rubric (task
  completion, naturalness, turn-taking, hallucination, safety, medical-advice
  issues, scheduling/insurance/hours correctness, verification questions, confusion
  recovery, call-ending behavior). Returns the JSON shape specified by the user
  (`task_completion`, `naturalness_score`, ..., `bugs[]`). Writes
  `runs/call_NNN/evaluation.json`.

- **`app/report_generator.py`** — reads every `evaluation.json` under `runs/`,
  flattens all `bugs[]` entries, and renders `BUG_REPORT.md` with the fields the
  user specified (title, severity, scenario, call file ref, timestamp, what
  happened, why it matters, expected behavior, recommendation).

- **`run_calls.py`** — top-level script: loads all scenarios, for each one calls
  `caller.place_call` → `storage.save_call` → `evaluator.evaluate`, logging progress
  and call IDs as it goes, then invokes `report_generator` once all calls finish.
  Supports `--scenario <id>` to run just one (for iterating/debugging a single
  persona without re-running the whole batch).

## Data Flow

1. `run_calls.py` loads scenarios from `scenarios/*.yaml` via `app/scenarios.py`.
2. For each scenario: `app/prompts.py` builds the system prompt → `app/caller.py`
   places the call (with the hard-coded number safety check) → polls until ended →
   returns recording URL + transcript.
3. `app/storage.py` creates `runs/call_NNN/`, saves `scenario.yaml`,
   `transcript.txt`, `recording.mp3`, `metadata.json`.
4. `app/evaluator.py` reads the saved transcript + scenario, calls the evaluation
   LLM, saves `evaluation.json` into the same `runs/call_NNN/` directory.
5. After all scenarios complete (or on a separate `python -m app.report_generator`
   invocation), `app/report_generator.py` scans all `runs/*/evaluation.json` and
   writes `BUG_REPORT.md` at the repo root.

## Error Handling

- **Number safety check** in `caller.py` is a hard assert, not a warning — if the
  resolved target number isn't `+18054398008`, the call is never placed and the
  script raises immediately.
- If a single scenario's call fails (busy, no-answer, Vapi error, polling timeout),
  `run_calls.py` logs the failure with the scenario id and continues to the next
  scenario rather than aborting the whole batch.
- If recording download or evaluation fails for a completed call, that call's
  artifacts that did succeed (e.g. transcript) are still kept; the failure is logged
  and that call is flagged as incomplete rather than silently dropped.
- `analyze`/evaluator step is decoupled from the calling step — if evaluation fails
  for a call, transcripts/recordings already on disk aren't lost and evaluation can
  be re-run later against existing `runs/` data.

## Testing / Validation

- No automated test suite is justified for an external-API-driven one-off batch
  script — value comes from the project actually placing real calls. Validation is:
  run `--scenario <id>` against one scenario first, confirm the call sounds natural
  and the transcript/recording/evaluation files come out correctly, before running
  the full batch of 10.
- `app/scenarios.py`'s YAML validation (required-field check) is the one piece worth
  a couple of quick unit tests, since a bad scenario file silently producing a
  broken persona would be hard to notice mid-call.
