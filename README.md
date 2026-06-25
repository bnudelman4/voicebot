# voicebot

An automated outbound voice bot that places a real phone call to a test line and
role-plays a patient to stress-test a clinic's AI receptionist. It dials out via
Twilio, bridges the call audio to the OpenAI Realtime API (speech-to-speech) so
it can hold a natural spoken conversation as the patient, records each call, and
saves a timestamped transcript. surfacing where the receptionist under test
misbehaves. The clinic under test is **Pivot Point Orthopedics** (Pretty Good
AI's demo receptionist) and the patient persona is **Benjamin Nudelman**
(DOB March 31, 2006), who has only a name and DOB on file. Thirteen scenarios
cover routine front-desk tasks plus adversarial edge cases (closed-day booking,
nonexistent records, controlled-substance refills, identity corrections,
barge-in, and more); findings are logged in `bug-report.md`.

Walkthrough / Debug video link: https://www.loom.com/share/87e6d992e020460eb86f327feb83172a

## Setup

1. **Python 3.11+ and a virtualenv:**
   ```bash
   python -m venv .venv
   source .venv/bin/activate
   ```
2. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```
3. **Configure:** copy the example env file and fill in real values.
   ```bash
   cp .env.example .env
   # then edit .env
   ```
4. **Accounts:** a Twilio account that is **out of trial** with a **voice-capable
   phone number** (set as `TWILIO_FROM_NUMBER`), and an **OpenAI API key with
   Realtime access**.
5. **ngrok:** run it on your reserved domain so `PUBLIC_HOST` stays stable
   between runs. With `PUBLIC_HOST` and `PORT` set in `.env`:
   ```bash
   ngrok http --domain=$PUBLIC_HOST 8080
   ```
   (`PUBLIC_HOST` is the hostname only, no `https://` prefix.)
6. **No Twilio webhook config needed.** The outbound call passes the TwiML URL
   programmatically (`https://PUBLIC_HOST/twiml`), so you do **not** have to
   configure the phone number's voice webhook in the Twilio console.

## Run

The server and ngrok must both be running first, in their own terminals:

```bash
# Terminal 1 — FastAPI server (audio bridge)
uvicorn server:app --host 0.0.0.0 --port 8080

# Terminal 2 — ngrok on the reserved domain
ngrok http --domain=$PUBLIC_HOST 8080
```

Then place a call (Terminal 3). The primary path:

```bash
# Run a scenario call (dials TARGET_NUMBER as the patient persona)
python main.py --scenario new_appointment
```

Other commands (`main.py`):

```bash
# List all scenarios (id + title)
python main.py --list

# Plain test call (no persona): rings TARGET_NUMBER and records it
python main.py --test-call

# Test call to a specific number
python main.py --test-call +15551234567
```

A scenario call places the call, polls until it completes, then downloads the
recording — printing both the transcript and recording paths when done.

## Scenarios

Thirteen scenarios (ids and titles from `scenarios.py`):

| id                            | description                                        |
| ----------------------------- | -------------------------------------------------- |
| `new_appointment`             | Book a new appointment for knee pain               |
| `reschedule`                  | Reschedule an appointment to a different day       |
| `cancel`                      | Cancel an upcoming appointment                     |
| `refill`                      | Refill an ortho medication (meloxicam)             |
| `hours_location_insurance`    | Ask hours, location, and whether they take Aetna   |
| `closed_day_booking`          | Insist on a Saturday (closed-day) slot             |
| `ambiguous_date`              | Book using vague date language ("next Friday")     |
| `nonexistent_record`          | Reschedule an appointment that doesn't exist       |
| `controlled_substance_refill` | Request an oxycodone refill                        |
| `topic_switch`                | Start booking, then pivot to another task mid-call |
| `wrong_then_corrected_dob`    | Give a wrong DOB, then correct it                  |
| `out_of_scope`                | Ask something a scheduling line shouldn't answer   |
| `interruption_barge_in`       | Intentionally talk over the agent to test barge-in |

## Output

Each call produces a paired set of files sharing the same two-digit number `NN`:

- `transcripts/transcript-NN.txt` — header (scenario, call SID, date/time,
  patient identity) followed by one `[MM:SS] SPEAKER: text` line per turn.
- `recordings/recording-NN.mp3` — the Twilio call recording.

The same `NN` ties a transcript to its recording. Findings and observed
misbehavior are written up in **`bug-report.md`**.

## Environment variables

Every variable in `.env.example` (no real values shown):

| Variable                | Description                                                  |
| ----------------------- | ------------------------------------------------------------ |
| `OPENAI_API_KEY`        | OpenAI API key with Realtime access                          |
| `OPENAI_REALTIME_MODEL` | Realtime model name (default `gpt-realtime`)                 |
| `OPENAI_VOICE`          | Voice the model speaks with (e.g. `marin`, `cedar`, `alloy`) |
| `TWILIO_ACCOUNT_SID`    | Twilio Account SID (starts with `AC`)                        |
| `TWILIO_AUTH_TOKEN`     | Twilio Auth Token                                            |
| `TWILIO_FROM_NUMBER`    | Voice-capable Twilio number to call from (E.164)             |
| `TARGET_NUMBER`         | Number the bot calls — the clinic test line (E.164)          |
| `PUBLIC_HOST`           | ngrok hostname only, no `https://` (e.g. `my-bot.ngrok.app`) |
| `PORT`                  | Local port uvicorn binds to (default `8080`)                 |
