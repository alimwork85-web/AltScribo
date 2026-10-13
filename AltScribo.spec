# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_data_files, collect_dynamic_libs

datas = [('AltScribo.ico', '.')]
binaries = []
hiddenimports = ['altscribo.app', 'altscribo.config', 'altscribo.recorder', 'altscribo.transcriber', 'altscribo.injector', 'altscribo.menu', 'altscribo.punctuation', 'altscribo.startup', 'speech_recognition', 'sounddevice', 'scipy.io.wavfile', 'pyperclip', 'pystray', 'keyboard']

# التعرف المحلي اختياري: يُضمَّن فقط إن كانت faster-whisper مثبّتة في بيئة البناء
try:
    import faster_whisper  # noqa: F401
    datas += collect_data_files('faster_whisper')
    binaries += collect_dynamic_libs('ctranslate2')
    hiddenimports += ['faster_whisper', 'ctranslate2', 'tokenizers', 'onnxruntime', 'huggingface_hub']
except ImportError:
    pass


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
