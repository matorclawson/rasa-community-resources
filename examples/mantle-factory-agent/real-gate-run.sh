#!/bin/sh
# REAL GATE RUN, scripted mode only. Written for the Council to read before anyone runs it. Contains no secret.
# WHAT RUNS
#   1. ./demo setup: uv sync --project project --locked --python 3.12. Installs the locked project environment (rasa-pro
#      3.21.0.dev5 and dependencies) from PyPI into examples/mantle-factory-agent/project/.venv.
#   2. Prints which no-network wrapper the machine proves (macOS sandbox-exec, or Linux unshare / sudo+unshare / bubblewrap).
#   3. test_isolation.py: 11 refusal tests (fake wrappers, edited helper, LIVE off Linux). No gate is executed by these
#      except run_a6.py refusals.
#   4. test_factory_gate.py: factory_gate.run_factory('good') and ('ignores-limit') in SCRIPTED mode. A scripted builder writes
#      an attempt into a temp folder, then the pinned protected gate (ch06 run_a6.py plus acceptance suite, sha256-pinned)
#      judges it under the no-network wrapper. Expected: good = ACCEPT, ignores-limit = REJECT naming
#      test_b1_four_currencies_show_at_most_the_limit. Two LIVE tests are skipped on Linux by design. No LIVE build is run.
# READS: this checkout only, and PyPI during step 1. No credential is read or needed. The tests use the string
#   'unit-test-placeholder' and patched commands, not a provider.
# WRITES: examples/mantle-factory-agent/project/.venv and temporary folders under $TMPDIR. Nothing else.
# NEEDS: a Linux codespace created from rasa-ops/workshop-codespace-20261101 (user vscode, Python 3.12, uv, network for step 1),
#   or a Mac with sandbox-exec. Not for ENG-UK or any shared seat machine. Run from the repository root or this folder.
# NOT COVERED: any LIVE or funded run, Studio, Mantle in the Inspector.
set -eu
cd "$(dirname "$0")"
./demo setup
project/.venv/bin/python -B -c "import factory_gate; print('wrapper proven:', factory_gate._isolation().first_blocking())"
project/.venv/bin/python -B -m unittest discover -s . -p 'test_isolation.py' -v
project/.venv/bin/python -B -m unittest discover -s . -p 'test_factory_gate.py' -v
