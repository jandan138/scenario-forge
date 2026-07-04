.PHONY: test lint type package-smoke phase10x-smoke diff-check check

PYTHON ?= python
CHECK_PYTHON ?= $(PYTHON)
CHECK_PYTHON_PATH ?= $(shell command -v $(CHECK_PYTHON))
SMOKE_OUT ?= /tmp/scenario-forge-smoke-package
SMOKE_SUITE_OUT ?= /tmp/scenario-forge-smoke-suite
PHASE10X_SUITE_OUT ?= /tmp/scenario-forge-phase10x-suite

test:
	$(CHECK_PYTHON) -m pytest -q

lint:
	$(CHECK_PYTHON) -m ruff check src tests scripts

type:
	$(CHECK_PYTHON) -m mypy src

package-smoke:
	rm -rf "$(SMOKE_OUT)"
	PYTHONPATH=src $(CHECK_PYTHON) -m scenario_forge.cli package scaffold --out "$(SMOKE_OUT)"
	PYTHONPATH=src $(CHECK_PYTHON) -m scenario_forge.cli workflow compose --package "$(SMOKE_OUT)" --family pick_place --binding object=object_001 --binding target_zone=target_zone
	PYTHONPATH=src $(CHECK_PYTHON) -m scenario_forge.cli layout plan --package "$(SMOKE_OUT)" --difficulty easy
	PYTHONPATH=src $(CHECK_PYTHON) -m scenario_forge.cli task compile --package "$(SMOKE_OUT)" --family pick_place
	PYTHONPATH=src $(CHECK_PYTHON) -m scenario_forge.cli scene compile --instances "$(SMOKE_OUT)/scene/instances.yaml" --asset-lock "$(SMOKE_OUT)/locks/asset_lock.yaml" --out "$(SMOKE_OUT)/scene/main.usda"
	PYTHONPATH=src $(CHECK_PYTHON) -m scenario_forge.cli export ebench --package "$(SMOKE_OUT)"
	PYTHONPATH=src $(CHECK_PYTHON) -m scenario_forge.cli package check "$(SMOKE_OUT)"
	rm -rf "$(SMOKE_SUITE_OUT)"
	PYTHONPATH=src $(CHECK_PYTHON) -m scenario_forge.cli suite generate --spec examples/suite_spec_smoke.yaml --out "$(SMOKE_SUITE_OUT)"
	PYTHONPATH=src $(CHECK_PYTHON) -m scenario_forge.cli suite quality --suite "$(SMOKE_SUITE_OUT)"

phase10x-smoke:
	rm -rf "$(PHASE10X_SUITE_OUT)"
	PYTHONPATH=src $(CHECK_PYTHON) -m scenario_forge.cli suite generate --spec examples/suite_spec_phase10x_golden.yaml --out "$(PHASE10X_SUITE_OUT)"
	PYTHONPATH=src $(CHECK_PYTHON) -m scenario_forge.cli suite phase10x --suite "$(PHASE10X_SUITE_OUT)" --eos-python "$(CHECK_PYTHON_PATH)" --external-evidence examples/phase10x_external_evidence.yaml --runtime-smoke examples/phase10x_runtime_smoke.yaml --rc-min-packages 10 --rc-max-packages 20 --strict

diff-check:
	git diff --check

check: test lint package-smoke phase10x-smoke diff-check
