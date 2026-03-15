.PHONY: init bootstrap weekly-sync full-reset preview test

init:
	python -m ytmusic_organizer.cli init --workspace .ytmo

bootstrap:
	python -m ytmusic_organizer.cli bootstrap --workspace .ytmo

weekly-sync:
	python -m ytmusic_organizer.cli weekly-sync --workspace .ytmo

full-reset:
	python -m ytmusic_organizer.cli full-reset --workspace .ytmo

preview:
	python -m ytmusic_organizer.cli preview --workspace .ytmo

test:
	python -m unittest discover -s tests -v
