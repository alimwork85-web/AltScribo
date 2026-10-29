import ctypes
import os
import sys
import threading
import winsound

import keyboard
import pystray
from PIL import Image, ImageDraw
from pystray._util import win32

from . import __version__, config, i18n, startup
from .config import log
from .i18n import t
from .injector import paste_text
from .menu import TrayMenu
from .recorder import Recorder
from .transcriber import EngineError, NetworkError, NoSpeech, Transcriber, whisper_available

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
        i18n.set_language(self.settings["ui_language"])
        self.recorder = Recorder(self.settings["sample_rate"])
        self.transcriber = Transcriber(self.settings, self.notify)
        self.has_whisper = whisper_available()
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
                    self.notify(t("mic_failed"))
                    return
                play_sound("start")
                self.icon.icon = self.recording_icon
                self.icon.title = t("tip_recording")
                log.info("بدأ التسجيل")
            else:
                frames = self.recorder.stop()
                play_sound("stop")
                self.icon.icon = self.base_icon
                self.icon.title = t("tip_idle")
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
            self.notify(t("network_failed"))
            return
        except EngineError as e:
            log.error("%s", e)
            self.notify(t("whisper_failed"))
            return
        except Exception:
            log.exception("خطأ أثناء معالجة الصوت")
            self.notify(t("processing_failed"))
            return
        log.info("تم التعرف ولصق نص من %s حرفًا", len(text))
        try:
            paste_text(text)
        except Exception:
            log.exception("فشل اللصق")
            self.notify(t("paste_failed"))

    def open_path(self, path):
        try:
            os.startfile(path)
        except OSError as e:
            log.error("تعذّر فتح %s: %s", path, e)

    def set_engine(self, name):
        if self.settings["engine"] == name:
            return
        self.settings["engine"] = name
        config.save_settings({"engine": name})
        log.info("محرك التعرف: %s", name)
        self.transcriber.preload()

    def toggle_setting(self, key):
        self.settings[key] = not self.settings[key]
        config.save_settings({key: self.settings[key]})

    def toggle_startup(self):
        try:
            if startup.is_enabled():
                startup.disable()
                self.notify(t("startup_off"))
            else:
                startup.enable()
                self.notify(t("startup_on"))
        except Exception as e:
            log.error("فشل تعديل التشغيل التلقائي: %s", e)
            self.notify(t("startup_failed"))

    def toggle_ui_language(self):
        lang = "en" if i18n.current() == "ar" else "ar"
        self.settings["ui_language"] = lang
        config.save_settings({"ui_language": lang})
        i18n.set_language(lang)
        self.icon.title = t("tip_recording") if self.recorder.is_recording else t("tip_idle")
        log.info("لغة الواجهة: %s", lang)

    def exit(self):
        if self.recorder.is_recording:
            self.recorder.stop()
        self.icon.stop()
        os._exit(0)

    def menu_items(self):
        hotkey = self.settings["hotkey"]
        toggle = t("stop_recording") if self.recorder.is_recording else t("start_recording")
        return [
            (f"AltScribo {__version__}  ({hotkey})", None, False),
            None,
            (toggle, self.toggle_recording, True),
            None,
            (t("engine_google"), lambda: self.set_engine("google"), True,
             self.settings["engine"] == "google"),
            (t("engine_whisper") if self.has_whisper else t("engine_whisper_missing"),
             lambda: self.set_engine("whisper"), self.has_whisper,
             self.settings["engine"] == "whisper"),
            (t("auto_punctuation"), lambda: self.toggle_setting("auto_punctuation"), True,
             self.settings["auto_punctuation"]),
            (t("spoken_punctuation"), lambda: self.toggle_setting("spoken_punctuation"), True,
             self.settings["spoken_punctuation"]),
            (t("startup"), self.toggle_startup, True, startup.is_enabled()),
            None,
            (t("switch_language"), self.toggle_ui_language, True),
            (t("open_settings"), lambda: self.open_path(config.SETTINGS_PATH), True),
            (t("open_log"), lambda: self.open_path(config.LOG_PATH), True),
            None,
            (t("exit"), self.exit, True),
        ]

    def run(self):
        hotkey = self.settings["hotkey"]
        self.menu = TrayMenu()
        self.icon = TrayIcon(
            "AltScribo", self.base_icon, t("tip_idle"),
            on_right_click=lambda: self.menu.show(self.menu_items(), i18n.is_rtl()),
        )

        try:
            keyboard.add_hotkey(hotkey, self.toggle_recording, suppress=True)
            log.info("تم تفعيل الاختصار العام (%s)", hotkey)
        except Exception as e:
            log.error("فشل تسجيل الاختصار: %s", e)

        if self.settings["engine"] == "whisper" and not self.has_whisper:
            log.warning("Whisper غير مثبّت، يُستخدم Google")
            self.settings["engine"] = "google"
        self.transcriber.preload()
        self.icon.run()


class TrayIcon(pystray.Icon):
    """ أيقونة الشريط مع قائمة مخصصة بدل قائمة Windows الأصلية """

    def __init__(self, *args, on_right_click, **kwargs):
        super().__init__(*args, **kwargs)
        self._on_right_click = on_right_click

    def _on_notify(self, wparam, lparam):
        if lparam == win32.WM_RBUTTONUP:
            self._on_right_click()
        else:
            super()._on_notify(wparam, lparam)


def run():
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(2)
    except Exception:
        pass
    config.setup_logging()
    if already_running():
        log.info("الأداة تعمل بالفعل، سيتم الخروج")
        sys.exit(0)
    App().run()
