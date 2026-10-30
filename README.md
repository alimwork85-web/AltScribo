# AltScribo

Voice dictation for Windows: press a hotkey, speak, and the text is typed into whatever window you are in. Bilingual (Arabic/English) interface, a system-wide hotkey that survives screen lock, a fully local Whisper engine, and an on-screen recording indicator.

**Current version: 1.5.4** — Developer: **Ali Alhumedi**

## What's new in 1.5.4

- Default shortcut is now `Alt+F9` instead of `Alt+S`, so pressing the hotkey can no longer type a letter into the focused window.
- "Open text history" now opens a small window with the last 20 texts: select one and press **Copy** (or double-click it).
- "Paste last text" now **copies** the text to the clipboard and tells you, so `Ctrl+V` works no matter which window has focus.
- The history window has a dark title bar matching the app.

## How it works

1. Put the caret wherever you want to write.
2. Press `Alt+F9` — a high beep plays and the tray icon turns red: recording started.
3. Speak, with no time limit.
4. Press `Alt+F9` again — a low beep, and the text appears at the caret a moment later.

## Features

- **System-wide hotkey:** works in any program and never leaks the `S` keystroke into the focused window. It uses the Windows `RegisterHotKey` API instead of a low-level hook, so it keeps working after `Win+L`, sleep, or long idle. If another program already owns the shortcut, you get a clear notification instead of silent failure.
- **Bilingual interface:** the tray menu, notifications and tooltips follow Windows' language, or you can force Arabic or English from the menu.
- **On-screen indicator:** a small floating capsule shows recording state with a blinking dot and a timer, then "Typing…", then `OFF` — without ever taking focus from the window you are typing in.
- **Text history:** every recognized text is saved (last 20) to `history.json`, so nothing is lost if the paste lands in the wrong window. "Paste last text" re-inserts the most recent one.
- **Automatic offline fallback:** if Google cannot be reached and Whisper is installed, the same recording is transcribed locally and you are told so.
- **Push-to-talk:** optional mode where recording runs only while the hotkey is held down.
- **Auto-stop on silence:** optionally stop and transcribe after N seconds of silence.
- **Microphone selection:** pick the input device from a submenu; the choice is stored by device name and survives restarts.
- **Two engines:** Google (online) or Whisper (fully local, no internet). Pick from the tray menu.
- **Auto punctuation:** adds sentence-ending marks and commas before connectors, and converts Eastern digits to Western ones (0-9). Skipped for English input.
- **Spoken punctuation:** say "فاصلة", "علامة استفهام", "سطر جديد"… (table below).
- **Paste that respects the clipboard:** the previous clipboard text is restored after pasting; images and files are left untouched.
- **Single instance:** a second copy refuses to start, so you never record twice.
- **Update check:** notifies once if a newer release exists on GitHub. It never downloads or installs anything.
- **Graceful failures:** clear notifications instead of silent ones; the log lives at `%APPDATA%\AltScribo\altscribo.log`.

## Download and run

Download `AltScribo-v1.5.4-windows.zip` from the [releases page](https://github.com/alimwork85-web/AltScribo/releases), unzip it anywhere, then run `AltScribo.exe`. The icon appears in the notification area (possibly inside the hidden-icons arrow).

To start it with Windows: choose "Start with Windows" in the tray menu, and choose it again to undo.

## On-screen indicator

While recording, a small capsule appears at the bottom center of the screen that holds the active window:

| State | What you see | Behaviour |
|---|---|---|
| Recording | blinking red dot, `ON`, and a timer (`0:07`) | stays visible |
| Typing | gray dot, "Typing…" | stays until transcription and pasting finish |
| Done | `OFF` | visible for about 1.2 s, then disappears |

The capsule never takes keyboard focus, never appears in `Alt+Tab` or the taskbar, and clicks pass through it to whatever is underneath. Turn it off with "On-screen indicator" in the tray menu.

## Push-to-talk and auto-stop

- **Hold to talk:** enable it from the menu (`push_to_talk`); recording then runs only while you hold the hotkey, and releasing the key stops it and pastes.
- **Auto-stop on silence:** set `auto_stop_silence_seconds` above zero (e.g. `3`). Recording stops and pastes after that many seconds of silence. The countdown only starts once speech is detected, so silence before you start talking does not cut you off. `0` disables it.

## Microphone selection

Tray menu → "Microphone" → pick a device, or "Default". The device is stored by name (indices change between sessions), applied to the next recording, and cannot be changed while recording.

## Text history

Every successful recognition is appended to `%APPDATA%\AltScribo\history.json` (last 20 entries, atomic writes; a corrupted file is never overwritten). Menu items:

- **Paste last text** — copies the latest text to the clipboard and notifies you; paste it yourself with `Ctrl+V`. Copying does not depend on which window has focus.
- **Open text history** — a small window listing the last 20 texts. Select one and press **Copy** (or double-click it) to copy the full text, not the shortened preview. The window has no scrollbar; the mouse wheel scrolls the list.

## Offline recognition (Whisper)

Choose "Whisper (local, offline)" in the tray menu. On first use the model (~480 MB for `small`) is downloaded to `%APPDATA%\AltScribo\models`; afterwards recognition runs entirely on your machine, with no internet and no audio leaving the computer. Whisper punctuates by itself.

- Slightly slower than Google: a few seconds per sentence on CPU.
- Change the model with `whisper_model`: `base` is faster and less accurate, `medium` is much slower and more accurate.
- If `faster-whisper` is not installed the option appears disabled as "Whisper (not installed)".
- If the internet drops mid-use and Whisper is installed, the same recording is transcribed locally and you get a notification.

## Speech language

Tray menu → "Speech: Arabic" / "Speech: English" switches the recognition language between `ar-SA` and `en-US` with no restart and no model reload. This is independent of the interface language. In English mode the Arabic auto-punctuation and spoken punctuation commands are skipped; whitespace and digit normalization still applies.

## Spoken punctuation

| You say | Result |
|---|---|
| فاصلة | ، |
| فاصلة منقوطة | ؛ |
| علامة استفهام | ؟ |
| علامة تعجب | ! |
| نقطتان رأسيتان | : |
| نقطة | . (only at the end of speech — it is a common word) |
| سطر جديد | line break |
| فقرة جديدة | blank line, then a line break |

You can disable these commands from the menu if they conflict with what you dictate.

## Settings

Tray menu → "Open settings", or edit `%APPDATA%\AltScribo\settings.json`:

| Setting | Meaning | Default |
|---|---|---|
| `hotkey` | global shortcut | `alt+f9` |
| `language` | speech recognition language | `ar-SA` |
| `timeout_seconds` | service timeout in seconds | `15` |
| `max_gain` | maximum amplification for quiet audio | `4.0` |
| `sample_rate` | recording sample rate | `16000` |
| `engine` | `google` or `whisper` | `google` |
| `whisper_model` | `tiny`, `base`, `small`, `medium`, `large-v3` | `small` |
| `auto_punctuation` | automatic punctuation (Arabic only) | `true` |
| `spoken_punctuation` | spoken punctuation commands (Arabic only) | `true` |
| `ui_language` | interface language: `auto`, `ar`, `en` | `auto` |
| `input_device` | microphone name, `""` = system default | `""` |
| `push_to_talk` | record only while the hotkey is held | `false` |
| `auto_stop_silence_seconds` | stop after this many silent seconds, `0` = off | `0` |
| `silence_threshold` | RMS level counted as speech | `500` |
| `show_overlay` | show the on-screen indicator | `true` |

Restart after editing the file by hand (changes made from the menu apply immediately). `language` accepts other dialects such as `ar-EG` or `ar-AE`.

## Privacy

With the Google engine the recorded audio is sent to Google's speech service, which is why it needs internet. With Whisper the audio never leaves your machine. Recordings are not stored; dictated texts are kept only in the local `history.json` (last 20, on your disk), and `altscribo.log` holds startup events and errors only.

## Run from source

```bash
python -m venv venv
venv\Scripts\pip install -r requirements.txt
venv\Scripts\python main.py
```

For local recognition install `requirements-whisper.txt` instead. That needs Python 3.12–3.14, because `ctranslate2` and `onnxruntime` are not available for Python 3.15 yet.

## Build the EXE

```bash
venv\Scripts\pyinstaller AltScribo.spec --noconfirm
```

Output: `dist\AltScribo\AltScribo.exe`. If `faster-whisper` is installed in the build environment, local recognition is bundled automatically (larger build); otherwise the build ships the Google engine only. The exe carries a version resource with the publisher name and version (see `version_info.txt`).

## Code layout

- `altscribo/config.py`: paths, settings, logging.
- `altscribo/recorder.py`: microphone recording, device selection, silence detection.
- `altscribo/transcriber.py`: audio to text via Google or Whisper, plus local fallback.
- `altscribo/punctuation.py`: auto punctuation and spoken punctuation commands.
- `altscribo/startup.py`: the "start with Windows" shortcut.
- `altscribo/menu.py`: the custom tray menu and the Tk UI thread.
- `altscribo/overlay.py`: the floating recording indicator.
- `altscribo/i18n.py`: every user-visible string, Arabic and English.
- `altscribo/injector.py`: paste via the clipboard, keeping the old contents.
- `altscribo/app.py`: tray icon, global hotkey, notifications, update check.

## Requirements

Windows 10 or newer, a microphone, and an internet connection (for the Google engine, or the first Whisper model download only).

## Developer

**Ali Alhumedi** — [github.com/alimwork85-web](https://github.com/alimwork85-web) · © 2026 Ali Alhumedi

---

<div dir="rtl">

# AltScribo (العربية)

أداة إملاء صوتي لويندوز: تضغط اختصارًا، تتكلم، فيُكتب الكلام في أي نافذة تعمل فيها. بواجهة عربية/إنجليزية، واختصار عام لا يتوقف بعد قفل الشاشة، ومحرك Whisper محلي، ومؤشر عائم على الشاشة.

**الإصدار الحالي: 1.5.4** — المطوّر: **علي الحميدي (Ali Alhumedi)**

## الجديد في 1.5.4

- الاختصار الافتراضي صار `Alt+F9` بدل `Alt+S`، فلم يبقَ الاختصار قادرًا على كتابة حرف في النافذة التي تعمل فيها.
- «فتح سجل النصوص» يفتح نافذة صغيرة بآخر 20 نصًا: اختر نصًا واضغط **«نسخ»** أو انقر عليه نقرًا مزدوجًا.
- «أعد لصق آخر نص» صار **ينسخ** النص إلى الحافظة ويُشعرك بذلك، فتلصقه أنت بـ`Ctrl+V` أيًّا كانت النافذة النشطة.
- نافذة السجل بشريط عنوان داكن يطابق التطبيق.

## كيف تعمل

1. ضع المؤشر في أي مكان تريد الكتابة فيه.
2. اضغط `Alt+F9`، فتسمع نغمة حادة وتتحول الأيقونة إلى أيقونة بنقطة حمراء: بدأ التسجيل.
3. تكلّم دون أي حد زمني.
4. اضغط `Alt+F9` مرة ثانية، فتسمع نغمة منخفضة، ثم يظهر النص في مكان المؤشر خلال لحظات.

## المزايا

- **اختصار عام ثابت:** يعمل في أي برنامج، ولا يمرّر حرف `S` إلى النافذة المفتوحة. يستخدم `RegisterHotKey` في Windows بدل خطاف لوحة المفاتيح، فيبقى يعمل بعد قفل الشاشة (`Win+L`) وبعد السكون. وإن كان الاختصار محجوزًا لبرنامج آخر تظهر رسالة واضحة بدل الفشل الصامت.
- **واجهة ثنائية اللغة:** القائمة والإشعارات وتلميح الأيقونة تتبع لغة Windows، أو تختار العربية أو الإنجليزية من القائمة.
- **مؤشر على الشاشة:** كبسولة صغيرة تعرض حالة التسجيل بنقطة تنبض وعدّاد، ثم «جارٍ الكتابة…»، ثم `OFF`، دون أن تسرق التركيز من نافذتك.
- **سجل النصوص:** كل نص مُتعرَّف عليه يُحفظ (آخر 20) في `history.json`، فلا يضيع الكلام إن ذهب اللصق إلى نافذة أخرى. وبند «أعد لصق آخر نص» يعيد آخر نص.
- **تحويل تلقائي محلي:** إن انقطع الإنترنت وكان Whisper مثبّتًا، يُعاد التعرّف على نفس التسجيل محليًا مع إشعار بذلك.
- **اضغط مع الاستمرار:** وضع اختياري يسجّل فقط ما دام الاختصار مضغوطًا.
- **إيقاف تلقائي بعد صمت:** يمكن إيقاف التسجيل والتعرّف بعد عدد ثوانٍ من الصمت.
- **اختيار الميكروفون:** من قائمة فرعية، ويُحفظ بالاسم لا بالرقم فيبقى بعد إعادة التشغيل.
- **محركان:** Google عبر الإنترنت، أو Whisper محلي بالكامل بلا إنترنت.
- **ترقيم تلقائي:** يضيف علامة في نهاية الكلام وفاصلة قبل أدوات الربط، ويحوّل الأرقام إلى غربية (0-9). معطّل في الإنجليزية.
- **أوامر ترقيم منطوقة:** قل «فاصلة» أو «علامة استفهام» أو «سطر جديد»… (الجدول أدناه).
- **لصق يحترم الحافظة:** يعيد نص الحافظة القديم بعد اللصق، ولا يمسّ الصور والملفات.
- **نسخة واحدة فقط:** لا يمكن تشغيل نسختين معًا.
- **فحص التحديثات:** إشعار واحد إن وُجد إصدار أحدث على GitHub، بلا تنزيل أو تثبيت تلقائي.
- **أعطال واضحة:** إشعارات عربية بدل الفشل الصامت، والسجلّ في `%APPDATA%\AltScribo\altscribo.log`.

## التنزيل والتشغيل

نزّل الملف `AltScribo-v1.5.4-windows.zip` من صفحة [الإصدارات](https://github.com/alimwork85-web/AltScribo/releases)، وفكّ ضغطه في أي مجلد، ثم شغّل `AltScribo.exe`. ستظهر الأيقونة في شريط المهام (قد تكون داخل السهم الصغير).

للتشغيل مع Windows تلقائيًا: اختر «التشغيل مع Windows» من قائمة الأيقونة، واختره مرة أخرى للإلغاء.

## المؤشر على الشاشة

أثناء التسجيل تظهر كبسولة أسفل وسط الشاشة التي فيها نافذتك النشطة:

| الحالة | ما تراه | السلوك |
|---|---|---|
| تسجيل | نقطة حمراء تنبض + `ON` + عدّاد مثل `0:07` | يبقى ظاهرًا |
| كتابة | نقطة رمادية + «جارٍ الكتابة…» | يبقى حتى ينتهي التعرّف واللصق |
| انتهى | `OFF` | يظهر نحو 1.2 ثانية ثم يختفي |

لا يأخذ المؤشر التركيز، ولا يظهر في `Alt+Tab` أو شريط المهام، والنقر عليه يمر إلى ما تحته. لإخفائه: بند «مؤشر التسجيل على الشاشة» في القائمة.

## اضغط مع الاستمرار والإيقاف بعد صمت

- **اضغط مع الاستمرار:** فعّله من القائمة (`push_to_talk`)، فيسجّل ما دام الاختصار مضغوطًا، ويوقف عند رفع الإصبع ويُلصق.
- **الإيقاف بعد صمت:** اجعل `auto_stop_silence_seconds` أكبر من صفر (مثل `3`)، فيتوقف التسجيل ويُلصق بعد هذه المدة من الصمت. لا يبدأ العدّ قبل سماع كلام، فالصمت قبل أن تبدأ لا يقطعك. و`0` يعطّله.

## اختيار الميكروفون

قائمة الأيقونة ← «الميكروفون» ← اختر الجهاز أو «الافتراضي». يُحفظ الجهاز بالاسم (الأرقام تتغير بين الجلسات)، ويُطبَّق على التسجيل التالي، ولا يمكن تغييره أثناء التسجيل.

## سجل النصوص

كل تعرّف ناجح يُضاف إلى `%APPDATA%\AltScribo\history.json` (آخر 20 عنصرًا، كتابة ذرية، ولا يُكتب فوق ملف تالف). وبندان في القائمة:

- **أعد لصق آخر نص** — ينسخ آخر نص إلى الحافظة ويُشعرك، وتلصقه أنت بـ`Ctrl+V`. النسخ لا يعتمد على النافذة النشطة.
- **فتح سجل النصوص** — نافذة صغيرة تعرض آخر 20 نصًا. اختر نصًا واضغط **«نسخ»** أو انقر عليه نقرًا مزدوجًا لنسخ النص الكامل لا المعاينة المختصرة. لا شريط تمرير في النافذة؛ عجلة الفأرة تمرّر القائمة.

## التعرف المحلي (Whisper)

اختر «Whisper محلي بلا إنترنت» من القائمة. في أول استخدام يُنزَّل النموذج (نحو 480 ميغابايت لنموذج `small`) إلى `%APPDATA%\AltScribo\models`، ثم يعمل التعرف كاملًا على جهازك دون إنترنت ودون إرسال صوتك لأي جهة. يضع Whisper علامات الترقيم بنفسه.

- أبطأ من Google قليلًا: بضع ثوانٍ لكل جملة على المعالج.
- يمكن تغيير النموذج عبر `whisper_model`: `base` أسرع وأقل دقة، و`medium` أدق وأبطأ بكثير.
- إن لم تكن مكتبة faster-whisper مثبّتة يظهر الخيار معطّلًا بعبارة «غير مثبّت».
- إن انقطع الإنترنت أثناء العمل ووُجد Whisper، يُعاد التعرّف محليًا على نفس التسجيل مع إشعار.

## لغة التعرف على الكلام

بند «لغة الكلام: العربية / English» يبدّل لغة التعرّف بين `ar-SA` و`en-US` دون إعادة تشغيل أو تحميل نموذج. وهذا مستقل عن لغة الواجهة. في الإنجليزية لا يُطبَّق الترقيم العربي التلقائي ولا الأوامر المنطوقة العربية، ويبقى تنظيم المسافات والأرقام.

## أوامر الترقيم المنطوقة

| تقول | يُكتب |
|---|---|
| فاصلة | ، |
| فاصلة منقوطة | ؛ |
| علامة استفهام | ؟ |
| علامة تعجب | ! |
| نقطتان رأسيتان | : |
| نقطة | . (في آخر الكلام فقط، لأنها كلمة شائعة) |
| سطر جديد | سطر جديد |
| فقرة جديدة | سطر فارغ ثم سطر جديد |

يمكن إيقاف هذه الأوامر من القائمة إن كانت تتعارض مع ما تكتبه.

## الإعدادات

من قائمة الأيقونة اختر «فتح الإعدادات»، أو افتح `%APPDATA%\AltScribo\settings.json`:

| الإعداد | الوصف | الافتراضي |
|---|---|---|
| `hotkey` | الاختصار العام | `alt+f9` |
| `language` | لغة التعرف على الكلام | `ar-SA` |
| `timeout_seconds` | مهلة انتظار الخدمة بالثواني | `15` |
| `max_gain` | أقصى تضخيم للصوت الخافت | `4.0` |
| `sample_rate` | معدل أخذ العينات | `16000` |
| `engine` | محرك التعرف: `google` أو `whisper` | `google` |
| `whisper_model` | `tiny` أو `base` أو `small` أو `medium` أو `large-v3` | `small` |
| `auto_punctuation` | الترقيم التلقائي (عربي فقط) | `true` |
| `spoken_punctuation` | أوامر الترقيم المنطوقة (عربي فقط) | `true` |
| `ui_language` | لغة الواجهة: `auto` أو `ar` أو `en` | `auto` |
| `input_device` | اسم الميكروفون، و`""` = الافتراضي | `""` |
| `push_to_talk` | التسجيل ما دام الاختصار مضغوطًا | `false` |
| `auto_stop_silence_seconds` | الإيقاف بعد صمت بهذه الثواني، `0` = معطّل | `0` |
| `silence_threshold` | عتبة RMS التي تُعدّ كلامًا | `500` |
| `show_overlay` | إظهار المؤشر على الشاشة | `true` |

أعد تشغيل الأداة بعد أي تعديل يدوي على الملف (ما تغيّره من القائمة يُحفظ ويعمل فورًا). ويمكنك تغيير `language` إلى لهجة أخرى مثل `ar-EG` أو `ar-AE`.

## الخصوصية

مع محرك Google يُرسل الصوت المسجَّل إلى خدمة Google للتعرف على الكلام، ولذلك يحتاج إلى اتصال بالإنترنت. ومع محرك Whisper لا يغادر الصوت جهازك. لا تُحفظ التسجيلات؛ والنصوص المُملاة تُحفظ فقط في `history.json` المحلي (آخر 20)، وسجلّ التشغيل `altscribo.log` يحوي أحداث التشغيل والأخطاء فقط.

## التشغيل من المصدر

```bash
python -m venv venv
venv\Scripts\pip install -r requirements.txt
venv\Scripts\python main.py
```

لتفعيل التعرف المحلي ثبّت `requirements-whisper.txt` بدل `requirements.txt`. يتطلب ذلك Python من 3.12 إلى 3.14، لأن حزم ctranslate2 وonnxruntime غير متوفرة لـ Python 3.15 بعد.

## بناء ملف EXE

```bash
venv\Scripts\pyinstaller AltScribo.spec --noconfirm
```

يظهر الناتج في `dist\AltScribo\AltScribo.exe`. إن كانت faster-whisper مثبّتة في بيئة البناء يُضمَّن التعرف المحلي تلقائيًا (ويزيد حجم البرنامج)، وإلا يُبنى بمحرك Google فقط. ويحمل الملف مورد إصدار باسم الناشر ورقم الإصدار (انظر `version_info.txt`).

## بنية الكود

- `altscribo/config.py`: المسارات والإعدادات والسجلّ.
- `altscribo/recorder.py`: التسجيل واختيار الميكروفون وكشف الصمت.
- `altscribo/transcriber.py`: تحويل الصوت إلى نص بمحرك Google أو Whisper، والتحويل المحلي عند الانقطاع.
- `altscribo/punctuation.py`: الترقيم التلقائي وأوامر الترقيم المنطوقة.
- `altscribo/startup.py`: اختصار التشغيل مع Windows.
- `altscribo/menu.py`: قائمة الأيقونة المخصصة وخيط Tk.
- `altscribo/overlay.py`: المؤشر العائم لحالة التسجيل.
- `altscribo/i18n.py`: كل نص يراه المستخدم بالعربية والإنجليزية.
- `altscribo/injector.py`: اللصق عبر الحافظة مع حفظها وإعادتها.
- `altscribo/app.py`: أيقونة الشريط والاختصار والإشعارات وفحص التحديثات.

## المتطلبات

Windows 10 أو أحدث، وميكروفون، واتصال بالإنترنت (لمحرك Google، أو لتنزيل نموذج Whisper أول مرة فقط).

## المطوّر

**Ali Alhumedi** — [github.com/alimwork85-web](https://github.com/alimwork85-web) · © 2026 Ali Alhumedi

</div>
