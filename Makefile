PYTHON ?= python3
VENV ?= .venv
VENV_PYTHON := $(VENV)/bin/python

$(VENV_PYTHON):
	$(PYTHON) -m venv $(VENV)
	$(VENV_PYTHON) -m pip install --upgrade pip
	$(VENV_PYTHON) -m pip install -r requirements.txt

.PHONY: install
install: $(VENV_PYTHON)

.PHONY: test
test: $(VENV_PYTHON)
	$(VENV_PYTHON) -m unittest discover -s tests -p 'test_*.py'

.PHONY: sync-core
sync-core: $(VENV_PYTHON)
	$(VENV_PYTHON) scripts/nflverse_pipeline.py sync --datasets players schedules teams draft_picks combine

.PHONY: sync-stage-slice
sync-stage-slice: $(VENV_PYTHON)
	$(VENV_PYTHON) scripts/nflverse_pipeline.py sync --datasets players schedules teams draft_picks combine
	$(VENV_PYTHON) scripts/nflverse_pipeline.py sync --datasets rosters --seasons 2021 2022 2023 2024 2025

.PHONY: sample-ingest
sample-ingest: $(VENV_PYTHON)
	$(VENV_PYTHON) scripts/nflverse_pipeline.py sync --datasets players schedules teams

.PHONY: build-db
build-db: $(VENV_PYTHON)
	$(VENV_PYTHON) scripts/nflverse_pipeline.py build-db

.PHONY: build-stage
build-stage: $(VENV_PYTHON)
	$(VENV_PYTHON) scripts/nflverse_pipeline.py build-stage --start-season 2021 --end-season 2025

.PHONY: validate-stage
validate-stage: $(VENV_PYTHON)
	$(VENV_PYTHON) scripts/nflverse_pipeline.py validate-stage --start-season 2021 --end-season 2025

.PHONY: run-app
run-app: $(VENV_PYTHON)
	$(VENV_PYTHON) -m flask --app webapp.app run --host 127.0.0.1 --port 5000
