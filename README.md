# voicebot

Automated outbound voice bot. Places phone calls via Twilio to a test line,
bridges audio between Twilio Media Streams and the OpenAI Realtime API so it can
hold a natural spoken conversation as a "patient," records each call, and saves
transcripts.

> **Status:** scaffolding only. Modules are documented stubs; the audio bridge
> and call logic are not implemented yet.

## Overview

The bot dials a number (`TARGET_NUMBER`), and once connected streams audio in
both directions: the called party's audio goes to the OpenAI Realtime API, and
the model's synthesized speech goes back to the call. A scenario's `persona`
system prompt makes the model act as the patient **Benjamin Nudelman (DOB March
31, 2006)** with a specific goal (book an appointment, refill a prescription,
ask about office hours). Each call is recorded and transcribed.

## Architecture

_Placeholder — to be filled in as the bridge is implemented._

```
main.py ──places call──▶ Twilio ──dials──▶ TARGET_NUMBER
                           │
                           ▼ (TwiML: <Connect><Stream>)
                    server.py  /twiml  +  /media-stream (websocket)
                           │
                           ▼ raw websocket
                  OpenAI Realtime API (gpt-realtime)
```

- `settings.py` — load + validate env config.
- `scenarios.py` — patient personas (system prompts).
- `caller.py` — place the recorded outbound call (Twilio REST).
- `server.py` — TwiML endpoint + Twilio↔OpenAI audio bridge (FastAPI).
- `transcripts.py` — write transcript files; download recordings as mp3.
- `main.py` — CLI to pick a scenario and trigger a call.

## Setup

```bash
# 1. Create and activate a virtual environment (Python 3.11+)
python3 -m venv .venv
source .venv/bin/activate

# 2. Install dependencies
pip install -r requirements.txt

# 3. Configure
cp .env.example .env
# then edit .env and fill in your real values

# 4. Start ngrok on your configured domain (must match PUBLIC_HOST in .env)
ngrok http --domain=your-domain.ngrok.app 8080
```

## Run

Two pieces: the server (so Twilio can reach `PUBLIC_HOST`) and the CLI.

```bash
# Terminal 1 — start the server
uvicorn server:app --host 0.0.0.0 --port 8080

# Terminal 2 — list scenarios, then place a call
python main.py --list
python main.py --scenario new_appointment
```

## Scenarios

Defined in `scenarios.py`. Current set:

| id | title |
|----|-------|
| `new_appointment` | New appointment booking |
| `prescription_refill` | Prescription refill |
| `office_hours` | Office-hours question |

More will be added later. All use the patient identity Benjamin Nudelman, DOB
March 31, 2006.

## Output locations

- **Recordings:** `recordings/` — Twilio call recordings downloaded as mp3.
- **Transcripts:** `transcripts/` — per-call, timestamped, both-sides text.
- **Bug report:** _TBD_ — where call issues / failures will be logged.
