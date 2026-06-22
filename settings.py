"""Configuration loading and validation.

Reads every required environment variable (see .env.example) into a single
immutable ``Settings`` object. Call :func:`load_settings` once at startup; it
raises a clear ``ConfigError`` listing all missing variables instead of failing
later with a cryptic ``KeyError`` deep in the call stack.
"""

from __future__ import annotations

import os
from dataclasses import dataclass

from dotenv import load_dotenv


class ConfigError(RuntimeError):
    """Raised when one or more required env vars are missing or invalid."""


@dataclass(frozen=True)
class Settings:
    """All runtime configuration, validated and typed."""

    openai_api_key: str
    openai_realtime_model: str
    openai_voice: str
    twilio_account_sid: str
    twilio_auth_token: str
    twilio_from_number: str
    target_number: str
    public_host: str  # hostname only, no scheme (e.g. "my-bot.ngrok.app")
    port: int

    @property
    def public_ws_url(self) -> str:
        """wss:// URL Twilio dials for the Media Stream websocket."""
        return f"wss://{self.public_host}/media-stream"

    @property
    def public_twiml_url(self) -> str:
        """https:// URL Twilio fetches for the call's TwiML."""
        return f"https://{self.public_host}/twiml"


# (name, default). default=None means the var is required.
_REQUIRED = (
    ("OPENAI_API_KEY", None),
    ("OPENAI_REALTIME_MODEL", "gpt-realtime"),
    ("OPENAI_VOICE", "alloy"),
    ("TWILIO_ACCOUNT_SID", None),
    ("TWILIO_AUTH_TOKEN", None),
    ("TWILIO_FROM_NUMBER", None),
    ("TARGET_NUMBER", "+18054398008"),
    ("PUBLIC_HOST", None),
    ("PORT", "8080"),
)


def load_settings() -> Settings:
    """Load .env, validate required vars, return a frozen ``Settings``.

    Raises:
        ConfigError: if any required variable is missing, or PORT is not an int.
    """
    load_dotenv()

    values: dict[str, str] = {}
    missing: list[str] = []
    for name, default in _REQUIRED:
        val = os.getenv(name, default)
        if val is None or val == "":
            missing.append(name)
        else:
            values[name] = val

    if missing:
        raise ConfigError(
            "Missing required environment variable(s): "
            + ", ".join(missing)
            + ". Copy .env.example to .env and fill them in."
        )

    try:
        port = int(values["PORT"])
    except ValueError as exc:
        raise ConfigError(f"PORT must be an integer, got {values['PORT']!r}") from exc

    return Settings(
        openai_api_key=values["OPENAI_API_KEY"],
        openai_realtime_model=values["OPENAI_REALTIME_MODEL"],
        openai_voice=values["OPENAI_VOICE"],
        twilio_account_sid=values["TWILIO_ACCOUNT_SID"],
        twilio_auth_token=values["TWILIO_AUTH_TOKEN"],
        twilio_from_number=values["TWILIO_FROM_NUMBER"],
        target_number=values["TARGET_NUMBER"],
        public_host=values["PUBLIC_HOST"],
        port=port,
    )
