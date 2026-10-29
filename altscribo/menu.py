import ctypes
import queue
import re
import threading
import tkinter as tk

from .config import log

FONT_FAMILY = "Tahoma"

LIGHT = {"bg": "#FFFFFF", "fg": "#1B2A2F", "muted": "#6B7A80", "hover": "#E3F1F4",
         "border": "#C9D6DA", "sep": "#E4EAEC"}
DARK = {"bg": "#25292C", "fg": "#F1F5F6", "muted": "#9AA8AE", "hover": "#34505A",
        "border": "#475258", "sep": "#394146"}


def _rtl(label):
    """ Tk يرسم النص باتجاه أساسي من اليسار؛ تضمين RLE يصحّح ترتيب النص العربي المختلط """
    if re.search("[\u0600-\u06FF]", label):
        return "\u202b" + label + "\u202c"
    return label


def _is_dark_theme():
    try:
        import winreg
        key = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            r"Software\Microsoft\Windows\CurrentVersion\Themes\Personalize")
        return winreg.QueryValueEx(key, "AppsUseLightTheme")[0] == 0
    except Exception:
        return False


class TrayMenu:
    """ قائمة منبثقة مخصصة بخط أكبر وتخطيط من اليمين إلى اليسار (أو العكس للإنجليزية).
    تعمل في خيط Tk خاص؛ show(items) آمنة للاستدعاء من أي خيط.
    items: قائمة عناصر (label, callback, enabled[, checked]) أو None للفاصل. """

    WIDTH = 280
    ROW_H = 32
    PAD = 4

    def __init__(self):
        self._requests = queue.Queue()
        self._root = None
        self._popup = None
        self._sub = None
        self._ready = threading.Event()
        threading.Thread(target=self._loop, daemon=True).start()
        self._ready.wait(5)

    def show(self, items, rtl=True):
        self._requests.put((items, rtl))

    def run_on_ui(self, fn):
        """ ينفّذ دالة على خيط Tk؛ Tk لا يقبل الاستدعاء من خيوط أخرى """
        self._requests.put(fn)

    # ---------- خيط Tk ----------
    def _loop(self):
        self._root = tk.Tk()
        self._root.withdraw()
        self._ready.set()
        self._poll()
        self._root.mainloop()

    def _poll(self):
        try:
            while True:
                request = self._requests.get_nowait()
                try:
                    if callable(request):
                        request()
                    else:
                        self._open(*request)
                except Exception:
                    log.warning("فشل تحديث واجهة القائمة", exc_info=True)
        except queue.Empty:
            pass
        self._root.after(40, self._poll)

    def _close(self, *_):
        for attr in ("_sub", "_popup"):
            window = getattr(self, attr)
            if window is not None:
                try:
                    window.destroy()
                except tk.TclError:
                    pass
                setattr(self, attr, None)

    def _open(self, items, rtl):
        self._close()
        theme = DARK if _is_dark_theme() else LIGHT
        popup = tk.Toplevel(self._root)
        self._popup = popup
        popup.overrideredirect(True)
        popup.attributes("-topmost", True)
        popup.configure(bg=theme["border"])

        body = tk.Frame(popup, bg=theme["bg"])
        body.pack(padx=1, pady=1, fill="both")
        tk.Frame(body, bg=theme["bg"], height=self.PAD).pack(fill="x")

        rows = 0
        for item in items:
            if item is None:
                tk.Frame(body, bg=theme["sep"], height=1).pack(fill="x", padx=12, pady=3)
                continue
            label, callback, enabled = item[:3]
            checked = item[3] if len(item) > 3 else None
            rows += 1
            self._row(body, theme, rtl, label, callback, enabled, checked)
        tk.Frame(body, bg=theme["bg"], height=self.PAD).pack(fill="x")

        popup.update_idletasks()
        width, height = self.WIDTH, popup.winfo_reqheight()
        x, y = popup.winfo_pointerxy()
        sw, sh = popup.winfo_screenwidth(), popup.winfo_screenheight()
        x = max(8, min(x - width // 2, sw - width - 8))
        y = y - height - 12
        if y < 8:
            y = min(popup.winfo_pointery() + 12, sh - height - 8)
        popup.geometry(f"{width}x{height}+{x}+{y}")

        popup.bind("<Escape>", self._close)
        popup.bind("<FocusOut>", lambda e: popup.after(80, self._close_if_unfocused))
        popup.focus_force()

    def _open_sub(self, row, theme, rtl, items):
        """ قائمة فرعية بجانب الصف: يسارًا في RTL ويمينًا في LTR """
        if self._sub is not None:
            try:
                self._sub.destroy()
            except tk.TclError:
                pass
            self._sub = None
        sub = tk.Toplevel(self._root)
        self._sub = sub
        sub.overrideredirect(True)
        sub.attributes("-topmost", True)
        sub.configure(bg=theme["border"])
        body = tk.Frame(sub, bg=theme["bg"])
        body.pack(padx=1, pady=1, fill="both")
        tk.Frame(body, bg=theme["bg"], height=self.PAD).pack(fill="x")
        for item in items:
            if item is None:
                tk.Frame(body, bg=theme["sep"], height=1).pack(fill="x", padx=12, pady=3)
                continue
            label, callback, enabled = item[:3]
            checked = item[3] if len(item) > 3 else None
            self._row(body, theme, rtl, label, callback, enabled, checked)
        tk.Frame(body, bg=theme["bg"], height=self.PAD).pack(fill="x")

        sub.update_idletasks()
        width, height = self.WIDTH, sub.winfo_reqheight()
        rx, ry = row.winfo_rootx(), row.winfo_rooty()
        x = rx - width if rtl else rx + row.winfo_width()
        x = max(8, min(x, sub.winfo_screenwidth() - width - 8))
        sub.geometry(f"{width}x{height}+{x}+{max(8, ry - self.PAD)}")
        sub.bind("<Escape>", self._close)

    def _close_if_unfocused(self):
        if self._popup is None:
            return
        try:
            if self._popup.focus_displayof() is None:
                self._close()
        except tk.TclError:
            self._popup = None

    def _row(self, parent, theme, rtl, label, callback, enabled, checked=None):
        side, anchor = ("right", "e") if rtl else ("left", "w")
        fg = theme["fg"] if enabled else theme["muted"]
        font = (FONT_FAMILY, 9, "bold") if callback is None and not enabled else (FONT_FAMILY, 10)
        row = tk.Frame(parent, bg=theme["bg"], height=self.ROW_H)
        row.pack(fill="x", padx=self.PAD)
        row.pack_propagate(False)
        labels = []
        if checked is not None:
            mark = tk.Label(row, text="✓" if checked else "", bg=theme["bg"], fg=fg,
                            font=(FONT_FAMILY, 10, "bold"), width=2, anchor=anchor)
            mark.pack(side=side, fill="y", padx=(0, 8) if rtl else (8, 0))
            labels.append(mark)
        text = tk.Label(row, text=_rtl(label), bg=theme["bg"], fg=fg, font=font, anchor=anchor,
                        justify=side, padx=12 if checked is None else 4)
        text.pack(side=side, fill="both", expand=True)
        labels.append(text)
        if isinstance(callback, (list, tuple)):
            arrow = tk.Label(row, text="\u25c2" if rtl else "\u25b8", bg=theme["bg"], fg=fg,
                             font=(FONT_FAMILY, 9), padx=8)
            arrow.pack(side="left" if rtl else "right", fill="y")
            labels.append(arrow)
        if not enabled:
            return

        def paint(color):
            row.configure(bg=color)
            for w in labels:
                w.configure(bg=color)

        def enter(_):
            paint(theme["hover"])

        def leave(_):
            paint(theme["bg"])

        def click(_):
            if isinstance(callback, (list, tuple)):
                self._open_sub(row, theme, rtl, callback)
                return
            self._close()
            threading.Thread(target=callback, daemon=True).start()

        for w in (row, *labels):
            w.bind("<Enter>", enter)
            w.bind("<Leave>", leave)
            w.bind("<Button-1>", click)
            w.configure(cursor="hand2")
