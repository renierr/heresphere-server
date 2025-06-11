# -*- mode: python ; coding: utf-8 -*-

import os

def collect_static_files():
    result = []
    exclude_dirs = ['videos', 'library']

    result.append(('templates', 'templates'))

    for root, dirs, files in os.walk('static'):
        rel_path = root[len('static')+1:] if len(root) > len('static') else ''

        if any(rel_path == exclude or
               rel_path.startswith(exclude + os.sep) or
               rel_path.startswith(exclude + '/') or
               rel_path.startswith(exclude + '\\')
               for exclude in exclude_dirs):
            continue

        for file in files:
            source_path = os.path.join(root, file)
            target_path = os.path.join(root)
            result.append((source_path, target_path))

    return result
datas = collect_static_files()
print("Collected static files:", datas)

a = Analysis(
    ['main.py'],
    pathex=['.', './src'],
    binaries=[],
    datas=datas,
    hiddenimports=['waitress'],
    hookspath=['.'],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure, a.zipped_data)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='hserver',
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
    icon='./static/favicon.ico',
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='hserver',
)
