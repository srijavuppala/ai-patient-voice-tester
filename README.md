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
2. Get a Vapi **Private Key** from your Vapi dashboard (API Keys page — not the
   Public Key; the private key is required for server-side call placement).
3. Get an OpenAI API key from platform.openai.com (used for the evaluator pass).
4. Copy `.env.example` to `.env` and fill in:

   ```
   VAPI_API_KEY=your-vapi-private-key
   VAPI_PHONE_NUMBER_ID=your-vapi-phone-number-id
   OPENAI_API_KEY=your-openai-key
   ```

   The call target (`+18054398008`) is hard-coded in `app/caller.py` and is not
   configurable via environment variables, by design.

5. Create a virtual environment and install dependencies:

   ```bash
   python3 -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   ```

## Running

Run all 12 scenarios (places 12 real phone calls, ~1-3 min each):

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

Tests cover scenario loading/validation (12 scenarios including edge cases), prompt building, storage, the Vapi caller's
safety check and polling logic (all HTTP calls mocked), and the evaluator/report
generator. They do not place real calls or call OpenAI/Vapi.

## Dashboard

Generate an interactive HTML dashboard to browse all calls, transcripts, recordings, and bugs:

```bash
python generate_dashboard.py
```

Then open `dashboard/index.html` in your browser. It shows:
- **Overview stats** — total calls, pass/fail/partial counts, bugs found
- **Scenario table** — all 12 scenarios with results, scores, and links
- **Call cards** — audio player, color-coded transcript (AI vs agent), inline bug badges, and severity-colored bug lists
