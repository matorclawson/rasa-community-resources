"""Explicit one-customer Codespace configuration; never discover a recipient."""
from __future__ import annotations

import os
from pathlib import Path
import re

from pydantic import SecretStr


class ConfigurationError(ValueError):
    pass


class Settings:
    @classmethod
    def environment(cls, values=None):
        values = os.environ if values is None else values
        names = ("TWILIO_ACCOUNT_SID", "TWILIO_AUTH_TOKEN", "SHOP_WHATSAPP_CUSTOMER",
                 "SHOP_SHEET_ID", "GOOGLE_TOKEN_JSON", "OPENAI_API_KEY", "RASA_PRO_LICENSE", "CODESPACE_NAME")
        missing = [name for name in names if not values.get(name)]
        if missing:
            raise ConfigurationError("Missing settings: " + ", ".join(missing))
        if not re.fullmatch(r"AC[0-9a-fA-F]{32}", values["TWILIO_ACCOUNT_SID"]):
            raise ConfigurationError("TWILIO_ACCOUNT_SID must be an Account SID, not an API key SID")
        if not re.fullmatch(r"\+[1-9][0-9]{6,14}", values["SHOP_WHATSAPP_CUSTOMER"]):
            raise ConfigurationError("SHOP_WHATSAPP_CUSTOMER must name the admitted customer in E.164 form")
        if not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", values["CODESPACE_NAME"]):
            raise ConfigurationError("Invalid Codespace identity")
        if not re.fullmatch(r"[A-Za-z0-9_-]{20,120}", values["SHOP_SHEET_ID"]):
            raise ConfigurationError("Invalid SHOP_SHEET_ID")
        instance = cls()
        instance.account_sid = values["TWILIO_ACCOUNT_SID"]
        # The corrected operator input is the account Auth Token. Never fall
        # back to the historical API-key-secret name for signature validation.
        instance.auth_token = SecretStr(values["TWILIO_AUTH_TOKEN"])
        instance.customer = values["SHOP_WHATSAPP_CUSTOMER"]
        # Public new-trial sender confirmed by the operator through Architect
        # msg-architect-arch-whatsapp-trial-flow-20261119. No customer discovery.
        instance.sender = "+447723317807"
        instance.port = 8080
        instance.public_base = "https://" + values["CODESPACE_NAME"] + "-8080.app.github.dev"
        instance.state_directory = Path(values.get("SHOP_WHATSAPP_STATE_DIR", ".state-whatsapp")).absolute()
        instance.spreadsheet_id = values["SHOP_SHEET_ID"]
        instance.google_token_json = SecretStr(values["GOOGLE_TOKEN_JSON"])
        return instance
