import json
import logging
import os
import sys
from logging.handlers import RotatingFileHandler

APP_NAME = "AltScribo"

DEFAULTS = {
    "hotkey": "alt+s",
    "language": "ar-SA",
    "timeout_seconds": 15,
    "max_gain": 4.0,
    "sample_rate": 16000,
}


def get_resource_path(relative_path):
    if hasattr(sys, "_MEIPASS"):
        return os.path.join(sys._MEIPASS, relative_path)
    base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base, relative_path)


def get_data_dir():
    base = os.environ.get("APPDATA") or os.path.expanduser("~")
    path = os.path.join(base, APP_NAME)
    os.makedirs(path, exist_ok=True)
    return path


DATA_DIR = get_data_dir()
SETTINGS_PATH = os.path.join(DATA_DIR, "settings.json")
LOG_PATH = os.path.join(DATA_DIR, "altscribo.log")
ICON_PATH = get_resource_path("AltScribo.ico")

log = logging.getLogger(APP_NAME)


def setup_logging():
    log.setLevel(logging.INFO)
    fmt = logging.Formatter("%(asctime)s %(levelname)s %(message)s")
    file_handler = RotatingFileHandler(LOG_PATH, maxBytes=1_000_000, backupCount=1, encoding="utf-8")
    file_handler.setFormatter(fmt)
    log.addHandler(file_handler)
    if sys.stderr is not None:
        console = logging.StreamHandler()
        console.setFormatter(fmt)
        log.addHandler(console)


def load_settings():
    """ يحمّل الإعدادات؛ ينشئ الملف إن لم يوجد، ولا يكتب فوقه إن كان تالفًا """
    settings = dict(DEFAULTS)
    if not os.path.exists(SETTINGS_PATH):
        try:
            with open(SETTINGS_PATH, "w", encoding="utf-8") as f:
                json.dump(DEFAULTS, f, indent=2, ensure_ascii=False)
        except OSError as e:
            log.warning("تعذّر إنشاء ملف الإعدادات: %s", e)
        return settings
    try:
        with open(SETTINGS_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        for key, default in DEFAULTS.items():
            value = data.get(key, default)
            ok = isinstance(value, (int, float)) if isinstance(default, (int, float)) else isinstance(value, type(default))
            if ok and not isinstance(value, bool):
                settings[key] = value
            elif key in data:
                log.warning("قيمة غير صالحة للإعداد %s، تُستخدم القيمة الافتراضية", key)
    except (OSError, ValueError, AttributeError) as e:
        log.warning("ملف الإعدادات تالف، تُستخدم القيم الافتراضية: %s", e)
    return settings
