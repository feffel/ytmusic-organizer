.PHONY: check-venv setup sync rebuild cleanup stats test demo-record demo-render demo-check launch-generate

VENV_PYTHON := .venv/bin/python

check-venv:
	@test -x $(VENV_PYTHON) || (echo "Error: .venv not found. Create it with: python -m venv .venv && . .venv/bin/activate && pip install -e ." && exit 1)

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

demo-record:
	./scripts/demo/record.sh

demo-render:
	./scripts/demo/render.sh

demo-check:
	@tracked=$$(git ls-files '*.cast' '*.gif' '*.mp4'); \
	if [ -n "$$tracked" ]; then \
		echo "Tracked media files are not allowed:"; \
		echo "$$tracked"; \
		exit 1; \
	fi

launch-generate:
	./scripts/launch/generate.sh
