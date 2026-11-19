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

## Release-candidate channel workaround

The rc1 Mantle resolver inserts Inspector's default Deepgram speech settings even
when this profile selects a native Rime speech model. The built-in Inspector then
refuses both media modes. `rime_channel.RimeOnlyInspector` removes only those
exact built-in defaults before passing the configuration to the native Inspector.
It refuses another configured speech engine. It never calls Deepgram and does not
patch the installed wheel or change the transfer guard. The full native channel
resolver is exercised in this profile's tests. Remove this adapter after the
upstream resolver is fixed and that removal has passed a fresh native run.
