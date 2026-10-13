import re

# أوامر ترقيم منطوقة؛ الأطول أولًا حتى لا تطغى "فاصلة" على "فاصلة منقوطة"
SPOKEN_MARKS = [
    (("فقرة جديدة", "فقره جديده"), "\n\n"),
    (("سطر جديد",), "\n"),
    (("علامة استفهام", "علامه استفهام"), "؟"),
    (("علامة تعجب", "علامه تعجب"), "!"),
    (("فاصلة منقوطة", "فاصله منقوطه"), "؛"),
    (("نقطتان رأسيتان", "نقطتين رأسيتين"), ":"),
    (("فاصلة", "فاصله"), "،"),
    (("نقطة", "نقطه"), "."),
]

# "نقطة" كلمة شائعة، فلا تُعدّ أمرًا إلا في آخر الكلام أو قبل سطر جديد
END_ONLY = {"."}

# كلمات تبدأ بها الأسئلة غالبًا (استُبعدت "ما" و"من" لأنهما تأتيان كثيرًا في غير السؤال)
QUESTION_WORDS = {
    "هل", "أين", "اين", "متى", "كيف", "لماذا", "ماذا", "كم", "أي", "اي",
    "أليس", "اليس", "ليش", "ليه", "شو", "وين", "إيش", "ايش", "ايه", "إيه", "امتى", "إمتى",
}

# أدوات ربط تسبقها فاصلة عادةً
COMMA_BEFORE = ("ولكن", "لكن", "لذلك", "لذا", "بينما", "إلا أن", "الا ان")

END_MARKS = ".؟?!:؛…\n"
ARABIC = "\u0600-\u06FF"
EASTERN_DIGITS = str.maketrans("٠١٢٣٤٥٦٧٨٩۰۱۲۳۴۵۶۷۸۹", "01234567890123456789")


def apply_spoken_marks(text):
    """ يستبدل أوامر الترقيم المنطوقة (كلمات مستقلة فقط) بعلاماتها """
    for phrases, mark in SPOKEN_MARKS:
        replacement = mark if mark.startswith("\n") else mark + " "
        for phrase in phrases:
            pattern = r"\s*(?<!\w)" + re.escape(phrase) + r"(?!\w)[ \t]*"
            if mark in END_ONLY:
                pattern += r"(?=\n|$)"
            text = re.sub(pattern, replacement, text)
    return text


def auto_punctuate(text):
    """ ترقيم تقريبي لنص بلا علامات: فواصل قبل أدوات الربط، وعلامة في النهاية """
    words = text.split()
    if not words:
        return text
    for conj in COMMA_BEFORE:
        pattern = r"(?<=[^\s،,.؟?!:؛])[ \t]+(" + re.escape(conj) + r")(?!\w)"
        text = re.sub(pattern, r"، \1", text)
    body = text.rstrip(" \t")
    if body and body[-1] not in END_MARKS:
        first = words[0]
        is_question = first in QUESTION_WORDS or first.lstrip("و") in QUESTION_WORDS
        text = body + ("؟" if is_question else ".")
    return text


def normalize(text):
    """ أرقام غربية، وعلامات عربية بجوار النص العربي، ومسافات مرتبة """
    text = text.translate(EASTERN_DIGITS)
    text = re.sub(rf"(?<=[{ARABIC}])\s*,", "،", text)
    text = re.sub(rf"(?<=[{ARABIC}])\s*\?", "؟", text)
    text = re.sub(rf"(?<=[{ARABIC}])\s*;", "؛", text)
    text = re.sub(r"[ \t]+([،,.؟?!:؛;])", r"\1", text)      # لا مسافة قبل العلامة
    text = re.sub(r"([،,])\s*([.؟?!])", r"\2", text)        # فاصلة ثم نقطة: تبقى النقطة
    text = re.sub(r"([،؛؟!])(?=[^\s\d])", r"\1 ", text)     # مسافة بعد العلامة
    text = re.sub(rf"([.:])(?=[{ARABIC}])", r"\1 ", text)
    text = re.sub(r"[ \t]{2,}", " ", text)
    text = re.sub(r"[ \t]*\n[ \t]*", "\n", text)
    return text.strip(" \t")


def process(text, spoken=True, auto=True):
    if spoken:
        text = apply_spoken_marks(text)
    if auto:
        text = auto_punctuate(text)
    return normalize(text)
