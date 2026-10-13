# AltScribo

أداة إملاء صوتي عربية لنظام Windows. تعمل من أيقونة في شريط المهام: اضغط `Alt+S` لبدء التسجيل، وتكلّم، ثم اضغطه مرة ثانية فيُحوَّل الصوت إلى نص ويُلصق في مكان المؤشر.

> **تنبيه خصوصية:** يُرسل الصوت المسجَّل إلى خدمة Google للتعرف على الكلام، فتحتاج الأداة إلى اتصال بالإنترنت.

## التشغيل من المصدر

```bash
python -m venv venv
venv\Scripts\pip install -r requirements.txt
venv\Scripts\python main.py
```

## بناء ملف EXE

```bash
venv\Scripts\pyinstaller AltScribo.spec --noconfirm
```

يظهر الناتج في `dist\AltScribo\AltScribo.exe`.

## الإعدادات والسجلّ

كلاهما في `%APPDATA%\AltScribo` ويمكن فتحهما من قائمة أيقونة الشريط:

- `settings.json`: `hotkey` و`language` و`timeout_seconds` و`max_gain` و`sample_rate`. يلزم إعادة تشغيل الأداة بعد التعديل.
- `altscribo.log`: سجلّ التشغيل والأخطاء.

## بنية الكود

- `altscribo/config.py`: المسارات والإعدادات والسجلّ.
- `altscribo/recorder.py`: التسجيل من الميكروفون.
- `altscribo/transcriber.py`: تحويل الصوت إلى نص.
- `altscribo/injector.py`: اللصق عبر الحافظة مع حفظها وإعادتها.
- `altscribo/app.py`: أيقونة الشريط والاختصار والإشعارات.
