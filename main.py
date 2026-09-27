import winsound
import io
import os
import sys
import threading
import time
import keyboard
import numpy as np
import pyperclip
import pystray
import scipy.io.wavfile as wav
import sounddevice as sd
import speech_recognition as sr
from PIL import Image, ImageDraw

# ==============================================================
# 1. المسارات والثوابت
# ==============================================================
def get_resource_path(relative_path):
    if hasattr(sys, '_MEIPASS'):
        return os.path.join(sys._MEIPASS, relative_path)
    return os.path.join(os.path.abspath("."), relative_path)

ICON_PATH = get_resource_path("AltScribo.ico")
if not os.path.exists(ICON_PATH):
    ICON_PATH = get_resource_path("app_icon.ico")

recognizer = sr.Recognizer()

# متغيرات التحكم في حالة التسجيل اليدوي
is_recording = False
audio_frames = []
stream = None
sample_rate = 16000


def get_default_icon():
    image = Image.new("RGB", (64, 64), color=(0, 120, 212))
    d = ImageDraw.Draw(image)
    d.rectangle([16, 16, 48, 48], fill=(255, 255, 255))
    return image


def play_sound(sound_type):
    """ تنبيهات صوتية لخفر وتأكيد بدء وإيقاف التسجيل """
    try:
        if sound_type == "start":
            winsound.Beep(1200, 150)  # نغمة مرتفعة = بدء التسجيل
        elif sound_type == "stop":
            winsound.Beep(600, 150)   # نغمة منخفضة = إيقاف التسجيل والبدء بالمعالجة
    except Exception:
        pass


# ==============================================================
# 2. حلقة تسجيل ودعم الإيقاف والتشغيل اليدوي
# ==============================================================
def audio_callback(indata, frames, time_info, status):
    """ تجميع البيانات الصوتية أثناء التسجيل المستمر """
    global audio_frames, is_recording
    if is_recording:
        audio_frames.append(indata.copy())


def toggle_recording():
    """ التبديل بين بدء وإيقاف التسجيل عند الضغط على Alt+S """
    global is_recording, audio_frames, stream

    if not is_recording:
        # --- بدء التسجيل اليدوي ---
        is_recording = True
        audio_frames = []
        play_sound("start")
        print("\n🎙️ بدأ التسجيل... اتكلم براحتك! (اضغط Alt+S للإيقاف)")

        try:
            stream = sd.InputStream(
                samplerate=sample_rate,
                channels=1,
                dtype="int16",
                callback=audio_callback
            )
            stream.start()
        except Exception as e:
            print(f"❌ خطأ أثناء فتح الميكروفون: {e}")
            is_recording = False

    else:
        # --- إيقاف التسجيل والتجهيز للصق ---
        is_recording = False
        play_sound("stop")
        print("🛑 تم إيقاف التسجيل، جاري تحويل الصوت ولصق النص...")

        if stream is not None:
            stream.stop()
            stream.close()
            stream = None

        # معالجة الصوت في خيط مستقل لعدم تجميد الكيبورد
        threading.Thread(target=process_and_inject, daemon=True).start()


def process_and_inject():
    """ تحويل التسجيل إلى نص ولصقه مباشرة في مكان المؤشر """
    global audio_frames

    if not audio_frames:
        print("⚠️ لم يتم تسجيل أي صوت.")
        return

    try:
        # دمج كل المكاتب الصوتية المسجلة
        recording = np.concatenate(audio_frames, axis=0)

        # مضاعفة حساسية الصوت الخافت
        max_val = np.max(np.abs(recording))
        if max_val > 0:
            gain = min(32767.0 / max_val, 4.0)
            recording = (recording * gain).astype(np.int16)

        wav_io = io.BytesIO()
        wav.write(wav_io, sample_rate, recording)
        wav_io.seek(0)

        with sr.AudioFile(wav_io) as source:
            audio = recognizer.record(source)
            try:
                text = recognizer.recognize_google(audio, language="ar-SA")
                if text:
                    text_to_paste = text.strip() + " "
                    print(f"✅ تم التعرف ولصق: {text_to_paste}")

                    # حفظ الحافظة القديمة
                    old_clipboard = pyperclip.paste()

                    # لصق النص الجديد فوراً
                    pyperclip.copy(text_to_paste)
                    time.sleep(0.05)
                    keyboard.send("ctrl+v")

                    # إرجاع الحافظة القديمة
                    time.sleep(0.15)
                    try:
                        pyperclip.copy(old_clipboard)
                    except Exception:
                        pass
            except sr.UnknownValueError:
                print("⚠️ لم يتم التعرف على كلام واضح.")
            except sr.RequestError as e:
                print(f"❌ خطأ اتصالات: {e}")

    except Exception as e:
        print(f"⚠️ خطأ أثناء معالجة الصوت: {e}")


# ==============================================================
# 3. أيقونة شريط المهام (System Tray) والاختصارات العامة
# ==============================================================
def setup_tray_and_hotkey():
    if os.path.exists(ICON_PATH):
        try:
            image = Image.open(ICON_PATH)
        except Exception:
            image = get_default_icon()
    else:
        image = get_default_icon()

    def on_exit(icon, item):
        global is_recording, stream
        is_recording = False
        if stream:
            stream.stop()
            stream.close()
        icon.stop()
        os._exit(0)

    menu = pystray.Menu(
        pystray.MenuItem("AltScribo Voice Typing (Alt+S)", lambda: None, enabled=False),
        pystray.MenuItem("تشغيل / إيقاف التسجيل", lambda icon, item: toggle_recording()),
        pystray.MenuItem("خروج (Exit)", on_exit),
    )

    icon_obj = pystray.Icon("AltScribo", image, "AltScribo - أداة الإملاء الصوتي", menu)

    # تسجيل اختصار Alt+S فقط للبدء والإنهاء
    try:
        keyboard.add_hotkey("alt+s", toggle_recording)
        print("✅ تم تفعيل الاختصار العام (Alt+S) بنجاح.")
    except Exception as e:
        print(f"❌ فشل تسجيل الاختصار: {e}")

    icon_obj.run()


if __name__ == "__main__":
    print("\n===============================================")
    print("🚀 بدء تشغيل AltScribo Global Voice Typing Tool...")
    print("===============================================")
    print("1. اضغط Alt + S للبدء في التسجيل (ستسمع نغمة حادة).")
    print("2. اتكلم براحتك بدون أي تقييد بالوقت.")
    print("3. اضغط Alt + S مرة أخرى للإيقاف ولصق النص تلقائياً!")
    print("===============================================\n")

    setup_tray_and_hotkey()