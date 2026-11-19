.DEFAULT_GOAL := help
.PHONY: help run text test
help:
	@echo "Select this project with the workspace helper. Download the pinned public Jack Henry archive in examples/jack-henry-silverlake first. run uses Rime Prism; text is a developer check, not voice acceptance."
run:
	LITELLM_LOCAL_MODEL_COST_MAP=True RASA_TELEMETRY_ENABLED=false uv run --locked python run_demo.py --port 5005
text:
	LITELLM_LOCAL_MODEL_COST_MAP=True RASA_TELEMETRY_ENABLED=false uv run --locked python run_demo.py --port 5005 --text-api
test:
	LITELLM_LOCAL_MODEL_COST_MAP=True RASA_TELEMETRY_ENABLED=false uv run --locked python -B -m unittest discover -s tests -v
