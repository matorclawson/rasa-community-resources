# Rasa + Jack Henry SilverLake + Rime: verify before confirming a transfer

Work in progress. No completed voice run or recording is claimed yet.

This profile reuses the repository's SilverLake teaching host and banking skill.
Its agent configuration replaces the old `llm.model_group` with the required
rc1 `orchestrator.model_group`. It changes the speech interface to native Rime Prism on exactly Rasa Pro 3.22.0rc1.
Rime is the only speech vendor. The Rasa orchestrator uses OpenAI for tool planning;
that is a model dependency, not a second speech provider.

All bank data is fictional. Requests go to the local SOAP mock, checked against
Jack Henry's public jXchange definitions. No real account, sign-in or transfer is used.
Saying “verify me” refreshes a simulated grant; it is not customer authentication.

Use a new selected environment, not the original SilverLake environment:

```sh
python3 scripts/workspace.py start tutorials/speech-week/silverlake-rime --owner rasa-silverlake-rime-rc1-20261119
```

Download the public vendor archive with the original example's documented manual
step (`make download` in `examples/jack-henry-silverlake`). Then run `make run`
here. Keys are RASA_PRO_LICENSE, OPENAI_API_KEY and RIME_API_KEY. Never print values.
The launcher reads those values in memory and copies only committed project source
into a temporary run directory; it does not copy an environment or dependency tree.

Try “verify me”, request an own-account transfer, then say “confirm transfer”.
For a separate run, wait until the verification grant expires before confirming.
Preserve the original event/voice outputs and compare the host's refusal with its
journal. Successful text is not voice acceptance; a provider handshake is not a
completed banking conversation. No recording result is asserted in this draft.

The reused host checks the grant again after the review is delivered and again at
confirmation. Existing guard tests give offline boundary examples; this new rc1
profile still needs its own native run, actual audio and check-removed proof.

## Current release-candidate blocker

The full Inspector startup is blocked on rc1: Mantle fills default Deepgram ASR
and TTS settings even when this profile selects native Rime Prism. Inspector
then correctly refuses both media modes. A trial Inspector subclass was also
rejected because rc1 custom channels must use its published API contract; that
trial is reverted. No installed wheel, channel validation or bank guard is patched.
The native engine checks pass, but they do not establish full voice readiness.
The REST-only developer check disables Inspector and does not test speech.
