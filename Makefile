.PHONY: dist

clean:
	rm -rf dist

dist2:
	pyinstaller "Rogue Basement.spec"

dist: clean dist2

app: dist
	rm -rf "dist/Rogue Basement"
	mkdir -p "dist/Rogue Basement"
	cp -r "dist/Rogue Basement.app" "dist/Rogue Basement/"
	cp Manual.txt "dist/Rogue Basement/Manual.txt"
	cd dist && zip -vr "Rogue Basement - Mac.zip" "Rogue Basement/" -x "*.DS_Store"
