#!/usr/bin/env bash
# Draft by rasa-ops, Nov 1, 2026. Not yet run in a codespace.
# Installs Mantle from this repo's own pin (RASA_PRO_VERSION) in its own virtual environment.
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
PIN="$(tr -d '[:space:]' < "$ROOT/RASA_PRO_VERSION")"
echo "Installing rasa-pro==$PIN"
python -m venv "$HOME/.venv-mantle"
"$HOME/.venv-mantle/bin/pip" install --quiet "rasa-pro==$PIN"
"$HOME/.venv-mantle/bin/rasa" --version
echo "Mantle is ready. Activate it with: source ~/.venv-mantle/bin/activate"
echo "Start Studio with: bash $ROOT/.devcontainer/software-factories-workshop/start-studio.sh"
