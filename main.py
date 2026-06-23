"""CLI entry point: list scenarios and place test calls.

Phase 2: --test-call places a real recorded outbound call, waits for it to
finish, and downloads the recording as mp3. The OpenAI media-stream bridge is
not implemented yet.

Usage:
    python main.py --list                    # list available scenarios
    python main.py --test-call               # call settings.target_number
    python main.py --test-call +15551234567  # call a specific number

The web server (server.py) must be running and reachable at PUBLIC_HOST (via
ngrok) before placing a call — Twilio fetches TwiML from that public host.
"""

from __future__ import annotations

import argparse
import logging
import time

from caller import place_call
from scenarios import SCENARIOS
from settings import load_settings
from transcripts import download_recording

# Twilio call statuses that mean the call is over.
_TERMINAL_STATUSES = {"completed", "failed", "busy", "no-answer", "canceled"}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Place an automated patient call.")
    parser.add_argument(
        "--scenario",
        help="scenario id to run (see --list)",
        choices=sorted(SCENARIOS),
    )
    parser.add_argument(
        "--list",
        action="store_true",
        help="list available scenarios and exit",
    )
    parser.add_argument(
        "--test-call",
        nargs="?",
        const="",  # flag present without a value -> use settings.target_number
        metavar="NUMBER",
        help="place a recorded test call to NUMBER (default: TARGET_NUMBER)",
    )
    return parser


def _list_scenarios() -> None:
    print("Available scenarios:")
    for sid, sc in SCENARIOS.items():
        print(f"  {sid:20s} {sc.title}")


def _wait_for_completion(settings, call_sid: str, timeout: float = 300.0, interval: float = 3.0) -> str:
    """Poll the call status until terminal or timeout. Returns last status."""
    from twilio.rest import Client

    client = Client(settings.twilio_account_sid, settings.twilio_auth_token)
    deadline = time.monotonic() + timeout
    status = "queued"
    while time.monotonic() < deadline:
        status = client.calls(call_sid).fetch().status
        print(f"  call status: {status}")
        if status in _TERMINAL_STATUSES:
            return status
        time.sleep(interval)
    return status


def _place_and_collect(to_number: str, scenario_id: str | None) -> None:
    """Place a call, wait for it to finish, then download the recording."""
    settings = load_settings()
    label = f"scenario {scenario_id!r}" if scenario_id else "test call"
    print(f"Placing {label} to {to_number} ...")

    call_sid = place_call(to_number, scenario_id)
    print(f"Call SID: {call_sid}")

    status = _wait_for_completion(settings, call_sid)
    print(f"Final call status: {status}")

    print("Downloading recording (may take a few seconds) ...")
    path = download_recording(call_sid)
    if path:
        print(f"Recording saved: {path}")
    else:
        print("No recording available (call may not have connected).")


def _run_test_call(target: str) -> None:
    settings = load_settings()
    _place_and_collect(target or settings.target_number, None)


def _run_scenario_call(scenario_id: str) -> None:
    settings = load_settings()
    _place_and_collect(settings.target_number, scenario_id)


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    for _noisy in ("twilio", "urllib3", "httpx", "httpcore"):
        logging.getLogger(_noisy).setLevel(logging.WARNING)
    args = build_parser().parse_args()

    if args.test_call is not None:
        _run_test_call(args.test_call)
        return

    if args.scenario:
        _run_scenario_call(args.scenario)
        return

    _list_scenarios()


if __name__ == "__main__":
    main()
