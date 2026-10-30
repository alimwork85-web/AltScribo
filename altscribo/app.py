import ctypes
import ctypes.wintypes
import json
import os
import sys
import threading
import time
import urllib.request
import winsound

import keyboard
import pyperclip
import pystray
from PIL import Image, ImageDraw
from pystray._util import win32

from . import __version__, config, history_view, i18n, startup
from .config import log
from .i18n import t
from .injector import paste_text
from .menu import TrayMenu
from .overlay import Overlay
from .recorder import Recorder, input_devices
from .transcriber import EngineError, NetworkError, NoSpeech, Transcriber, whisper_available

ERROR_ALREADY_EXISTS = 183
_mutex = None

RELEASES_URL = "https://github.com/alimwork85-web/AltScribo/releases"
LATEST_RELEASE_API = "https://api.github.com/repos/alimwork85-web/AltScribo/releases/latest"


def version_tuple(text):
    """ يحوّل "v1.3.2" إلى (1, 3, 2) للمقارنة الرقمية """
    parts = []
    for piece in str(text).strip().lstrip("vV").split("."):
        digits = "".join(ch for ch in piece if ch.isdigit())
        parts.append(int(digits) if digits else 0)
    return tuple(parts)


def check_updates(notify):
    """ يفحص آخر إصدار على GitHub ويُشعر فقط؛ لا تنزيل ولا تثبيت """
    try:
        request = urllib.request.Request(LATEST_RELEASE_API, headers={"User-Agent": "AltScribo"})
        with urllib.request.urlopen(request, timeout=5) as response:
            data = json.load(response)
        latest = str(data.get("tag_name", ""))
        if version_tuple(latest) > version_tuple(__version__):
            log.info("يتوفر إصدار أحدث: %s (الحالي %s)", latest, __version__)
            notify(t("update_available", version=latest.lstrip("vV")))
    except Exception as e:
        log.info("تعذّر فحص التحديثات: %s", e)


MOD_ALT = 0x1
MOD_CONTROL = 0x2
MOD_SHIFT = 0x4
MOD_WIN = 0x8
MOD_NOREPEAT = 0x4000
WM_HOTKEY = 0x0312
HOTKEY_ID = 1


def parse_hotkey(text):
    """ يحوّل "alt+s" إلى (المعدِّلات، رمز المفتاح)، أو None إن لم تُفهم الصيغة """
    mods = MOD_NOREPEAT
    vk = None
    for part in str(text).lower().replace(" ", "").split("+"):
        if part == "alt":
            mods |= MOD_ALT
        elif part in ("ctrl", "control"):
            mods |= MOD_CONTROL
        elif part == "shift":
            mods |= MOD_SHIFT
        elif part == "win":
            mods |= MOD_WIN
        elif len(part) == 1 and part.isascii() and part.isalnum():
            if vk:
                return None
            vk = ord(part.upper())
        elif len(part) in (2, 3) and part[0] == "f" and part[1:].isdigit() and 1 <= int(part[1:]) <= 12:
            if vk:
                return None
            vk = 0x70 + int(part[1:]) - 1
        else:
            return None
    return None if vk is None else (mods, vk)


HISTORY_LIMIT = 20


def load_history():
    """ يقرأ سجل النصوص: [] إن لم يوجد، وNone إن كان الملف تالفًا (لا يُكتب فوقه) """
    if not os.path.exists(config.HISTORY_PATH):
        return []
    try:
        with open(config.HISTORY_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, ValueError) as e:
        log.warning("ملف سجل النصوص تالف، لن يُكتب فوقه: %s", e)
        return None
    if not isinstance(data, list):
        log.warning("ملف سجل النصوص تالف، لن يُكتب فوقه")
        return None
    return [item for item in data if isinstance(item, dict) and isinstance(item.get("text"), str)]


def add_history(text):
    """ يضيف النص مع وقته ويحفظ آخر 20 عنصرًا كتابةً ذرية """
    items = load_history()
    if items is None:
        return
    items.append({"time": time.strftime("%Y-%m-%d %H:%M:%S"), "text": text})
    tmp = config.HISTORY_PATH + ".tmp"
    try:
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(items[-HISTORY_LIMIT:], f, indent=2, ensure_ascii=False)
        os.replace(tmp, config.HISTORY_PATH)
    except OSError as e:
        log.warning("تعذّر حفظ سجل النصوص: %s", e)


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
        self.recorder.input_device = self.settings["input_device"]
        self.recorder.silence_seconds = self.settings["auto_stop_silence_seconds"]
        self.recorder.silence_threshold = self.settings["silence_threshold"]
        self.transcriber = Transcriber(self.settings, self.notify)
        self.has_whisper = whisper_available()
        self.base_icon = load_base_icon()
        self.recording_icon = make_recording_icon(self.base_icon)
        self.icon = None
        self.menu = None
        self.overlay = None

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
                if self.overlay:
                    self.overlay.show_recording()
                if self.recorder.silence_seconds > 0:
                    threading.Thread(target=self.watch_silence, daemon=True).start()
            else:
                frames = self.recorder.stop()
                play_sound("stop")
                self.icon.icon = self.base_icon
                self.icon.title = t("tip_idle")
                log.info("توقف التسجيل، جاري التحويل")
                if self.overlay:
                    self.overlay.show_processing()
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
        else:
            log.info("تم التعرف ولصق نص من %s حرفًا", len(text))
            add_history(text)
            try:
                paste_text(text)
            except Exception:
                log.exception("فشل اللصق")
                self.notify(t("paste_failed"))
        finally:
            if self.overlay:
                self.overlay.show_done()

    def open_path(self, path):
        try:
            os.startfile(path)
        except OSError as e:
            log.error("تعذّر فتح %s: %s", path, e)

    def open_history(self):
        """ يفتح سجل النصوص في نافذة قابلة للنسخ بدل ملف JSON في محرر """
        history_view.show(load_history())

    def repaste_last(self):
        """ ينسخ آخر نص إلى الحافظة؛ اللصق يدوي لأن القائمة تسرق التركيز """
        items = load_history()
        if not items:
            self.notify(t("history_empty"))
            return
        try:
            pyperclip.copy(items[-1]["text"])
        except Exception:
            log.exception("فشل نسخ آخر نص")
            self.notify(t("paste_failed"))
            return
        log.info("نُسخ آخر نص إلى الحافظة (%s حرفًا)", len(items[-1]["text"]))
        self.notify(t("repasted"))

    def set_engine(self, name):
        if self.settings["engine"] == name:
            return
        self.settings["engine"] = name
        config.save_settings({"engine": name})
        log.info("محرك التعرف: %s", name)
        self.transcriber.preload()

    def set_input_device(self, name):
        """ يختار ميكروفون الإدخال بالاسم ويحفظه (يُمنع أثناء التسجيل) """
        if self.recorder.is_recording:
            return
        self.settings["input_device"] = name
        self.recorder.input_device = name
        config.save_settings({"input_device": name})
        log.info("ميكروفون الإدخال: %s", name or "الافتراضي")

    def microphone_menu(self):
        """ عناصر القائمة الفرعية للميكروفون، والمختار عليه علامة """
        current = self.settings["input_device"]
        busy = self.recorder.is_recording
        items = [(t("default_device"), lambda: self.set_input_device(""), not busy, current == "")]
        for name in input_devices():
            items.append((name, (lambda n: lambda: self.set_input_device(n))(name),
                          not busy, current == name))
        return items

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

    def toggle_speech_language(self):
        """ يبدّل لغة التعرف على الكلام؛ لا يمسّ لغة الواجهة """
        code = "en-US" if self.settings["language"].startswith("ar") else "ar-SA"
        self.transcriber.set_language(code)
        config.save_settings({"language": code})
        log.info("لغة التعرف على الكلام: %s", code)

    def toggle_overlay(self):
        """ تفعيل/تعطيل مؤشر التسجيل على الشاشة """
        enabled = not self.settings["show_overlay"]
        self.settings["show_overlay"] = enabled
        config.save_settings({"show_overlay": enabled})
        if enabled and self.menu is not None:
            self.overlay = self.overlay or Overlay(self.menu, self.base_icon)
        elif not enabled and self.overlay is not None:
            self.overlay.hide()
            self.overlay = None
        log.info("مؤشر التسجيل على الشاشة: %s", "مفعّل" if enabled else "معطّل")

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
        # ما يُعرض في القائمة قد يختلف عن الاختصار المسجّل (لوحة تحتاج Fn للوصول إلى F9)
        label = self.settings.get("hotkey_label") or hotkey
        toggle = t("stop_recording") if self.recorder.is_recording else t("start_recording")
        has_history = bool(load_history())
        return [
            (f"AltScribo {__version__}  ({label})", None, False),
            None,
            (toggle, self.toggle_recording, True),
            None,
            (t("repaste_last"), self.repaste_last, has_history),
            (t("open_history"), self.open_history, True),
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
            (t("push_to_talk"), lambda: self.toggle_setting("push_to_talk"), True,
             self.settings["push_to_talk"]),
            (t("show_overlay"), self.toggle_overlay, True, self.settings["show_overlay"]),
            (t("startup"), self.toggle_startup, True, startup.is_enabled()),
            (t("microphone"), self.microphone_menu(), True),
            None,
            (t("speech_language_en") if self.settings["language"].startswith("en")
             else t("speech_language_ar"), self.toggle_speech_language, True),
            (t("switch_language"), self.toggle_ui_language, True),
            (t("open_settings"), lambda: self.open_path(config.SETTINGS_PATH), True),
            (t("open_log"), lambda: self.open_path(config.LOG_PATH), True),
            (t("releases_page"), lambda: self.open_path(RELEASES_URL), True),
            None,
            (t("exit"), self.exit, True),
        ]

    def register_hotkey(self, hotkey):
        """ يشغّل الاختصار العام عبر RegisterHotKey بدل خطاف keyboard الهشّ """
        parsed = parse_hotkey(hotkey)
        if parsed is None:
            log.error("صيغة الاختصار غير مفهومة: %s", hotkey)
            self.notify(t("hotkey_invalid", hotkey=hotkey))
            return
        threading.Thread(target=self._hotkey_loop, args=parsed, daemon=True).start()

    def watch_silence(self):
        """ يوقف التسجيل بعد صمت طويل؛ يعمل خارج callback الصوت """
        limit = self.recorder.silence_seconds
        while self.recorder.is_recording:
            elapsed = self.recorder.silence_elapsed()
            if elapsed is not None and elapsed >= limit:
                log.info("صمت %.1f ثانية، إيقاف تلقائي", elapsed)
                self.toggle_recording()
                return
            time.sleep(0.2)

    def push_to_talk(self, vk):
        """ وضع اضغط مع الاستمرار: تسجيل ما دام المفتاح مضغوطًا """
        if self.recorder.is_recording:
            return
        self.toggle_recording()
        if self.recorder.is_recording:
            threading.Thread(target=self._wait_key_release, args=(vk,), daemon=True).start()

    def _wait_key_release(self, vk):
        """ يوقف التسجيل عند رفع الإصبع؛ لا يبدأ شيئًا من نفسه """
        time.sleep(0.03)
        while ctypes.windll.user32.GetAsyncKeyState(vk) & 0x8000:
            time.sleep(0.03)
        if self.recorder.is_recording:
            self.toggle_recording()

    def _hotkey_loop(self, modifiers, vk):
        """ حلقة الرسائل: RegisterHotKey وGetMessageW في الخيط نفسه """
        user32 = ctypes.windll.user32
        if not user32.RegisterHotKey(None, HOTKEY_ID, modifiers, vk):
            log.error("تعذّر تسجيل الاختصار %s: محجوز لبرنامج آخر", self.settings["hotkey"])
            self.notify(t("hotkey_taken", hotkey=self.settings["hotkey"]))
            return
        try:
            log.info("تم تفعيل الاختصار العام (%s)", self.settings["hotkey"])
            msg = ctypes.wintypes.MSG()
            while user32.GetMessageW(ctypes.byref(msg), None, 0, 0) > 0:
                if msg.message == WM_HOTKEY:
                    if self.settings["push_to_talk"]:
                        self.push_to_talk(vk)
                    else:
                        self.toggle_recording()
        finally:
            user32.UnregisterHotKey(None, HOTKEY_ID)

    def run(self):
        hotkey = self.settings["hotkey"]
        self.menu = TrayMenu()
        self.icon = TrayIcon(
            "AltScribo", self.base_icon, t("tip_idle"),
            on_right_click=lambda: self.menu.show(self.menu_items(), i18n.is_rtl()),
        )

        self.register_hotkey(hotkey)
        threading.Thread(target=check_updates, args=(self.notify,), daemon=True).start()
        if self.settings["show_overlay"]:
            self.overlay = Overlay(self.menu, self.base_icon)

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
