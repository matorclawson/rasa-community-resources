"""Native loader/config checks; no model, provider or bank network calls."""
import importlib.util
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import socket

HERE = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("silverlake_rime_profile", HERE / "run_demo.py")
profile = importlib.util.module_from_spec(spec)
spec.loader.exec_module(profile)


class ProfileTests(unittest.TestCase):
    def setUp(self):
        self.guard = patch.object(socket.socket, "connect", side_effect=AssertionError("network_forbidden"))
        self.guard.start()
        self.addCleanup(self.guard.stop)

    def test_temporary_project_preserves_existing_bank_sources(self):
        with tempfile.TemporaryDirectory() as directory:
            target = profile.prepare(directory)
            for relative in ("agent.yml", "hooks.py", "skills/banking/skill.md", "skills/banking/tools.py"):
                self.assertEqual((target / relative).read_bytes(), (profile.BANK / relative).read_bytes())
            self.assertFalse((target / ".env").exists())
            self.assertFalse((target / ".venv").exists())

    def test_actual_profile_uses_native_rime_not_second_speech_vendor(self):
        import yaml
        from rasa.core.channels.voice_stream.speech_model.factory import speech_model_from_config
        from rasa.core.channels.voice_stream.audio_bytes import L16_16KHZ
        from rasa.core.channels.voice_stream.speech_model.rime_prism import RimePrismSpeechModel
        config = yaml.safe_load((HERE / "integrations.yml").read_text())
        channel = config["channels"]["inspector"]
        self.assertNotIn("asr", channel)
        self.assertNotIn("tts", channel)
        with patch.dict("os.environ", {"RIME_API_KEY": "offline-placeholder"}):
            engine = speech_model_from_config(channel["speech_model"], L16_16KHZ)
        self.assertIsInstance(engine, RimePrismSpeechModel)

    def test_exact_runtime_and_source_lock(self):
        import importlib.metadata
        import tomllib
        self.assertEqual(importlib.metadata.version("rasa-pro"), "3.22.0rc1")
        locked = tomllib.loads((HERE / "uv.lock").read_text())
        rasa = next(p for p in locked["package"] if p["name"] == "rasa-pro")
        self.assertEqual(rasa["version"], "3.22.0rc1")
        self.assertEqual(rasa["wheels"][0]["hash"], "sha256:b05acc14b16a038f76fde95e06a22704be750aa10cbf2998a70fa5927db3dbcf")


if __name__ == "__main__":
    unittest.main()
