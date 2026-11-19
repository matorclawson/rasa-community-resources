# Rasa Mantle with Rime Prism speech-to-speech (3.22.0rc1)

Work in progress. Exact release-candidate configuration is derived from the pinned wheel, not the old voice router. Native checks and a real provider recording are separate receipts; neither is claimed by these source files.

Create only this project environment from its committed pyproject.toml and uv.lock with scripts/workspace.py start, using a distinct owner. `make test` runs offline contract checks. `make inspect` uses the configured provider credentials and dialogue model; run it only for the approved bounded demonstration.

The task is fictional Juniper Library hours. Use the same day question for clean speech, a mid-sentence pause, an interruption and labelled noise. Preserve original audio, provider/agent events, source/lock hashes and failed outcomes privately. Do not claim a recording from a synthetic transcript.

Rime Prism is a native speech model, not the separate Rime Coda synthesis engine. Its key is RIME_API_KEY.
