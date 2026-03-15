.PHONY: setup sync reset cleanup preview test

setup:
	python -m ytmusic_organizer.cli setup --workspace .ytmo

sync:
	python -m ytmusic_organizer.cli sync --workspace .ytmo

reset:
	python -m ytmusic_organizer.cli reset --workspace .ytmo

cleanup:
	python -m ytmusic_organizer.cli cleanup --workspace .ytmo

preview:
	python -m ytmusic_organizer.cli preview --workspace .ytmo

test:
	python -m unittest discover -s tests -v
