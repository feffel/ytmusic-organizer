.PHONY: check-venv setup sync reset cleanup preview test

VENV_PYTHON := .venv/bin/python

check-venv:
	@test -x $(VENV_PYTHON) || (echo "Error: .venv not found. Create it with: python -m venv .venv && . .venv/bin/activate && pip install -e ." && exit 1)

setup: check-venv
	$(VENV_PYTHON) -m ytmusic_organizer.cli setup

sync: check-venv
	$(VENV_PYTHON) -m ytmusic_organizer.cli sync

reset: check-venv
	$(VENV_PYTHON) -m ytmusic_organizer.cli reset

cleanup: check-venv
	$(VENV_PYTHON) -m ytmusic_organizer.cli cleanup

preview: check-venv
	$(VENV_PYTHON) -m ytmusic_organizer.cli preview

test: check-venv
	$(VENV_PYTHON) -m unittest discover -s tests -v
