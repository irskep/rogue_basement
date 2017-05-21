# -*- mode: python -*-

block_cipher = None


a = Analysis(['run.py'],
             pathex=['/Users/steve/dev/ld38'],
             binaries=[],
             datas=[
               #('/Users/steve/env/ld38/lib/python3.5/site-packages/bearlibterminal/libBearLibTerminal.dylib', '.'),
               #('/usr/local/lib/libavbin.10.dylib', '.'),
               #('/usr/local/lib/libavbin.5.dylib', '.'),
               #('/usr/local/lib/libavbin.dylib', '.'),
               ('/Users/Steve/AppData/Local/Programs/Python/Python35/Lib/site-packages/bearlibterminal/BearLibTerminal.dll', '.'),
               ('/Windows/System32/avbin64.dll', '.'),
               ('data', 'data'),
               ('assets', 'assets'),
             ],
             hiddenimports=['future'],
             hookspath=[],
             runtime_hooks=[],
             excludes=[],
             win_no_prefer_redirects=False,
             win_private_assemblies=False,
             cipher=block_cipher)
pyz = PYZ(a.pure, a.zipped_data,
             cipher=block_cipher)
exe = EXE(pyz,
          a.scripts,
          exclude_binaries=True,
          name='Rogue Basement',
          debug=False,
          strip=False,
          upx=True,
          console=False )
coll = COLLECT(exe,
               a.binaries,
               a.zipfiles,
               a.datas,
               strip=False,
               upx=True,
               name='Rogue Basement')
app = BUNDLE(coll,
             name='Rogue Basement.app',
             icon=None,
             bundle_identifier='com.steveasleep.RogueBasement')
