.DEFAULT_GOAL := help
.PHONY: help setup doctor run test contract-test validate models models-check

help:
	@echo "Premier fictional banking example"
	@echo "  make help          List these commands (the default)."
	@echo "  make setup         Install or reuse the locked environment."
	@echo "  make doctor        Check setting names, vendor input and locked runtime."
	@echo "  make run           Check prerequisites, then start the Inspector."
	@echo "  make test          Run offline example controls."
	@echo "  make validate      Validate the Rasa configuration."
	@echo "  make models-check  Check generated models against the tested archive."

setup:
	python3 setup_environment.py

doctor:
	uv run --locked python -m premier_demo.startup doctor

run: doctor
	uv run --locked python run_demo.py --port 5005

test:
	uv run --locked --group models python -m unittest discover -s tests -v

contract-test:
	uv run --locked python -m unittest tests.test_contract -v

validate:
	uv run --locked python -c "from rasa.mantle.validation import validate_project; validate_project('.')"

models:
	uv run --locked --group models python make_models.py

models-check:
	uv run --locked --group models python make_models.py --check
