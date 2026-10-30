import ctypes
import time

import keyboard
import pyperclip


def copy_text(text):
    """ ينسخ النص إلى الحافظة بلا لصق (لا يعتمد على النافذة النشطة) """
    pyperclip.copy(text)


def paste_text(text):
    """ لصق النص عبر الحافظة ثم إرجاع الحافظة القديمة إن كانت نصًا """
    try:
        old_clipboard = pyperclip.paste()
    except Exception:
        old_clipboard = ""

    pyperclip.copy(text)
    time.sleep(0.05)
    # انتظار تحرير Alt حتى لا يتحول اللصق إلى Ctrl+Alt+V
    for _ in range(20):
        if not (ctypes.windll.user32.GetAsyncKeyState(0x12) & 0x8000):
            break
        time.sleep(0.05)
    keyboard.send("ctrl+v")

    if old_clipboard:
        time.sleep(0.4)
        try:
            pyperclip.copy(old_clipboard)
        except Exception:
            pass
