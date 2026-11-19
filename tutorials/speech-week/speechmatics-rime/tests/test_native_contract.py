"""Actual rc1 model-group mapper checks; no SDK network or credentials."""
import unittest
import os
# Use the dependency-bundled pricing map; do not fetch one during config checks.
os.environ["LITELLM_LOCAL_MODEL_COST_MAP"] = "True"
from pathlib import Path
from rasa.mantle.config.channels import load_integration_speech_inputs
from rasa.mantle.config.speech_model_group import resolve_speech_model_group
from rasa.shared.exceptions import InvalidConfigException


def groups(**extra):
    return [{"id": "input", "models": [{"provider": "speechmatics",
        "api_key": "${SPEECHMATICS_API_KEY}", "region": "eu",
        "language_map": {"en": {"language": "en", "model": "linden-1"}}, **extra}]}]


class SpeechmaticsContract(unittest.TestCase):
    def test_companion_file_resolves_two_explicit_native_provider_groups(self):
        channels, configured = load_integration_speech_inputs(Path.cwd())
        self.assertEqual(resolve_speech_model_group(channels["inspector"]["asr"], configured,
                                                  slot="asr")["provider"], "speechmatics")
        self.assertEqual(resolve_speech_model_group(channels["inspector"]["tts"], configured,
                                                  slot="tts")["provider"], "rime")

    def test_native_agent_stt_group_resolves_without_old_router(self):
        config = resolve_speech_model_group("input", groups(), slot="asr")
        self.assertEqual(config["provider"], "speechmatics")
        self.assertEqual(config["language_map"]["en"]["model"], "linden-1")

    def test_old_realtime_adapter_tuning_is_not_a_native_agent_stt_config(self):
        for key, value in {"operating_point": "enhanced", "max_delay": 1.0,
                           "end_of_utterance_silence_trigger": 0.7}.items():
            with self.subTest(key=key):
                with self.assertRaises(InvalidConfigException) as error:
                    resolve_speech_model_group("input", groups(**{key: value}), slot="asr")
                self.assertIn(key, str(error.exception))

    def test_language_is_explicit_even_when_model_is_named(self):
        data = groups(); del data[0]["models"][0]["language_map"]["en"]["language"]
        with self.assertRaises(InvalidConfigException):
            resolve_speech_model_group("input", data, slot="asr")

    def test_asr_provider_cannot_be_relabelled_as_native_tts(self):
        with self.assertRaises(InvalidConfigException):
            resolve_speech_model_group("input", groups(), slot="tts")


if __name__ == "__main__":
    unittest.main()
