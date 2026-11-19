.DEFAULT_GOAL := help
.PHONY: help test inspect
help:
	@echo "Use the repository workspace helper with this selected locked project; test is offline, inspect calls approved providers."
test:
	PYTHONDONTWRITEBYTECODE=1 uv run --locked python -B -m unittest discover -s tests -v
inspect:
	uv run --locked rasa inspect
