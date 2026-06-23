"""Outbound call placement via the Twilio REST API.

Places a recorded outbound call that points Twilio at our /twiml endpoint.
The OpenAI media-stream bridge is not wired in yet; this proves the telephony
path (dialing, reachability, recording).
"""

from __future__ import annotations

import logging
from urllib.parse import urlencode

from twilio.rest import Client

from settings import load_settings

logger = logging.getLogger(__name__)

# Hard cap on call length so a stuck/runaway call can't ring up indefinitely.
MAX_CALL_SECONDS = 240


def place_call(to_number: str, scenario_id: str | None = None) -> str:
    """Place a recorded outbound call to ``to_number``.

    Args:
        to_number: E.164 number to dial.
        scenario_id: optional scenario id, appended to the TwiML URL as a query
            param for forward-compatibility (not used by the server yet).

    Returns:
        The Twilio Call SID.
    """
    settings = load_settings()
    client = Client(settings.twilio_account_sid, settings.twilio_auth_token)

    url = f"https://{settings.public_host}/twiml"
    if scenario_id:
        url = f"{url}?{urlencode({'scenario': scenario_id})}"

    call = client.calls.create(
        from_=settings.twilio_from_number,
        to=to_number,
        url=url,
        record=True,
        time_limit=MAX_CALL_SECONDS,  # safety cap; Twilio ends the call after this
    )
    logger.info("placed call from=%s to=%s sid=%s", settings.twilio_from_number, to_number, call.sid)
    return call.sid
