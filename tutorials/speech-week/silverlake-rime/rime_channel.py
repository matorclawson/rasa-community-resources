"""Narrow rc1 workaround: discard only injected Inspector speech defaults.

rc1's Mantle channel resolver fills default Deepgram ASR/TTS even for a native
speech_model. The native Inspector correctly rejects that mixed configuration.
This profile admits only Rime Prism and removes those exact built-in defaults;
any other cascaded value is refused. No engine, permission or bank rule changes.
"""
from rasa.core.channels.inspector import InspectorInputChannel
from rasa.shared.exceptions import InvalidConfigException


class RimeOnlyInspector(InspectorInputChannel):
    @classmethod
    def from_credentials(cls, credentials):
        data = dict(credentials or {})
        speech = data.get("speech_model")
        if not isinstance(speech, dict) or speech.get("name") != "rime_prism":
            raise InvalidConfigException("This profile requires only native Rime Prism.")
        for side in ("asr", "tts"):
            if side in data:
                if data[side] != cls.DEFAULT_SPEECH_CONFIG[side]:
                    raise InvalidConfigException("A second speech provider is not allowed in this profile.")
                data.pop(side)
        return super().from_credentials(data)
