import ctypes

# كل نص يظهر للمستخدم: المفتاح ← (العربية، الإنجليزية)
STRINGS = {
    "tip_idle": ("AltScribo - أداة الإملاء الصوتي", "AltScribo - voice dictation"),
    "tip_recording": ("AltScribo - جارٍ التسجيل…", "AltScribo - recording…"),
    "start_recording": ("بدء التسجيل", "Start recording"),
    "stop_recording": ("إيقاف التسجيل", "Stop recording"),
    "engine_google": ("Google عبر الإنترنت", "Google (online)"),
    "engine_whisper": ("Whisper محلي بلا إنترنت", "Whisper (local, offline)"),
    "engine_whisper_missing": ("Whisper (غير مثبّت)", "Whisper (not installed)"),
    "auto_punctuation": ("ترقيم تلقائي", "Auto punctuation"),
    "spoken_punctuation": ("أوامر الترقيم المنطوقة", "Spoken punctuation"),
    "startup": ("التشغيل مع Windows", "Start with Windows"),
    "switch_language": ("English", "العربية"),
    "open_settings": ("فتح الإعدادات", "Open settings"),
    "open_log": ("فتح السجلّ", "Open log"),
    "exit": ("خروج", "Exit"),
    "mic_failed": ("تعذّر فتح الميكروفون", "Could not open the microphone"),
    "network_failed": ("تعذّر الاتصال بخدمة التعرف على الكلام",
                       "Could not reach the speech recognition service"),
    "whisper_failed": ("تعذّر تشغيل التعرف المحلي (Whisper)، راجع السجلّ",
                       "Local recognition (Whisper) failed, see the log"),
    "processing_failed": ("حدث خطأ أثناء معالجة الصوت", "Something went wrong while processing audio"),
    "paste_failed": ("فشل لصق النص", "Could not paste the text"),
    "hotkey_invalid": ("صيغة الاختصار غير مفهومة: {hotkey}", "Invalid shortcut: {hotkey}"),
    "hotkey_taken": ("الاختصار {hotkey} محجوز لبرنامج آخر",
                     "The shortcut {hotkey} is used by another app"),
    "repaste_last": ("أعد لصق آخر نص", "Paste last text"),
    "open_history": ("فتح سجل النصوص", "Open text history"),
    "history_empty": ("سجل النصوص فارغ", "Text history is empty"),
    "microphone": ("الميكروفون", "Microphone"),
    "default_device": ("الافتراضي", "Default"),
    "push_to_talk": ("اضغط مع الاستمرار", "Hold to talk"),
    "whisper_fallback": ("انقطع الإنترنت، استُخدم Whisper المحلي",
                         "No internet, used local Whisper"),
    "startup_off": ("لن تعمل الأداة تلقائيًا مع Windows", "AltScribo will no longer start with Windows"),
    "startup_on": ("ستعمل الأداة تلقائيًا مع Windows", "AltScribo will start with Windows"),
    "startup_failed": ("تعذّر تعديل التشغيل التلقائي", "Could not change the startup setting"),
    "no_audio": ("لم يتم تسجيل أي صوت", "No audio was recorded"),
    "no_speech": ("لم يتم التعرف على كلام واضح", "No clear speech was recognized"),
    "whisper_downloading": ("جارٍ تنزيل نموذج Whisper ({model}) لأول مرة، قد يستغرق دقائق",
                            "Downloading the Whisper model ({model}) for the first time, this may take minutes"),
    "whisper_downloaded": ("اكتمل تنزيل نموذج Whisper، صار التعرف يعمل بلا إنترنت",
                           "Whisper model downloaded, recognition now works offline"),
    "whisper_load_failed": ("تعذّر تحميل نموذج Whisper، راجع السجلّ",
                            "Could not load the Whisper model, see the log"),
}

_lang = "ar"


def detect():
    """ العربية إن كانت لغة واجهة Windows عربية، وإلا الإنجليزية """
    try:
        return "ar" if ctypes.windll.kernel32.GetUserDefaultUILanguage() & 0x3FF == 0x01 else "en"
    except Exception:
        return "ar"


def set_language(setting):
    global _lang
    _lang = detect() if setting == "auto" else setting


def current():
    return _lang


def is_rtl():
    return _lang == "ar"


def t(key, **kwargs):
    text = STRINGS[key][0 if _lang == "ar" else 1]
    return text.format(**kwargs) if kwargs else text


# فحص ذاتي: كل مفتاح له نصّان غير فارغين
assert all(len(v) == 2 and all(v) for v in STRINGS.values())
