"""Signed WhatsApp intake with durable acknowledgement, separate from the worker.

No messages are sent by this module. The Core parser verifies the exact public
URL; the local host retains the verified event before returning a success.
"""
from __future__ import annotations

from http.server import BaseHTTPRequestHandler, HTTPServer
import json
from pathlib import Path
import re
from urllib.parse import parse_qsl, urlsplit

from .state import open_state


class IntakeHeld(RuntimeError):
    pass


class Journal:
    """A private inbox; opaque SIDs are keys, never timestamps or offsets."""

    def __init__(self, path: Path):
        self.db = open_state(path)
        self.db.executescript("""
            CREATE TABLE IF NOT EXISTS wa_inbox (
                sequence INTEGER PRIMARY KEY AUTOINCREMENT,
                event_id TEXT NOT NULL UNIQUE,
                original TEXT NOT NULL,
                event TEXT NOT NULL,
                phase TEXT NOT NULL DEFAULT 'saved'
            );
            CREATE TABLE IF NOT EXISTS wa_callbacks (
                sequence INTEGER PRIMARY KEY AUTOINCREMENT,
                original TEXT NOT NULL UNIQUE,
                receipt TEXT NOT NULL
            );
        """)

    def close(self):
        self.db.close()

    def retain(self, event, params):
        original = json.dumps(params, sort_keys=True, separators=(",", ":"), allow_nan=False)
        payload = event.model_dump_json()
        self.db.execute("BEGIN IMMEDIATE")
        changed = False
        try:
            old = self.db.execute(
                "SELECT original,event FROM wa_inbox WHERE event_id=?", (event.event_id,)
            ).fetchone()
            if old is not None and old != (original, payload):
                self.db.execute("UPDATE wa_inbox SET phase='held' WHERE event_id=?", (event.event_id,))
                changed = True
            elif old is None:
                self.db.execute(
                    "INSERT INTO wa_inbox(event_id,original,event) VALUES(?,?,?)",
                    (event.event_id, original, payload),
                )
            self.db.execute("COMMIT")
        except BaseException:
            self.db.execute("ROLLBACK")
            raise
        if changed:
            raise IntakeHeld("ORIGINAL_EVENT_CHANGED")

    def callback(self, receipt, params):
        # Keep every distinct signed callback, including late/duplicate status
        # transitions. The worker must reconcile it against its saved send SID
        # and recipient; a callback alone never places an order.
        original = json.dumps(params, sort_keys=True, separators=(",", ":"), allow_nan=False)
        self.db.execute(
            "INSERT OR IGNORE INTO wa_callbacks(original,receipt) VALUES(?,?)",
            (original, receipt.model_dump_json()),
        )


class Intake:
    def __init__(self, journal, *, public_base, account_sid, token, customer, sender,
                 inbound_parser=None, status_parser=None):
        parsed = urlsplit(public_base)
        if (parsed.scheme != "https" or not parsed.hostname or parsed.username
                or parsed.password or parsed.query or parsed.fragment
                or parsed.path not in ("", "/") or parsed.port not in (None, 443)):
            raise ValueError("Use the exact public HTTPS origin without a path or query")
        if not re.fullmatch(r"AC[0-9a-fA-F]{32}", account_sid):
            raise ValueError("Invalid account identity")
        for number in (customer, sender):
            if not re.fullmatch(r"\+[1-9][0-9]{6,14}", number):
                raise ValueError("Use an explicit E.164 customer and sender")
        if inbound_parser is None or status_parser is None:
            from zeo_core.integrations.twilio_whatsapp import parse_inbound, parse_status_callback
            inbound_parser, status_parser = parse_inbound, parse_status_callback
        self.journal, self.public_base = journal, public_base.rstrip("/")
        self.account_sid, self.token = account_sid, token
        self.customer, self.sender = customer, sender
        self.inbound_parser, self.status_parser = inbound_parser, status_parser

    def accept(self, path, content_type, body, signature):
        if path not in ("/twilio/inbound", "/twilio/status"):
            return 404
        if content_type.split(";", 1)[0].strip().lower() != "application/x-www-form-urlencoded":
            return 415
        if not 0 < len(body) <= 65536:
            return 413
        try:
            pairs = parse_qsl(body.decode("utf-8", errors="strict"), keep_blank_values=True,
                              strict_parsing=True, max_num_fields=100, errors="strict")
            params = dict(pairs)
            if len(params) != len(pairs):
                return 400
            # No Host / X-Forwarded-* value can alter the signature URL.
            parser = self.inbound_parser if path == "/twilio/inbound" else self.status_parser
            event = parser(self.token, url=self.public_base + path, params=params, signature=signature)
            if params.get("AccountSid") != self.account_sid:
                return 403
            if path == "/twilio/inbound":
                if (event.sender_id != self.customer or event.conversation_id != self.customer
                        or event.recipient_id != self.sender):
                    return 403
                if not re.fullmatch(r"SM[0-9a-fA-F]{32}", event.event_id):
                    return 400
                self.journal.retain(event, params)
            else:
                if event.to != self.customer:
                    return 403
                if not re.fullmatch(r"SM[0-9a-fA-F]{32}", event.provider_message_id):
                    return 400
                self.journal.callback(event, params)
            # All database writes have committed before this success is returned.
            return 200
        except IntakeHeld:
            return 409
        except (ValueError, UnicodeError):
            return 403
        except Exception:
            # No exception text, provider payload, token or phone is logged.
            return 503


def server(intake, *, port=8080):
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass

        def do_GET(self):
            self.send_error(405)

        def do_POST(self):
            self.connection.settimeout(5)
            try:
                if self.headers.get("Transfer-Encoding") is not None:
                    status = 400
                elif len(self.headers.get_all("Content-Length", [])) != 1:
                    status = 411
                else:
                    length = int(self.headers["Content-Length"])
                    if not 0 < length <= 65536:
                        status = 413
                    else:
                        body = self.rfile.read(length)
                        status = (400 if len(body) != length else intake.accept(
                            self.path, self.headers.get("Content-Type", ""), body,
                            self.headers.get("X-Twilio-Signature")))
            except Exception:
                status = 400
            self.send_response(status)
            self.send_header("Content-Type", "application/xml")
            self.send_header("Cache-Control", "no-store")
            self.send_header("Connection", "close")
            response = b"<Response/>" if status == 200 else b""
            self.send_header("Content-Length", str(len(response)))
            self.end_headers()
            self.wfile.write(response)
            self.close_connection = True

    return HTTPServer(("0.0.0.0", port), Handler)
