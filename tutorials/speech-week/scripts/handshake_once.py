"""One bounded native-provider handshake; no caller audio, model or bank task."""
import argparse
import asyncio
import contextlib
from datetime import datetime, timezone
import importlib.metadata
import io
import json
import os
from pathlib import Path
import stat


def utc():
    return datetime.now(timezone.utc).isoformat()


async def probe(provider):
    from rasa.core.channels.voice_stream.audio_bytes import L16_16KHZ
    if provider == "rime-prism":
        from rasa.core.channels.voice_stream.speech_model.factory import speech_model_from_config
        engine = speech_model_from_config({"name": "rime_prism", "voice": "aurora",
            "instructions": "Qualification handshake only. Do not initiate a response."}, L16_16KHZ)
        close = engine.close
    else:
        from rasa.api.voice.asr.v1.speechmatics import SpeechmaticsASR
        engine = SpeechmaticsASR.from_config_dict({"region": "eu", "language_map": {
            "en": {"language": "en", "model": "linden-1"}}}, L16_16KHZ, "en")
        close = engine.close_connection
    try:
        await asyncio.wait_for(engine.connect(), timeout=20)
        return {"outcome": "HANDSHAKE_ACCEPTED", "audio_sent": False}
    except Exception as error:
        status = getattr(getattr(error, "response", None), "status_code", None)
        return {"outcome": "HANDSHAKE_FAILED", "exception_type": type(error).__name__,
                "http_status": status if isinstance(status, int) else None, "audio_sent": False}
    finally:
        with contextlib.suppress(Exception):
            await asyncio.wait_for(close(), timeout=5)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("provider", choices=["rime-prism", "speechmatics"])
    parser.add_argument("--state-dir", type=Path, required=True)
    args = parser.parse_args()
    if importlib.metadata.version("rasa-pro") != "3.22.0rc1":
        raise SystemExit("Use the exact locked rc1 environment")
    args.state_dir.mkdir(mode=0o700, parents=True, exist_ok=True)
    info = args.state_dir.stat(follow_symlinks=False)
    if not stat.S_ISDIR(info.st_mode) or stat.S_IMODE(info.st_mode) & 0o077:
        raise SystemExit("Use a private state directory")
    path = args.state_dir / (args.provider + "-handshake.jsonl")
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    def retain(value):
        os.write(fd, (json.dumps(value, sort_keys=True) + "\n").encode())
        os.fsync(fd)
    retain({"phase": "intent", "at": utc(), "provider": args.provider, "attempt_limit": 1})
    directory = os.open(args.state_dir, os.O_RDONLY)
    os.fsync(directory)
    os.close(directory)
    try:
        # Native exceptions/HTTP headers must never reach caller logs.
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            result = asyncio.run(probe(args.provider))
        result.update(phase="result", at=utc(), provider=args.provider, attempts=1,
                      scope="Provider handshake only; no voice/model/bank acceptance")
        retain(result)
        print(json.dumps(result))
    finally:
        os.close(fd)


if __name__ == "__main__":
    main()
