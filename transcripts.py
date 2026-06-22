"""Transcript writing and Twilio recording download.

Stub only. Helpers to (1) persist a timestamped, both-sides transcript of a
call to transcripts/, and (2) download the call's Twilio recording as mp3 into
recordings/.
"""

from __future__ import annotations

import logging
import os
import time
import urllib.error
import urllib.request
from dataclasses import dataclass

from twilio.rest import Client

from settings import Settings, load_settings

logger = logging.getLogger(__name__)

TRANSCRIPTS_DIR = "transcripts"
RECORDINGS_DIR = "recordings"


@dataclass(frozen=True)
class TranscriptTurn:
    """One utterance in the conversation."""

    speaker: str  # "patient" (our bot) or "agent" (the called party)
    text: str
    timestamp: str  # ISO 8601


def write_transcript(call_sid: str, scenario_id: str, turns: list[TranscriptTurn]) -> str:
    """Write a per-call transcript file and return its path.

    Args:
        call_sid: Twilio Call SID (used in the filename).
        scenario_id: scenario that was run (recorded in the header).
        turns: ordered conversation turns, both sides, each timestamped.

    Returns:
        Path to the written file, e.g. transcripts/CA123..._new_appointment.txt.

    TODO:
        - Build a filename from a timestamp + scenario_id + call_sid.
        - Write a header (scenario, call_sid, start time) then one line per turn:
          "[HH:MM:SS] PATIENT: ..." / "[HH:MM:SS] AGENT: ...".
        - Consider also dumping the raw event list as JSON for debugging.
    """
    raise NotImplementedError("write_transcript is a stub")


def download_recording(
    call_sid: str,
    out_path: str | None = None,
    timeout: float = 60.0,
    interval: float = 3.0,
) -> str | None:
    """Poll for the call's Twilio recording, download it as mp3, save it.

    A recording is not available until shortly after the call ends, so this
    polls ``client.recordings.list(call_sid=...)`` with a short backoff until a
    recording appears or ``timeout`` (seconds) elapses.

    Args:
        call_sid: the call whose recording to fetch.
        out_path: where to save the mp3. Defaults to recordings/<call_sid>.mp3.
        timeout: max seconds to wait for the recording to become available.
        interval: seconds between polls.

    Returns:
        Path to the saved mp3, or ``None`` if no recording appeared in time.
    """
    settings = load_settings()
    client = Client(settings.twilio_account_sid, settings.twilio_auth_token)

    if out_path is None:
        os.makedirs(RECORDINGS_DIR, exist_ok=True)
        out_path = os.path.join(RECORDINGS_DIR, f"{call_sid}.mp3")
    else:
        os.makedirs(os.path.dirname(out_path) or ".", exist_ok=True)

    deadline = time.monotonic() + timeout
    while True:
        recordings = client.recordings.list(call_sid=call_sid, limit=1)
        if recordings:
            recording = recordings[0]
            # Media URL = recording resource URI with .mp3 instead of .json.
            url = f"https://api.twilio.com/2010-04-01/Accounts/{settings.twilio_account_sid}/Recordings/{recording.sid}.mp3"
            _download_with_auth(url, out_path, settings)
            logger.info("saved recording sid=%s -> %s", recording.sid, out_path)
            return out_path

        if time.monotonic() >= deadline:
            logger.warning("no recording for call_sid=%s after %.0fs", call_sid, timeout)
            return None

        logger.info("recording not ready for call_sid=%s; retrying in %.0fs", call_sid, interval)
        time.sleep(interval)


def _download_with_auth(
    url: str,
    out_path: str,
    settings: Settings,
    timeout: float = 30.0,
    interval: float = 2.0,
) -> None:
    """Fetch ``url`` with Twilio basic auth and write the bytes to ``out_path``.

    The mp3 can lag a few seconds behind the call ending, so HTTP 404s are
    retried with a short wait for up to ``timeout`` seconds.
    """
    import base64

    token = base64.b64encode(
        f"{settings.twilio_account_sid}:{settings.twilio_auth_token}".encode()
    ).decode()
    req = urllib.request.Request(url, headers={"Authorization": f"Basic {token}"})

    deadline = time.monotonic() + timeout
    while True:
        try:
            with urllib.request.urlopen(req) as resp, open(out_path, "wb") as fh:
                fh.write(resp.read())
            return
        except urllib.error.HTTPError as exc:
            if exc.code != 404 or time.monotonic() >= deadline:
                raise
            logger.info("mp3 not ready (404); retrying in %.0fs", interval)
            time.sleep(interval)
