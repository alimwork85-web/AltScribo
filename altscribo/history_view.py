""" نافذة سجل النصوص: آخر النصوص في قائمة، ونقرة مزدوجة أو زر «نسخ» تنسخ النص """
import threading
import tkinter as tk
import tkinter.font as tkfont

from .i18n import is_rtl, t
from .injector import copy_text
from .menu import DARK, LIGHT, FONT_FAMILY, _is_dark_theme, _rtl

_lock = threading.Lock()
_root = None      # النافذة المفتوحة حاليًا (واحدة فقط)


def _preview(item):
    """ سطر واحد مختصر من النص (بلا وقت: الأرقام تختل في السطر العربي) """
    return " ".join(str(item.get("text", "")).split())[:90]


def _fit(font, text, width):
    """ يقصّر النص حتى يلائم عرض القائمة بالبكسل — القصّ بالحروف يبتر العربية """
    if font.measure(text) <= width:
        return text
    while text and font.measure(text + "…") > width:
        text = text[:-1]
    return text + "…"


def build_window(root, items):
    """ يبني النافذة على root ويعيد (listbox, زر النسخ) — مفصولة عن Tk نفسها للاختبار """
    theme = DARK if _is_dark_theme() else LIGHT
    rtl = is_rtl()
    side = "right" if rtl else "left"
    anchor = "e" if rtl else "w"
    root.configure(bg=theme["bg"])
    root.title(t("history_title"))

    tk.Label(root, text=_rtl(t("history_title")), bg=theme["bg"], fg=theme["fg"],
             font=(FONT_FAMILY, 12, "bold"), anchor=anchor, padx=12, pady=8).pack(fill="x")

    body = tk.Frame(root, bg=theme["bg"])
    body.pack(fill="both", expand=True, padx=12)
    listbox = tk.Listbox(body, bg=theme["bg"], fg=theme["fg"], font=(FONT_FAMILY, 10),
                         selectbackground=theme["hover"], selectforeground=theme["fg"],
                         borderwidth=0, highlightthickness=0, activestyle="none",
                         justify=side)
    scroll = tk.Scrollbar(body, command=listbox.yview)
    listbox.configure(yscrollcommand=scroll.set)
    listbox.pack(side=side, fill="both", expand=True)
    scroll.pack(side="left" if rtl else "right", fill="y")

    label_font = tkfont.Font(root=root, font=(FONT_FAMILY, 10))

    def fill():
        """ يعيد تعبئة القائمة مقصوصة على عرضها الحالي بالبكسل """
        width = max(listbox.winfo_width() - 24, 60)
        listbox.delete(0, "end")
        for item in items:
            listbox.insert("end", _rtl(_fit(label_font, _preview(item), width)))

    root.update_idletasks()
    fill()
    listbox.bind("<Configure>", lambda _: fill())
    listbox.selection_set(len(items) - 1)

    status = tk.Label(root, text="", bg=theme["bg"], fg=theme["muted"],
                      font=(FONT_FAMILY, 9), anchor=anchor, padx=12)
    status.pack(fill="x")

    def copy_selected(_=None):
        """ ينسخ النص المحدد كما هو، لا المعاينة المختصرة """
        selected = listbox.curselection()
        if not selected:
            return
        try:
            copy_text(items[selected[0]]["text"])
        except Exception:
            status.configure(text=_rtl(t("paste_failed")))
            return
        status.configure(text=_rtl(t("copied")))

    button = tk.Button(root, text=t("copy"), command=copy_selected, bg=theme["hover"],
                       fg=theme["fg"], activebackground=theme["border"], activeforeground=theme["fg"],
                       font=(FONT_FAMILY, 10), borderwidth=0, padx=18, pady=4, cursor="hand2")
    button.pack(pady=(0, 10))
    listbox.bind("<Double-Button-1>", copy_selected)
    return listbox, button


def show(items):
    """ يفتح النافذة في خيط منفصل، أو يرفع المفتوحة. يعيد False إن كان السجل فارغًا """
    if not items:
        return False
    global _root
    with _lock:
        if _root is not None:
            try:
                _root.lift()
                _root.focus_force()
                return True
            except tk.TclError:
                _root = None
    threading.Thread(target=_run, args=(list(items),), daemon=True).start()
    return True


def _run(items):
    global _root
    root = tk.Tk()
    _root = root
    root.geometry("560x520")
    root.minsize(420, 320)
    root.attributes("-topmost", True)
    build_window(root, items)

    def on_close():
        global _root
        _root = None
        root.destroy()

    root.protocol("WM_DELETE_WINDOW", on_close)
    root.bind("<Escape>", lambda _: on_close())
    root.mainloop()
