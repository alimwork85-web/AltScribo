# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_data_files, collect_dynamic_libs

datas = [('AltScribo.ico', '.')]
binaries = []
hiddenimports = ['altscribo.app', 'altscribo.config', 'altscribo.recorder', 'altscribo.transcriber', 'altscribo.injector', 'altscribo.menu', 'altscribo.punctuation', 'altscribo.startup', 'altscribo.i18n','speech_recognition', 'sounddevice', 'pyperclip', 'pystray', 'keyboard']

# التعرف المحلي اختياري: يُضمَّن فقط إن كانت faster-whisper مثبّتة في بيئة البناء
try:
    import faster_whisper  # noqa: F401
    datas += collect_data_files('faster_whisper')
    binaries += collect_dynamic_libs('ctranslate2')
    hiddenimports += ['faster_whisper', 'ctranslate2', 'tokenizers', 'onnxruntime', 'huggingface_hub']
except ImportError:
    pass


# ملفات speech_recognition غير المستخدمة: نموذج pocketsphinx وأدوات flac لغير Windows
# (يبقى flac-win32.exe لأن محرك Google يحتاجه)
UNUSED_DATA = ('pocketsphinx-data', 'flac-linux', 'flac-mac')


a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
a.datas = [d for d in a.datas if not any(u in d[0] for u in UNUSED_DATA)]
a.binaries = [b for b in a.binaries if not any(u in b[0] for u in UNUSED_DATA)]
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='AltScribo',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=['AltScribo.ico'],
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='AltScribo',
)
