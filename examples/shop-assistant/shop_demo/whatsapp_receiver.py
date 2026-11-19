"""Bounded signed receiver only: no worker, model, order or outgoing message."""
from __future__ import annotations

import fcntl
from importlib.metadata import distribution
import json
import os
from pathlib import Path
import signal
import threading

from .whatsapp_settings import Settings
from .whatsapp_webhook import Intake, Journal, server

CORE_COMMIT = "41cc059f4f5f4639b21122d461b92998ece206e2"


def main():
    journal = listener = None
    descriptor = None
    try:
        settings = Settings.environment()
        installed = json.loads(distribution("zeocore").read_text("direct_url.json") or "{}")
        if installed.get("vcs_info", {}).get("commit_id") != CORE_COMMIT:
            raise RuntimeError("Receiver requires the qualified exact Core source pin")
        path = settings.state_directory / "inbox.sqlite3"
        journal = Journal(path)
        descriptor = os.open(path, os.O_RDWR | os.O_NOFOLLOW)
        fcntl.flock(descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)
        intake = Intake(journal, public_base=settings.public_base, account_sid=settings.account_sid,
                        token=settings.auth_token, customer=settings.customer, sender=settings.sender)
        listener = server(intake, port=settings.port)
        stop = threading.Event()
        for sig in (signal.SIGTERM, signal.SIGINT):
            signal.signal(sig, lambda *_: stop.set())
        # The worker remains absent. Retain events while the operator configures
        # the callback; expire without replay or restart after at most one hour.
        timer = threading.Timer(3600, stop.set)
        timer.daemon = True
        timer.start()
        listener.timeout = 0.5
        print("RECEIVER_READY sends=0 worker=absent ttl_seconds=3600", flush=True)
        try:
            while not stop.is_set():
                listener.handle_request()
        finally:
            timer.cancel()
        print("RECEIVER_STOPPED state=preserved", flush=True)
        return 0
    except Exception:
        # Never print credentials, request bodies, account or customer identities.
        print("RECEIVER_HELD inspect private setup without printing values", flush=True)
        return 1
    finally:
        if listener is not None:
            listener.server_close()
        if journal is not None:
            journal.close()
        if descriptor is not None:
            os.close(descriptor)


if __name__ == "__main__":
    raise SystemExit(main())
