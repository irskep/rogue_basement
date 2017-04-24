.PHONY: dist

clean:
	rm -rf dist

dist2:
	pyinstaller "Rogue Basement.spec"

dist: clean dist2
