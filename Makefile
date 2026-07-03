.PHONY: test lint type package-smoke diff-check check

PYTHON ?= python
CHECK_PYTHON ?= $(PYTHON)
SMOKE_OUT ?= /tmp/scenario-forge-smoke-package
SMOKE_SUITE_OUT ?= /tmp/scenario-forge-smoke-suite

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

diff-check:
	git diff --check

check: test lint package-smoke diff-check
