# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['mic_renamer\\__main__.py'],
    pathex=[],
    binaries=[],
    datas=[('mic_renamer/config/defaults.yaml', 'mic_renamer/config'),
           ('mic_renamer/config/tags.json', 'mic_renamer/config'),
           ('mic_renamer/favicon.png', 'mic_renamer'),
           ('mic_renamer/resources/icons/*.svg',
            'mic_renamer/resources/icons')],
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='mic-renamer',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
