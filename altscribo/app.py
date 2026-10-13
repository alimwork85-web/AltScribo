import ctypes
import os
import sys
import threading
import winsound

import keyboard
import pystray
from PIL import Image, ImageDraw

from . import __version__, config
from .config import log
from .injector import paste_text
from .recorder import Recorder
from .transcriber import NetworkError, NoSpeech, Transcriber

ERROR_ALREADY_EXISTS = 183
_mutex = None


def already_running():
    """ يمنع تشغيل نسختين معًا عبر mutex مسمّى """
    global _mutex
    _mutex = ctypes.windll.kernel32.CreateMutexW(None, False, "AltScribo_SingleInstance")
    return ctypes.windll.kernel32.GetLastError() == ERROR_ALREADY_EXISTS


def get_default_icon():
    image = Image.new("RGB", (64, 64), color=(0, 120, 212))
    ImageDraw.Draw(image).rectangle([16, 16, 48, 48], fill=(255, 255, 255))
    return image


def load_base_icon():
    try:
        return Image.open(config.ICON_PATH).convert("RGBA")
    except Exception:
        return get_default_icon().convert("RGBA")


def make_recording_icon(base):
    """ الأيقونة الأصلية مع نقطة حمراء """
    icon = base.copy()
    w, h = icon.size
    r = max(w // 4, 4)
    ImageDraw.Draw(icon).ellipse([w - 2 * r, h - 2 * r, w - 1, h - 1], fill=(220, 30, 30, 255))
    return icon


def play_sound(kind):
    """ نغمة مرتفعة عند البدء ومنخفضة عند الإيقاف """
    try:
        winsound.Beep(1200 if kind == "start" else 600, 150)
    except Exception:
        pass


class App:
    def __init__(self):
        self.settings = config.load_settings()
        self.recorder = Recorder(self.settings["sample_rate"])
        self.transcriber = Transcriber(
            self.settings["sample_rate"],
            self.settings["language"],
            self.settings["timeout_seconds"],
            float(self.settings["max_gain"]),
        )
        self.base_icon = load_base_icon()
        self.recording_icon = make_recording_icon(self.base_icon)
        self.icon = None

    def notify(self, message):
        log.info(message)
        try:
            if self.icon is not None:
                self.icon.notify(message, "AltScribo")
        except Exception:
            pass

    def toggle_recording(self, *_):
        with self.recorder.lock:
            if not self.recorder.is_recording:
                try:
                    self.recorder.start()
                except Exception as e:
                    log.error("فشل فتح الميكروفون: %s", e)
                    self.notify("تعذّر فتح الميكروفون")
                    return
                play_sound("start")
                self.icon.icon = self.recording_icon
                self.icon.title = "AltScribo - جارٍ التسجيل…"
                log.info("بدأ التسجيل")
            else:
                frames = self.recorder.stop()
                play_sound("stop")
                self.icon.icon = self.base_icon
                self.icon.title = "AltScribo - أداة الإملاء الصوتي"
                log.info("توقف التسجيل، جاري التحويل")
                threading.Thread(target=self.process, args=(frames,), daemon=True).start()

    def process(self, frames):
        try:
            text = self.transcriber.transcribe(frames)
        except NoSpeech as e:
            self.notify(str(e))
            return
        except NetworkError as e:
            log.error("خطأ اتصال: %s", e)
            self.notify("تعذّر الاتصال بخدمة التعرف على الكلام")
            return
        except Exception:
            log.exception("خطأ أثناء معالجة الصوت")
            self.notify("حدث خطأ أثناء معالجة الصوت")
            return
        log.info("تم التعرف ولصق نص من %s حرفًا", len(text))
        try:
            paste_text(text)
        except Exception:
            log.exception("فشل اللصق")
            self.notify("فشل لصق النص")

    def open_path(self, path):
        try:
            os.startfile(path)
        except OSError as e:
            log.error("تعذّر فتح %s: %s", path, e)

    def exit(self, icon, item):
        if self.recorder.is_recording:
            self.recorder.stop()
        icon.stop()
        os._exit(0)

    def run(self):
        hotkey = self.settings["hotkey"]
        menu = pystray.Menu(
            pystray.MenuItem(f"AltScribo {__version__} ({hotkey})", lambda: None, enabled=False),
            pystray.MenuItem("تشغيل / إيقاف التسجيل", self.toggle_recording),
            pystray.MenuItem("فتح الإعدادات", lambda icon, item: self.open_path(config.SETTINGS_PATH)),
            pystray.MenuItem("فتح السجلّ", lambda icon, item: self.open_path(config.LOG_PATH)),
            pystray.MenuItem("خروج (Exit)", self.exit),
        )
        self.icon = pystray.Icon("AltScribo", self.base_icon, "AltScribo - أداة الإملاء الصوتي", menu)

        try:
            keyboard.add_hotkey(hotkey, self.toggle_recording, suppress=True)
            log.info("تم تفعيل الاختصار العام (%s)", hotkey)
        except Exception as e:
            log.error("فشل تسجيل الاختصار: %s", e)

        self.icon.run()


def run():
    config.setup_logging()
    if already_running():
        log.info("الأداة تعمل بالفعل، سيتم الخروج")
        sys.exit(0)
    App().run()
