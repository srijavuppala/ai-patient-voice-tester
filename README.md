# AI Patient Voice Tester

A Python tool that places outbound voice calls (via [Vapi](https://vapi.ai)) to a
healthcare AI test line, where Vapi's own assistant plays a realistic patient persona
defined in YAML. After each call it saves the recording + transcript, runs an LLM
evaluation pass, and produces a consolidated bug report.

**Safety note:** this tool will only ever call `+1-805-439-8008` (the assigned
assessment test line). The target number is hard-coded as a constant
(`ALLOWED_TARGET_NUMBER`) in `app/caller.py` and checked before every call,
independent of any configuration value.

## Setup

1. Create a [Vapi](https://vapi.ai) account and buy/import one outbound phone number.
   Note its **Phone Number ID**.
2. Get a Vapi API key from your Vapi dashboard.
3. Get an Anthropic API key from console.anthropic.com (used for the evaluator pass).
4. Copy `.env.example` to `.env` and fill in:

   ```
   VAPI_API_KEY=your-vapi-key
   VAPI_PHONE_NUMBER_ID=your-vapi-phone-number-id
   ANTHROPIC_API_KEY=your-anthropic-key
   TARGET_PHONE_NUMBER=+18054398008
   ```

5. Create a virtual environment and install dependencies:

   ```bash
   python3 -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   ```

## Running

Run all 10 scenarios (places 10 real phone calls, ~1-3 min each):

```bash
python run_calls.py
```

Run a single scenario (useful for testing one persona without the full batch):

```bash
python run_calls.py --scenario appointment_simple_01
```

Each call's `scenario_id` is set in the corresponding file under `scenarios/`.

## Where artifacts are stored

Each call gets its own folder under `runs/`:

```
runs/call_001/
  scenario.yaml       # the scenario config used for this call
  transcript.txt      # full call transcript
  recording.mp3        # call audio
  metadata.json         # call id, timestamps, status
  evaluation.json       # LLM evaluation of this call's transcript
```

## Bug report

After all scenarios finish, `run_calls.py` automatically regenerates `BUG_REPORT.md`
at the repo root from every `runs/*/evaluation.json` file. You can also regenerate it
standalone without placing new calls:

```bash
python -c "from app.report_generator import generate_report; generate_report()"
```

## Running tests

```bash
source venv/bin/activate
pytest
```

Tests cover scenario loading/validation, prompt building, storage, the Vapi caller's
safety check and polling logic (all HTTP calls mocked), and the evaluator/report
generator. They do not place real calls.
