.PHONY: check-venv setup sync rebuild cleanup stats test verify pr-ready hooks-install demo-record demo-render demo-check launch-generate

VENV_PYTHON := .venv/bin/python

check-venv:
	@test -x $(VENV_PYTHON) || (echo "Error: .venv not found. Create it with: python -m venv .venv && . .venv/bin/activate && pip install -e .[dev]" && exit 1)

setup: check-venv
	$(VENV_PYTHON) -m ytmusic_organizer.cli setup

sync: check-venv
	$(VENV_PYTHON) -m ytmusic_organizer.cli sync

rebuild: check-venv
	$(VENV_PYTHON) -m ytmusic_organizer.cli rebuild

cleanup: check-venv
	$(VENV_PYTHON) -m ytmusic_organizer.cli cleanup

stats: check-venv
	$(VENV_PYTHON) -m ytmusic_organizer.cli stats

test: check-venv
	$(VENV_PYTHON) -m unittest discover -s tests -v

verify: check-venv
	$(VENV_PYTHON) -m ruff check .
	$(VENV_PYTHON) -m ruff format --check .
	$(VENV_PYTHON) -m unittest discover -s tests -v

pr-ready: verify

hooks-install: check-venv
	$(VENV_PYTHON) -m pre_commit install --hook-type pre-commit --hook-type pre-push

demo-record:
	./scripts/demo/record.sh

demo-render:
	./scripts/demo/render.sh

demo-check:
	@tracked=$$(git ls-files '*.cast' '*.gif' '*.mp4' | grep -v '^docs/assets/demo\.gif$$' || true); \
	if [ -n "$$tracked" ]; then \
		echo "Tracked media files are not allowed:"; \
		echo "$$tracked"; \
		exit 1; \
	fi

launch-generate:
	./scripts/launch/generate.sh
