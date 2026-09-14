from pathlib import Path

root = Path(SPECPATH)
a = Analysis(
    [str(root/'main.py')], pathex=[str(root)], binaries=[],
    datas=[(str(root/name), name) for name in ('data','assets','third-party-licenses')]
          + [(str(root/name),'.') for name in ('THIRD_PARTY.md','LICENSE')],
    hiddenimports=[], hookspath=[], hooksconfig={}, runtime_hooks=[],
    excludes=[], noarchive=False, optimize=0,
)
# Qt 6.11 imports the Windows system ICU API (unversioned symbols).
# Conda's identically named ICU exports version-suffixed symbols and must not
# shadow Windows/System32/icuuc.dll inside a frozen distribution.
a.binaries = [entry for entry in a.binaries
              if Path(entry[0]).name.lower() not in {'icuuc.dll','icudt78.dll'}]
pyz = PYZ(a.pure)
exe = EXE(pyz, a.scripts, [], exclude_binaries=True, name='FlyBrainStudio',
          debug=False, strip=False, upx=False, console=False,
          icon=str(root/'assets/icon.ico'))
coll = COLLECT(exe, a.binaries, a.datas, strip=False, upx=False, name='FlyBrainStudio')
