# Rasa + Jack Henry SilverLake + Deepgram: transfers with authoritative balances

Work in progress; no full voice acceptance or recording is claimed yet.

This cell starts from the existing `banking-transfer` case and reuses the
SilverLake teaching host, SOAP client, mock, journal, hooks and skill. It uses
Deepgram Nova 3 for recognition and Deepgram Aura for speech output on exactly
Rasa Pro 3.22.0rc1. There is one speech vendor. OpenAI plans the Rasa tool calls.

All bank data is fictional. The mock replies are checked against the public
Jack Henry jXchange definitions. Nothing contacts a real bank. A spoken identity
claim is not authentication, and “verify me” is only a simulated teaching grant.

Select this separate locked environment using the workspace helper. Download
and verify the public archive as documented in `examples/jack-henry-silverlake`.
Set RASA_PRO_LICENSE, OPENAI_API_KEY and DEEPGRAM_API_KEY without printing values.
`make run` opens Inspector with Deepgram; `make text` is a REST-only developer
check and does not initialize the unused voice channel.

The bank's returned available balance is authoritative for this exercise.
Do not calculate a new balance from the model's words or treat an accepted
transfer request as a posted transaction. Native voice runs and check-removed
proofs must be recorded before this cell is ready for publication.
