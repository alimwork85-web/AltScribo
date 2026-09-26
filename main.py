import io
import os
import sys
import threading
import time
import tkinter as tk
from tkinter import messagebox, ttk

import keyboard
import numpy as np
import pyperclip
import pystray
import scipy.io.wavfile as wav
import sounddevice as sd
import speech_recognition as sr
from PIL import Image, ImageDraw

# ==============================================================
# 1. تعريف المسارات والثوابت
# ==============================================================
def get_resource_path(relative_path):
    """ الحصول على المسار الصحيح سواء أثناء التطوير أو بعد التجميع بـ PyInstaller """
    if hasattr(sys, '_MEIPASS'):
        return os.path.join(sys._MEIPASS, relative_path)
    return os.path.join(os.path.abspath("."), relative_path)

# البحث عن ملف الأيقونة بمرونة في مسار المشروع أو المجلد المجمع
ICON_PATH = get_resource_path("AltScribo.ico")
if not os.path.exists(ICON_PATH):
    ICON_PATH = get_resource_path("app_icon.ico")

recognizer = sr.Recognizer()

is_listening = False
is_paused = False
current_thread = None


def get_default_icon():
    image = Image.new("RGB", (64, 64), color=(0, 120, 212))
    d = ImageDraw.Draw(image)
    d.rectangle([16, 16, 48, 48], fill=(255, 255, 255))
    return image


class AltScriboApp:

    def __init__(self, master):
        self.master = master
        self.master.title("AltScribo - المساعد الصوتي")

        self.master.attributes("-topmost", True)
        self.master.geometry("500x300")
        self.master.minsize(450, 220)  # ضمان حد أدنى للارتفاع لعدم اختفاء الأزرار
        self.master.protocol("WM_DELETE_WINDOW", self.on_closing_gui)

        if os.path.exists(ICON_PATH):
            try:
                self.master.iconbitmap(ICON_PATH)
            except Exception:
                pass

        self.main_frame = ttk.Frame(self.master, padding="10 10 10 10")
        self.main_frame.pack(fill="both", expand=True)

        # ------------------------------------------------------
        # حزم إطار الأزرار أولاً في الأسفل لضمان ثباته
        # ------------------------------------------------------
        button_frame = ttk.Frame(self.main_frame)
        button_frame.pack(side="bottom", fill="x", pady=(5, 0))

        self.btn_speak = ttk.Button(
            button_frame, text="🎙️ Speak", command=self.toggle_speak_manual
        )
        self.btn_speak.pack(side="left", padx=(0, 5), expand=True, fill="x")

        self.btn_copy = ttk.Button(
            button_frame, text="📋 Copy", command=self.copy_text
        )
        self.btn_copy.pack(side="left", padx=(0, 5), expand=True, fill="x")

        self.btn_delete = ttk.Button(
            button_frame, text="🗑️ Delete", command=self.delete_text
        )
        self.btn_delete.pack(side="left", expand=True, fill="x")

        # ------------------------------------------------------
        # مربع النص يأخذ المساحة المتبقية في الأعلى
        # ------------------------------------------------------
        self.text_area = tk.Text(
            self.main_frame, wrap="word", font=("Segoe UI", 11), bd=1, height=8
        )
        self.text_area.pack(side="top", fill="both", expand=True, pady=(0, 5))

        # تفعيل اختصار Ctrl+A لتظليل النص بالكامل
        self.text_area.bind("<Control-a>", self.select_all)
        self.text_area.bind("<Control-A>", self.select_all)

    def select_all(self, event=None):
        """تحديد النص كاملاً في مربع النص"""
        self.text_area.tag_add("sel", "1.0", "end-1c")
        self.text_area.focus_set()
        return "break"

    def show_and_start(self):
        self.master.deiconify()
        self.master.lift()
        self.master.focus_force()

        global is_listening, is_paused
        if not is_listening:
            self.start_listening()
        elif is_paused:
            self.resume_listening()

    def start_listening(self):
        global is_listening, is_paused, current_thread
        is_listening = True
        is_paused = False
        self.btn_speak.config(text="⏸️ Pause")

        current_thread = threading.Thread(
            target=self._listen_loop, daemon=True
        )
        current_thread.start()

    def pause_listening(self):
        global is_paused
        is_paused = True
        self.btn_speak.config(text="🎙️ Resume")

    def resume_listening(self):
        global is_paused
        is_paused = False
        self.btn_speak.config(text="⏸️ Pause")

    def stop_completely(self):
        global is_listening, is_paused
        is_listening = False
        is_paused = False
        self.btn_speak.config(text="🎙️ Speak")

    def toggle_speak_manual(self):
        global is_listening, is_paused
        if not is_listening:
            self.start_listening()
        elif not is_paused:
            self.pause_listening()
        else:
            self.resume_listening()

    def _listen_loop(self):
        """حلقة الاستماع باستخدام sounddevice لتفادي PyAudio"""
        global is_listening, is_paused
        sample_rate = 16000
        duration = 4  # التسجيل لمدة 4 ثوانٍ في كل دورة استماع

        while is_listening:
            if is_paused:
                time.sleep(0.2)
                continue

            try:
                # تسجيل الصوت من الميكروفون
                recording = sd.rec(
                    int(duration * sample_rate),
                    samplerate=sample_rate,
                    channels=1,
                    dtype="int16",
                )
                sd.wait()

                if is_listening and not is_paused:
                    # تحويل البيانات الصوتية لذاكرة مؤقتة
                    wav_io = io.BytesIO()
                    wav.write(wav_io, sample_rate, recording)
                    wav_io.seek(0)

                    with sr.AudioFile(wav_io) as source:
                        audio = recognizer.record(source)
                        try:
                            text = recognizer.recognize_google(
                                audio, language="ar-SA"
                            )
                            if text:
                                self.master.after(
                                    0, self._append_text, text + " "
                                )
                        except sr.UnknownValueError:
                            pass
                        except sr.RequestError as e:
                            print(f"❌ خطأ اتصالات: {e}")

            except Exception as e:
                print(f"⚠️ تنبيه أثناء تسجيل الصوت: {e}")
                time.sleep(0.5)

        self.master.after(0, lambda: self.btn_speak.config(text="🎙️ Speak"))

    def _append_text(self, text):
        self.text_area.insert(tk.END, text)
        self.text_area.see(tk.END)

    def copy_text(self):
        """تظليل كامل النص ونسخه إلى الحافظة تلقائياً"""
        self.select_all()
        text_to_copy = self.text_area.get(1.0, tk.END).strip()
        if text_to_copy:
            pyperclip.copy(text_to_copy)
            messagebox.showinfo("AltScribo", "تم تظليل النص ونسخه إلى الحافظة بنجاح.")

        self.stop_completely()

    def delete_text(self):
        self.text_area.delete(1.0, tk.END)

    def on_closing_gui(self):
        self.stop_completely()
        self.master.withdraw()


def setup_tray_and_hotkey(app, root):
    if os.path.exists(ICON_PATH):
        try:
            image = Image.open(ICON_PATH)
        except Exception:
            image = get_default_icon()
    else:
        image = get_default_icon()

    def on_show(icon, item):
        app.show_and_start()

    def on_exit(icon, item):
        app.stop_completely()
        icon.stop()
        root.after(0, root.destroy)

    menu = pystray.Menu(
        pystray.MenuItem("فتح / إملاء (Alt+S)", on_show),
        pystray.MenuItem("خروج (Exit)", on_exit),
    )

    icon_obj = pystray.Icon("AltScribo", image, "AltScribo Voice Tool", menu)

    try:
        keyboard.add_hotkey("alt+s", lambda: app.show_and_start())
        print("✅ تم تفعيل الاختصار Alt + S بنجاح.")
    except Exception as e:
        print(f"❌ فشل تسجيل الاختصار: {e}")

    threading.Thread(target=icon_obj.run, daemon=True).start()


if __name__ == "__main__":
    print("\n===============================================")
    print("🚀 بدء تشغيل AltScribo Voice Dictation Tool...")
    print("===============================================")

    root = tk.Tk()
    root.withdraw()

    app = AltScriboApp(root)
    setup_tray_and_hotkey(app, root)

    try:
        root.mainloop()
    except KeyboardInterrupt:
        pass
    finally:
        print("🛑 تم إغلاق التطبيق.")