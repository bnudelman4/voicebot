"""Transcript writing and Twilio recording download.

Numbering: transcript-NN.txt and recording-NN.mp3 share the same NN so both
files for one call line up. The NN is the max existing number across BOTH
folders, plus one (zero-padded to 2 digits).

How the two files get the same NN across two processes:
The server process holds the turns and writes the transcript when the Twilio
stream stops, choosing NN via next_sequence_number(). The transcript header
embeds the Twilio Call SID. main.py (a separate process) then looks up that
SID with find_sequence_for_call() to recover the same NN and names the mp3
recording-NN.mp3 to match. No IPC/shared state needed; the on-disk transcript
is the source of truth. (Assumes one call at a time, which the CLI enforces.)
"""

from __future__ import annotations

import datetime
import glob
import logging
import os
import re
import time
import urllib.error
import urllib.request

from twilio.rest import Client

from scenarios import PATIENT_NAME
from settings import Settings, load_settings

logger = logging.getLogger(__name__)

TRANSCRIPTS_DIR = "transcripts"
RECORDINGS_DIR = "recordings"
PATIENT_DOB_ISO = "2006-03-31"  # Benjamin Nudelman


def _max_seq(pattern: str, regex: str) -> int:
    """Largest NN matched by ``regex`` across files matching ``pattern`` (0 if none)."""
    nums = [int(m.group(1)) for p in glob.glob(pattern) if (m := re.search(regex, os.path.basename(p)))]
    return max(nums, default=0)


def next_sequence_number() -> str:
    """Next 2-digit NN = max existing across both folders + 1 (e.g. '03')."""
    highest = max(
        _max_seq(os.path.join(TRANSCRIPTS_DIR, "transcript-*.txt"), r"transcript-(\d+)\.txt$"),
        _max_seq(os.path.join(RECORDINGS_DIR, "recording-*.mp3"), r"recording-(\d+)\.mp3$"),
    )
    return f"{highest + 1:02d}"


def transcript_path(seq: str) -> str:
    """Path for transcript NN."""
    return os.path.join(TRANSCRIPTS_DIR, f"transcript-{seq}.txt")


def find_sequence_for_call(call_sid: str) -> str | None:
    """Return the NN of the transcript whose header references ``call_sid``."""
    for p in glob.glob(os.path.join(TRANSCRIPTS_DIR, "transcript-*.txt")):
        try:
            with open(p, encoding="utf-8") as fh:
                if call_sid in fh.read():
                    m = re.search(r"transcript-(\d+)\.txt$", os.path.basename(p))
                    if m:
                        return m.group(1)
        except OSError:
            continue
    return None


def write_transcript(turns: list[dict], seq: str, scenario_id: str | None, call_sid: str | None) -> str:
    """Write transcripts/transcript-NN.txt and return its path.

    Args:
        turns: ordered turns as captured live; each a dict with keys
            ``speaker`` (agent/patient), ``text``, and ``ts`` ("MM:SS").
        seq: 2-digit sequence number NN (from next_sequence_number()).
        scenario_id: scenario that was run (header).
        call_sid: Twilio Call SID (header; used later to match the recording).
    """
    os.makedirs(TRANSCRIPTS_DIR, exist_ok=True)
    path = transcript_path(seq)
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    lines = [
        f"Scenario:  {scenario_id or '(none)'}",
        f"Call SID:  {call_sid or '(unknown)'}",
        f"Date/time: {now}",
        f"Patient:   {PATIENT_NAME}, DOB {PATIENT_DOB_ISO}",
        "-" * 48,
    ]
    for t in turns:
        lines.append(f"[{t['ts']}] {t['speaker'].upper()}: {t['text']}")

    with open(path, "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines) + "\n")
    logger.info("wrote transcript %s (%d turns)", path, len(turns))
    return path


def download_recording(
    call_sid: str,
    seq: str,
    timeout: float = 60.0,
    interval: float = 3.0,
) -> str | None:
    """Poll for the call's Twilio recording, download it as recording-NN.mp3.

    A recording is not available until shortly after the call ends, so this
    polls ``client.recordings.list(call_sid=...)`` with a short backoff until a
    recording appears or ``timeout`` (seconds) elapses.

    Args:
        call_sid: the call whose recording to fetch.
        seq: 2-digit NN matching the call's transcript (recording-NN.mp3).
        timeout: max seconds to wait for the recording to become available.
        interval: seconds between polls.

    Returns:
        Path to the saved mp3, or ``None`` if no recording appeared in time.
    """
    settings = load_settings()
    client = Client(settings.twilio_account_sid, settings.twilio_auth_token)

    os.makedirs(RECORDINGS_DIR, exist_ok=True)
    out_path = os.path.join(RECORDINGS_DIR, f"recording-{seq}.mp3")

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
