"""FastAPI server: TwiML endpoint + Twilio <-> OpenAI Realtime audio bridge.

Stub only. Two responsibilities, no real logic yet:

  1. GET/POST /twiml  -> return TwiML that tells Twilio to open a Media Stream
     to our /media-stream websocket.
  2. WS /media-stream -> bridge audio between the Twilio Media Stream and the
     OpenAI Realtime API websocket, and capture transcript events.

Run locally with:  uvicorn server:app --host 0.0.0.0 --port $PORT
(ngrok must forward PUBLIC_HOST to that port.)
"""

from __future__ import annotations

from fastapi import FastAPI, Request, WebSocket
from fastapi.responses import PlainTextResponse, Response
from twilio.twiml.voice_response import VoiceResponse

from settings import load_settings

settings = load_settings()
app = FastAPI(title="voicebot")


@app.get("/health", response_class=PlainTextResponse)
def health() -> str:
    """Liveness check — confirm the server is reachable (e.g. through ngrok)."""
    return "ok"


@app.api_route("/twiml", methods=["GET", "POST"])
async def twiml(request: Request) -> Response:
    """Return test TwiML that keeps the call connected long enough to record.

    Phase 2 placeholder: say a short line, then pause so the recording captures
    the called party. The bidirectional Media Stream (<Connect><Stream>) will
    replace this once the audio bridge is implemented.
    """
    vr = VoiceResponse()
    vr.say("This is an automated test call.")
    vr.pause(length=15)
    return Response(content=str(vr), media_type="application/xml")


@app.websocket("/media-stream")
async def media_stream(ws: WebSocket) -> None:
    """Bridge Twilio Media Stream audio to/from the OpenAI Realtime API.

    Twilio sends base64-encoded mu-law (g711_ulaw, 8kHz) JSON frames; the
    OpenAI Realtime API can consume and emit the same g711_ulaw format, so no
    resampling is needed.

    TODO:
        - await ws.accept().
        - Read Twilio "start" event; extract streamSid + the scenario parameter,
          then look up the persona via scenarios.get_scenario().
        - Open the OpenAI Realtime websocket (raw `websockets` client) to
          wss://api.openai.com/v1/realtime?model={settings.openai_realtime_model}
          with Authorization: Bearer {settings.openai_api_key}.
        - Send session.update: instructions=persona, voice=settings.openai_voice,
          input/output audio format = g711_ulaw, turn_detection=server_vad.
        - Run two concurrent pumps (asyncio.gather):
            * Twilio "media" frames  -> OpenAI input_audio_buffer.append
            * OpenAI audio deltas    -> Twilio "media" frames (streamSid)
          Handle Twilio "mark"/"stop" and OpenAI "speech_started" (barge-in).
        - Collect transcript events (input + output transcription deltas) and
          hand them to transcripts.write_transcript when the call ends.
        - Clean up both sockets on disconnect / error.
    """
    raise NotImplementedError("media_stream websocket is a stub")
