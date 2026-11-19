"""Actual rc1 engine factory/config checks; never connect to a provider."""
import unittest
from rasa.core.channels.voice_stream.audio_bytes import L16_16KHZ
from rasa.core.channels.voice_stream.speech_model.factory import speech_model_from_config
from rasa.core.channels.voice_stream.speech_model.rime_prism import RimePrismConfig, RimePrismEngine
from rasa.shared.exceptions import InvalidConfigException
from pydantic import ValidationError


class PrismContract(unittest.TestCase):
    def test_native_prism_factory_builds_speech_model_without_connecting(self):
        engine = speech_model_from_config({"name": "rime_prism", "voice": "aurora",
            "instructions": "Use fictional library hours from the background assistant."}, L16_16KHZ)
        self.assertIsInstance(engine, RimePrismEngine)
        self.assertFalse(engine._started)

    def test_tts_provider_name_is_not_a_prism_speech_model(self):
        with self.assertRaises(InvalidConfigException) as error:
            speech_model_from_config({"name": "rime", "instructions": "Fictional fixture"}, L16_16KHZ)
        self.assertIn("rime_prism", str(error.exception))

    def test_blank_prism_instructions_are_rejected_before_connecting(self):
        with self.assertRaises(ValidationError):
            RimePrismConfig(instructions=" ")


if __name__ == "__main__":
    unittest.main()
