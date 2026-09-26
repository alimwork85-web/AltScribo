import tkinter as tk
from tkinter import ttk, messagebox
import speech_recognition as sr
import threading
import time
import pystray
from PIL import Image
import keyboard
import pyperclip
import sys
import os

# ==============================================================
# 1. تعريف المسارات والثوابت (Constants)
# يرجى التأكد من أن هذه المسارات صحيحة تماماً على جهازك
# ==============================================================
PROJECT_DIR = r"C:\Users\suailali\Desktop\المستودع\AltScribo"
ICON_PATH = os.path.join(PROJECT_DIR, "app_icon.ico")

# إعدادات التعرف على الصوت
recognizer = sr.Recognizer()
microphone = sr.Microphone()

# حالة التطبيق العامة
is_listening = False
current_thread = None
audio_capture_lock = threading.Lock() # قفل لضمان التعامل الآمن مع المدخلات

class AltScriboApp:
    """النافذة الرئيسية للتطبيق (Always-on-Top GUI)"""
    def __init__(self, master):
        self.master = master
        master.title("AltScribo - المساعد الصوتي")
        
        # تعيين النافذة لتكون دائماً في المقدمة وبحجم ثابت وشفافاً نسبياً
        master.attributes("-topmost", True) 
        master.geometry("600x450") # تحديد حجم مناسب للواجهة
        master.protocol("WM_DELETE_WINDOW", self.on_closing_gui)

        # إعداد الواجهة باستخدام Tkinter Notebook أو Frame لإدارة العناصر
        self.main_frame = ttk.Frame(master, padding="10 10 10 10")
        self.main_frame.pack(fill='both', expand=True)

        # مربع النص (Text Area)
        self.text_area = tk.Text(self.main_frame, wrap='word', font=('Arial', 12), bd=0, relief=tk.FLAT)
        self.text_area.pack(fill='both', expand=True, pady=(0, 15))

        # إطار الأزرار (Buttons Frame)
        button_frame = ttk.Frame(self.main_frame)
        button_frame.pack(fill='x')
        
        # الأزرار
        self.btn_speak = ttk.Button(button_frame, text="🎙️ Speak / Start", command=lambda: self.start_listening())
        self.btn_speak.pack(side='left', padx=(0, 10), expand=True)

        self.btn_copy = ttk.Button(button_frame, text="📋 Copy", command=self.copy_text)
        self.btn_copy.pack(side='left', padx=(0, 10), expand=True)

        self.btn_delete = ttk.Button(button_frame, text="🗑️ Delete", command=self.delete_text)
        self.btn_delete.pack(side='left', padx=(0, 10), expand=True)

        # تهيئة الحالة الأولية للزر
        self.update_speak_button_state("🎙️ Speak / Start")

    def update_speak_button_state(self, text):
        """يحدث النص الافتراضي لزر التحدث."""
        if self.btn_speak.cget("text") != text:
            self.btn_speak.config(text=text)


    # ==============================================================
    # 2. منطق التعرف على الصوت (STT Logic)
    # ==============================================================

    def update_status(self, status):
        """تحديث حالة التقديم في الواجهة."""
        print(f"[STATUS] {status}")
        if 'Status' in globals(): # للطباعة فقط للتأكد من وجودها
            pass 

    def start_listening(self):
        """يبدأ عملية الاستماع والتسجيل (يتم استدعاؤه بالضغط على الزر أو عند التفعيل)."""
        global is_listening, current_thread
        if is_listening:
            # إذا كنا نستمع بالفعل، فإن الضغط على هذا الزر يعني محاولة الإيقاف المؤقت/المتابعة
            return 

        self.text_area.delete(1.0, tk.END) # مسح المحتوى عند بدء جلسة جديدة
        is_listening = True
        self.update_speak_button_state("⏸️ Pause") # تغيير حالة الزر إلى الإيقاف المؤقت
        self.master.lift() # التأكد من أن النافذة في المقدمة

        # تشغيل الاستماع في خيط منفصل لمنع تجميد الواجهة (GUI thread)
        current_thread = threading.Thread(target=self._listen_loop, daemon=True)
        current_thread.start()

    def _listen_loop(self):
        """الحلقة الرئيسية للاستماع والتسجيل."""
        global is_listening
        with audio_capture_lock:
            print("--- [AltScribo] بدء الاستماع للمايكروفون...")
            while is_listening:
                try:
                    # الانتظار لفترة قصيرة في حال تغيير الحالة (مثل الإيقاف المؤقت)
                    time.sleep(0.1) 

                    if not is_listening: # تحقق من أن الخيط تم إيقافه يدوياً أو عبر أمر copy
                        break
                        
                    with microphone as source:
                        # ضبط التعديل على ضجيج الخلفية لتحسين الجودة
                        recognizer.adjust_for_ambient_noise(source, duration=0.5) 
                        print("[AltScribo] الاستماع الآن...")
                        # استمع لمدة قصيرة وانتظر الصوت
                        audio = recognizer.listen(source)

                    # محاولة التعرف على الكلام (دعم العربي والإنجليزية Mixed Language)
                    # استخدام اللغة العربية العامية مع الإنجليزية لزيادة الدقة
                    try:
                        text = recognizer.recognize_google(audio, language="ar-EG-AT", show_all=True) 
                        self.process_recognized_text(text)
                    except sr.WaitTimeoutError:
                        # لا تفعل شيئاً إذا لم يتم التقاط صوت خلال الفترة المحددة
                        pass
                    except Exception as e:
                        # التعامل مع أخطاء الشبكة أو التعرف على الكلام غير الناجح
                        print(f"⚠️ خطأ في التعرف على الصوت أو الاتصال بالشبكة: {e}")
                        # قد يكون هذا الخطأ طبيعياً عند التوقف المؤقت للاتصال
                        time.sleep(1) 


                except KeyboardInterrupt:
                    # تم إيقاف الاستماع عبر مقاطعة الخيط
                    print("\n[AltScribo] تم طلب الإيقاف يدوياً.")
                    break
                except Exception as e:
                    if is_listening:
                        print(f"❌ خطأ فادح في حلقة الاستماع: {e}")
                        is_listening = False # إيقاف العملية عند فشل كبير

        # التأكد من إعادة تعيين الحالة بعد خروج الحلقة
        self.master.after(0, lambda: self.update_speak_button_state("🎙️ Speak / Start"))


    def process_recognized_text(self, text):
        """يقوم بإدراج النص المكتشف في مربع النصوص."""
        global is_listening
        # تنظيف النص قبل الإضافة (لإزالة علامات التوقيت أو بيانات إضافية)
        clean_text = text.strip() 
        if clean_text:
            self.text_area.insert(tk.END, clean_text + " ")


    # ==============================================================
    # 3. وظائف التحكم بالأزرار (Button Actions)
    # ==============================================================

    def pause_resume(self):
        """يتحكم في حالة الاستماع: مؤقت أو استئناف."""
        global is_listening, current_thread

        if not is_listening:
            messagebox.showinfo("AltScribo", "الرجاء الضغط أولاً على زر البدء لتفعيل التطبيق.")
            return

        try:
            # محاكاة إيقاف مؤقت للتعرف على الصوت (لأن المكتبة لا توفر دالة pause/resume مباشرة)
            # الطريقة الأبسط هي التحكم في حالة is_listening داخل الخيط
            is_speaking = not is_speaking # تبديل الحالة المنطقية

            if is_speaking:
                # الانتقال إلى الإيقاف المؤقت (Pause)
                self.update_status("⏸️ تم إيقاف التسجيل مؤقتاً.")
                self.update_speak_button_state("🎙️ Resume")
                # لا نفعل شيئاً سوى تحديث الواجهة، الخيط يستمر في الحلقة لكنه ينتظر

            else:
                # الاستئناف (Resume) - يجب التأكد أن الـ loop يعمل أو إعادة تشغيله
                self.update_status("▶️ استئناف التسجيل...")
                self.update_speak_button_state("⏸️ Pause")
                # في التطبيق الحقيقي، قد تحتاج إلى إشارة لتنشيط الاستماع داخل الخيط بشكل أكثر تعقيداً هنا.

        except Exception as e:
            messagebox.showerror("خطأ", f"حدث خطأ أثناء محاولة تغيير الحالة: {e}")


    def copy_text(self):
        """ينسخ النص بالكامل ويوقف عملية الاستماع."""
        global is_listening, current_thread
        if not self.text_area.get(1.0, tk.END).strip():
            messagebox.showwarning("تنبيه", "لا يوجد نص لنسخه.")
            return

        try:
            # 1. النسخ إلى الحافظة (Clipboard)
            text_to_copy = self.text_area.get(1.0, tk.END).strip()
            pyperclip.copy(text_to_copy)
            self.update_status("✅ تم نسخ النص بنجاح.")

        finally:
            # 2. إيقاف عملية الاستماع (توقف كلياً وتغلق الخيوط)
            is_listening = False
            if current_thread and current_thread.is_alive():
                print("[AltScribo] إرسال إشارة الإيقاف لـ STT...")
                # تعطيل الزر وعرض الحالة النهائية
                self.update_speak_button_state("🎙️ Speak / Start")
                messagebox.showinfo("نجاح", "تم نسخ النص وإيقاف التسجيل بنجاح.")

    def delete_text(self):
        """يمسح محتوى مربع النصوص."""
        global is_listening
        if is_listening:
            # يجب إيقاف الاستماع قبل المسح لتجنب أي تعارضات
            print("[AltScribo] مسح المحتوى يتطلب إيقاف الاستماع مؤقتاً.")
            is_listening = False
            self.update_speak_button_state("🎙️ Speak / Start")
        
        # مسح النص من الواجهة
        self.text_area.delete(1.0, tk.END)
        self.update_status("🗑️ تم مسح محتوى مربع النصوص.")

    def on_closing_gui(self):
        """معالجة إغلاق النافذة: يوقف الاستماع ويترك التطبيق في صينية النظام."""
        global is_listening, current_thread
        print("[AltScribo] إشارة إغلاق GUI. تجميد STT...")
        is_listening = False # إيقاف الـ Listening Loop
        self.update_status("⏹️ تم إيقاف التسجيل. سيتم تخفيض النافذة إلى صينية النظام.")

        # لا نخرج من البرنامج (sys.exit()) بل نخفض الواجهة ونترك pystray يعمل
        self.master.withdraw() 


# ==============================================================
# 4. تهيئة التطبيق وتشغيل الأجزاء المساعدة
# ==============================================================

def setup_hotkey_and_tray(root):
    """يربط اختصار لوحة المفاتيح ويهيئ أيقونة صينية النظام."""
    
    app = AltScriboApp(root)

    # ربط وظيفة التفعيل بالاختصار Alt+S
    def hotkey_activate():
        print("✨ تم الضغط على الاختصار (Alt+S). تفعيل التطبيق...")
        if root.winfo_ismapped(): # إذا كانت النافذة موجودة بالفعل، قم بتنشيطها وتجميع التركيز
            root.lift() 
        else:
            # في حالة لم يتم فتح الواجهة بعد، اترك الـ Tkinter GUI يقوم بالتعامل مع الأمر
             pass

    try:
        keyboard.add_hotkey("alt+s", hotkey_activate)
        print("✅ تم تفعيل الاختصار Alt + S بنجاح.")
    except Exception as e:
        print(f"❌ فشل في ربط المفاتيح (قد يتطلب تشغيل كمدير): {e}")


    # إعداد أيقونة صينية النظام (System Tray Icon)
    def create_tray_icon():
        try:
            image = Image.open(ICON_PATH) # استخدام الأيقونة المحددة
        except FileNotFoundError:
            print("⚠️ تنبيه: لم يتم العثور على مسار أيقونة التطبيق المحدد.")
            # استخدام صورة احتياطية أو تجاهل خطوة الأيقونة إذا لزم الأمر

        def show_window(icon, item):
            """المنطق الذي يعمل عند النقر بالماوس على أيقونة صينية النظام."""
            print("🖱️ تم النقر على أيقونة الـ Tray. تنشيط النافذة...")
            root.deiconify() # إظهار الواجهة مرة أخرى
            root.lift()
        
        def exit_tray_icon(icon, item):
            """المنطق عند النقر بالزر الأيمن 'Exit'."""
            print("🛑 تم طلب خروج التطبيق من صينية النظام.")
            global is_listening
            is_listening = False # إيقاف الاستماع
            root.destroy()

        # بناء أيقونة الـ Tray باستخدام pystray
        icon_obj = pystray.Icon(
            "AltScribo", 
            image=image, 
            cursor=None,
            label="AltScribo - تفريغ صوتي", # النص الذي يظهر عند التحويم
            menu=pystray.Menu(
                ("فتح/تفعيل Alt+S", show_window),
                ("➖ خروج (Exit)", exit_tray_icon)
            )
        )

    return icon_obj

# --------------------- نقطة الدخول الرئيسية ------------------------
if __name__ == "__main__":
    print("\n===============================================")
    print("🚀 بدء تشغيل AltScribo Voice Dictation Tool...")
    print("===============================================")

    root = tk.Tk()
    # إعداد الـ Tkinter ليكون مخفياً مبدئياً حتى لا يظهر عند التشغيل
    root.withdraw() 
    
    # 1. تهيئة الأيقونة والربط بالاختصار
    tray_icon = setup_hotkey_and_tray(root)

    # 2. تشغيل الواجهة في الخلفية (GUI Thread)
    # يتم تمرير الكائن root إلى الـ App class ليقوم ببناء العناصر المرئية
    app_gui = AltScriboApp(root)
    
    # تهيئة الحالة الأولية للزر عند بدء التشغيل
    app_gui.update_status("✅ جاهز: اضغط Alt+S أو انقر على الأيقونة.")

    try:
        # 3. تشغيل حلقة Tkinter الرئيسية (GUI Event Loop)
        root.mainloop()
    finally:
        # تنظيف الموارد عند إغلاق root.mainloop()
        tray_icon.stop()
        print("===============================================")
        print("🛑 تم إنهاء AltScribo بالكامل.")

