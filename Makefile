.PHONY: dist

clean:
	rm -rf dist

app-mac: clean
	pyinstaller "pyinstaller_spec/mac.spec"

mac: app-mac
	rm -rf "dist/Rogue Basement"
	mkdir -p "dist/Rogue Basement"
	cp -r "dist/Rogue Basement.app" "dist/Rogue Basement/"
	cp Manual.txt "dist/Rogue Basement/Manual.txt"
	cd dist && zip -vr "Rogue Basement - Mac.zip" "Rogue Basement/" -x "*.DS_Store"

# The Windows instructions should be similar, but I did it all in an
# interactive console, so I don't remember the exact steps.
#
# The other thing about Windows is I could never get single-file mode to work,
# so the distribution has data files splatted all over the directory.
