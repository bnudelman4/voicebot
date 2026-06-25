## Architecture

`main.py` places an outbound call through the Twilio REST API with the call's
TwiML URL pointing at the FastAPI server (`server.py`), which is exposed to the
internet via ngrok on a reserved domain (`PUBLIC_HOST`). Twilio connects the
call and fetches that TwiML, which returns a `<Connect><Stream>` directing
Twilio to open a **bidirectional Media Stream websocket** back to the server's
`/media-stream` endpoint. The server reads the scenario id from the stream's
start event, loads that scenario's persona, and bridges the call audio to the
**OpenAI Realtime API** over a second websocket: inbound caller audio is
forwarded to the model and the model's spoken reply is streamed back to Twilio.
Audio is **G.711 mu-law 8 kHz end to end**, matching Twilio's format exactly so
no transcoding is needed. The whole call is capped at a maximum duration by
Twilio so a stuck call can't run away.

The design favors low latency and natural turn-taking, so it uses OpenAI's
**speech-to-speech** Realtime model rather than a stitched STT → LLM → TTS
pipeline, with **server-side VAD** for turn detection. The bot **deliberately
does not speak first**, the clinic agent is the callee and greets first, so the
bot listens and lets the receptionist lead the opening before steering toward its
goal. The audio deliverable comes from **Twilio call recording**, while the
transcript is captured live from the Realtime API's transcription events (the
agent's words via input-audio transcription, the patient's via the output
transcript) and written to disk by the server when the stream stops. The
transcript and the recording for one call share the same sequence number so the
two files always pair up.
