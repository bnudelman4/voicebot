"""FastAPI server: TwiML endpoint + Twilio <-> OpenAI Realtime audio bridge.

  1. GET/POST /twiml  -> TwiML that opens a bidirectional Media Stream to
     /media-stream, passing the scenario id as a <Parameter>.
  2. WS /media-stream -> bridge audio between the Twilio Media Stream and the
     OpenAI Realtime API. Both directions use G.711 mu-law 8kHz (audio/pcmu),
     matching Twilio exactly so no transcoding is needed.

Run locally with:  uvicorn server:app --host 0.0.0.0 --port $PORT
(ngrok must forward PUBLIC_HOST to that port.)
"""

from __future__ import annotations

import asyncio
import base64  # noqa: F401  (kept for clarity; payloads are passed through as-is)
import json
import logging
import time

import websockets
from fastapi import FastAPI, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import PlainTextResponse, Response
from twilio.twiml.voice_response import Connect, Stream, VoiceResponse

from scenarios import get_scenario
from settings import load_settings
from transcripts import next_sequence_number, write_transcript

logger = logging.getLogger("voicebot.server")

# Quiet HTTP-client header spam so per-turn transcript lines stand out.
for _noisy in ("twilio", "urllib3", "httpx", "httpcore"):
    logging.getLogger(_noisy).setLevel(logging.WARNING)

settings = load_settings()
app = FastAPI(title="voicebot")

OPENAI_REALTIME_URL = "wss://api.openai.com/v1/realtime"
# Fallback persona if a call arrives without a known scenario id.
_DEFAULT_PERSONA = (
    "You are a patient who just called a doctor's office. You placed the call, "
    "so let the receptionist greet you first, then state why you are calling. "
    "Speak naturally and never reveal you are an AI."
)


@app.get("/health", response_class=PlainTextResponse)
def health() -> str:
    """Liveness check — confirm the server is reachable (e.g. through ngrok)."""
    return "ok"


@app.api_route("/twiml", methods=["GET", "POST"])
async def twiml(request: Request) -> Response:
    """Return TwiML that opens a bidirectional Media Stream to /media-stream.

    The scenario id (from caller.place_call's ?scenario= query param) is passed
    to the websocket as a <Parameter>, surfacing in the Twilio 'start' event's
    customParameters.
    """
    scenario_id = request.query_params.get("scenario", "")

    vr = VoiceResponse()
    connect = Connect()
    stream = Stream(url=settings.public_ws_url)  # wss://PUBLIC_HOST/media-stream
    if scenario_id:
        stream.parameter(name="scenario", value=scenario_id)
    connect.append(stream)
    vr.append(connect)
    return Response(content=str(vr), media_type="application/xml")


def _session_update(persona: str) -> dict:
    """Build the OpenAI Realtime session.update (GA shape, mu-law in/out)."""
    return {
        "type": "session.update",
        "session": {
            "type": "realtime",
            "model": settings.openai_realtime_model,
            "output_modalities": ["audio"],
            "instructions": persona,
            "audio": {
                "input": {
                    "format": {"type": "audio/pcmu"},
                    "turn_detection": {
                        "type": "server_vad",
                        # Wait through short comma-length pauses before ending the
                        # turn (default 500ms; raised to ride out natural pauses).
                        "silence_duration_ms": 600,
                        # Audio kept before detected speech start (default 300ms).
                        "prefix_padding_ms": 300,
                        # VAD sensitivity 0-1; higher = needs louder speech (default 0.5).
                        "threshold": 0.5,
                    },
                    # whisper-1 is unreliable with G.711 mu-law; gpt-4o-mini-transcribe
                    # transcribes the agent's audio reliably for the input turn.
                    "transcription": {"model": "gpt-4o-mini-transcribe"},
                },
                "output": {
                    "format": {"type": "audio/pcmu"},
                    "voice": settings.openai_voice,
                },
            },
        },
    }


def _log_turn(state: dict, speaker: str, text: str) -> None:
    """Record + print one conversation turn with an elapsed timestamp."""
    text = (text or "").strip()
    if not text:
        return
    elapsed = time.monotonic() - state["start_time"]
    ts = f"{int(elapsed) // 60:02d}:{int(elapsed) % 60:02d}"
    state["turns"].append({"speaker": speaker, "text": text, "ts": ts})
    logger.info("captured turn #%d speaker=%s ts=%s", len(state["turns"]), speaker, ts)
    print(f"[{ts}] {speaker.upper()}: {text}", flush=True)


@app.websocket("/media-stream")
async def media_stream(ws: WebSocket) -> None:
    """Bridge Twilio Media Stream audio to/from the OpenAI Realtime API."""
    await ws.accept()
    state = {
        "stream_sid": None,
        "start_time": time.monotonic(),
        "bot_speaking": False,
        "response_active": False,  # True between response.created and response.done
        "call_sid": None,
        "scenario_id": None,
        "turns": [],
        "in_frames": 0,       # (a) inbound audio frames forwarded to OpenAI
        "out_deltas": 0,      # (b) output-audio events OpenAI emitted
        "out_forwarded": 0,   # (c) output frames sent back to Twilio
    }

    # Wait for Twilio 'start' to learn the streamSid + scenario before
    # configuring the OpenAI session.
    persona = _DEFAULT_PERSONA
    try:
        while state["stream_sid"] is None:
            data = json.loads(await ws.receive_text())
            if data.get("event") == "start":
                start = data["start"]
                state["stream_sid"] = start["streamSid"]
                state["call_sid"] = start.get("callSid")
                state["start_time"] = time.monotonic()
                scenario_id = (start.get("customParameters") or {}).get("scenario")
                state["scenario_id"] = scenario_id
                if scenario_id:
                    try:
                        persona = get_scenario(scenario_id).persona
                    except KeyError:
                        logger.warning("unknown scenario %r; using default persona", scenario_id)
                logger.info("stream start sid=%s scenario=%s", state["stream_sid"], scenario_id)
    except WebSocketDisconnect:
        return

    # Connect to OpenAI Realtime (no OpenAI-Beta header in GA).
    url = f"{OPENAI_REALTIME_URL}?model={settings.openai_realtime_model}"
    headers = {"Authorization": f"Bearer {settings.openai_api_key}"}
    try:
        async with websockets.connect(url, additional_headers=headers) as openai_ws:
            await openai_ws.send(json.dumps(_session_update(persona)))
            logger.info("connected to OpenAI Realtime, sent session.update (model=%s)", settings.openai_realtime_model)
            # Note: no initial response.create — the clinic agent greets first,
            # so the bot listens and server VAD triggers its reply.
            await asyncio.gather(
                _twilio_to_openai(ws, openai_ws, state),
                _openai_to_twilio(ws, openai_ws, state),
            )
    except Exception as exc:  # noqa: BLE001 - log + end the call cleanly
        logger.error("bridge error: %s", exc)
    finally:
        # Persist the transcript here (server owns the turns). It picks the NN
        # and embeds the Call SID; main.py recovers that NN to name the mp3.
        try:
            seq = next_sequence_number()
            path = write_transcript(state["turns"], seq, state["scenario_id"], state["call_sid"])
            print(f"Transcript saved: {path}", flush=True)
        except Exception as exc:  # noqa: BLE001 - never let writing crash teardown
            logger.error("failed to write transcript: %s", exc)
        # Diagnostic summary: (a) in_frames, (b) out_deltas, (c) out_forwarded.
        logger.info(
            "call ended sid=%s turns=%d in_frames=%d out_deltas=%d out_forwarded=%d",
            state["stream_sid"], len(state["turns"]),
            state["in_frames"], state["out_deltas"], state["out_forwarded"],
        )


async def _twilio_to_openai(ws: WebSocket, openai_ws, state: dict) -> None:
    """Twilio -> OpenAI: forward inbound mu-law audio into the input buffer."""
    try:
        while True:
            data = json.loads(await ws.receive_text())
            event = data.get("event")
            if event == "media":
                # payload is already base64 mu-law; append verbatim.
                await openai_ws.send(json.dumps({
                    "type": "input_audio_buffer.append",
                    "audio": data["media"]["payload"],
                }))
                state["in_frames"] += 1
                if state["in_frames"] == 1:
                    logger.info("(a) first inbound media frame -> OpenAI sid=%s", state["stream_sid"])
                elif state["in_frames"] % 250 == 0:  # ~5s at 20ms frames
                    logger.info("(a) inbound frames -> OpenAI: %d", state["in_frames"])
            elif event == "stop":
                logger.info("twilio stop sid=%s", state["stream_sid"])
                break
    except WebSocketDisconnect:
        logger.info("twilio disconnected sid=%s", state["stream_sid"])
    finally:
        await openai_ws.close()


async def _openai_to_twilio(ws: WebSocket, openai_ws, state: dict) -> None:
    """OpenAI -> Twilio: stream output audio back; handle transcripts + barge-in."""
    # Accept GA name and legacy name so audio forwards regardless of variant.
    audio_delta_types = {"response.output_audio.delta", "response.audio.delta"}
    transcript_done_types = {"response.output_audio_transcript.done", "response.audio_transcript.done"}
    seen_types: set[str] = set()
    try:
        async for raw in openai_ws:
            event = json.loads(raw)
            etype = event.get("type")

            # (b) Log the first occurrence of every OpenAI event type so we can
            # see exactly what the API emits (and catch typos in event names).
            if etype not in seen_types:
                seen_types.add(etype)
                logger.info("openai event (first seen): %s", etype)

            if etype in audio_delta_types:
                delta = event.get("delta")
                state["out_deltas"] += 1
                if state["out_deltas"] == 1:
                    logger.info("(b) first output-audio event from OpenAI (%s)", etype)
                if not delta:
                    logger.warning("output-audio event with empty delta: %s", etype)
                    continue
                # (c) mu-law chunk -> Twilio media frame with the streamSid.
                await ws.send_json({
                    "event": "media",
                    "streamSid": state["stream_sid"],
                    "media": {"payload": delta},
                })
                state["out_forwarded"] += 1
                if state["out_forwarded"] == 1:
                    logger.info("(c) first output frame -> Twilio sid=%s", state["stream_sid"])
                state["bot_speaking"] = True

            elif etype == "input_audio_buffer.speech_started":
                logger.info(
                    "openai VAD: agent speech started (bot_speaking=%s response_active=%s)",
                    state["bot_speaking"], state["response_active"],
                )
                # Barge-in: flush Twilio's queued bot audio if the bot is talking.
                if state["bot_speaking"]:
                    await ws.send_json({"event": "clear", "streamSid": state["stream_sid"]})
                    state["bot_speaking"] = False
                # Only cancel when a response is actually in progress, else OpenAI
                # returns "response_cancel_not_active".
                if state["response_active"]:
                    await openai_ws.send(json.dumps({"type": "response.cancel"}))
                    state["response_active"] = False

            elif etype == "input_audio_buffer.speech_stopped":
                logger.info("openai VAD: agent speech stopped (commit -> response expected)")

            elif etype == "input_audio_buffer.committed":
                logger.info("(a) OpenAI committed input audio buffer")

            elif etype == "response.created":
                logger.info("openai response.created (model is generating a reply)")
                state["response_active"] = True

            elif etype == "response.output_audio.done":
                state["bot_speaking"] = False

            elif etype in ("response.done", "response.cancelled"):
                state["bot_speaking"] = False
                state["response_active"] = False

            elif etype in transcript_done_types:
                _log_turn(state, "patient", event.get("transcript", ""))

            elif etype == "conversation.item.input_audio_transcription.completed":
                _log_turn(state, "agent", event.get("transcript", ""))

            elif etype == "error":
                # Full error: a rejected session.update field shows up here and
                # would silently break audio.
                logger.error("openai error: %s", json.dumps(event.get("error", event)))
    except websockets.ConnectionClosed:
        logger.info("openai disconnected sid=%s", state["stream_sid"])
    except WebSocketDisconnect:
        pass
