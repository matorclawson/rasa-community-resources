"""Bounded native shop host; requires qualified locked environments before use."""
from __future__ import annotations

import asyncio
from contextlib import AsyncExitStack
from datetime import datetime, timezone
import fcntl
import os
from pathlib import Path
import signal
import sys

from .whatsapp_settings import Settings, ConfigurationError


async def drive(conversation, stop, *, seconds=900, max_turns=30):
    deadline = asyncio.get_running_loop().time() + seconds
    turns = 0
    conversation.assert_safe()
    while not stop.is_set() and turns < max_turns and asyncio.get_running_loop().time() < deadline:
        handled = await conversation.handle_next()
        turns += int(handled)
        if not stop.is_set():
            await conversation.notify_shipments()
        if not handled:
            await asyncio.sleep(0.25)
    return turns


async def run():
    settings = Settings.environment()
    project = Path(__file__).resolve().parent.parent
    # Import only after value-free configuration admission. An uninstalled Core
    # adapter is a source gap, not a reason to substitute a different channel.
    from zeo_core.integrations.twilio_whatsapp import TwilioCredentials, TwilioWhatsAppClient
    from .assistant import Assistant
    from .locked_versions import require_locked_version
    from .mcp_client import ShopClient
    from .state import open_state
    from .whatsapp_conversation import Conversation
    from .whatsapp_webhook import Intake, Journal, server
    require_locked_version(project, "zeocore")
    require_locked_version(project, "rasa-pro")
    server_python = project / "server" / ".venv" / "bin" / "python"
    if not server_python.is_file():
        raise ConfigurationError("Install the locked native and server environments first")
    path = settings.state_directory / "inbox.sqlite3"
    initial = open_state(path)
    initial.close()
    lock = os.open(path, os.O_RDWR | os.O_NOFOLLOW)
    try:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        stop = asyncio.Event()
        loop = asyncio.get_running_loop()
        for sig in (signal.SIGINT, signal.SIGTERM):
            loop.add_signal_handler(sig, stop.set)
        try:
            child_env = {name: os.environ[name] for name in ("PATH", "LANG", "HOME", "SSL_CERT_FILE") if name in os.environ}
            child_env.update(GOOGLE_TOKEN_JSON=settings.google_token_json.get_secret_value(),
                SHOP_SHEET_ID=settings.spreadsheet_id, SHOP_STATE_DIR=str(settings.state_directory),
                PYTHONDONTWRITEBYTECODE="1")
            clock = lambda: datetime.now(timezone.utc)
            async with AsyncExitStack() as stack:
                channel = TwilioWhatsAppClient(TwilioCredentials(account_sid=settings.account_sid, auth_token=settings.auth_token))
                stack.callback(channel.close)
                client = await stack.enter_async_context(ShopClient(str(server_python),
                    arguments=["-B", "-m", "shop_demo.server"], environment=child_env, directory=project))
                assistant = await stack.enter_async_context(Assistant(client, project=project,
                    state_directory=settings.state_directory, clock=clock))
                conversation = Conversation(path, customer=settings.customer, sender=settings.sender,
                    public_base=settings.public_base, channel=channel, assistant=assistant, orders=client, clock=clock)
                stack.callback(conversation.close)
                intake_journal = Journal(path)
                stack.callback(intake_journal.close)
                intake = Intake(intake_journal, public_base=settings.public_base, account_sid=settings.account_sid,
                    token=settings.auth_token, customer=settings.customer, sender=settings.sender)
                conversation.assert_safe()
                listener = server(intake, port=settings.port)
                listener_task = asyncio.create_task(asyncio.to_thread(listener.serve_forever, poll_interval=0.25))
                try:
                    print("WhatsApp host ready for the configured customer; Ctrl-C requests a clean stop.", flush=True)
                    turns = await drive(conversation, stop)
                finally:
                    await asyncio.to_thread(listener.shutdown)
                    await listener_task
                    listener.server_close()
                print(f"WhatsApp host stopped after {turns} retained turns; state preserved.", flush=True)
        finally:
            for sig in (signal.SIGINT, signal.SIGTERM):
                loop.remove_signal_handler(sig)
    finally:
        os.close(lock)


def main():
    try:
        asyncio.run(run())
    except ConfigurationError as error:
        print(str(error), file=sys.stderr)
        return 1
    except BaseException:
        print("WhatsApp host stopped or held. Preserve its private state and inspect the original turn/send before restarting.", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
