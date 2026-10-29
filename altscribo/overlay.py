import ctypes
import ctypes.wintypes
import time
import tkinter as tk

from PIL import Image, ImageDraw, ImageTk

from .config import log
from .i18n import is_rtl, t
from .menu import DARK, FONT_FAMILY, LIGHT, _is_dark_theme

GWL_EXSTYLE = -20
WS_EX_TRANSPARENT = 0x00000020
WS_EX_TOOLWINDOW = 0x00000080
WS_EX_LAYERED = 0x00080000
WS_EX_NOACTIVATE = 0x08000000
MONITOR_DEFAULTTONEAREST = 0x00000002
TRANSPARENT_KEY = "#FF00FE"
RED = "#D62B2B"
DIM_RED = "#7A1A1A"


class _MONITORINFO(ctypes.Structure):
    _fields_ = [("cbSize", ctypes.wintypes.DWORD),
                ("rcMonitor", ctypes.wintypes.RECT),
                ("rcWork", ctypes.wintypes.RECT),
                ("dwFlags", ctypes.wintypes.DWORD)]


def work_area():
    """ (يسار، أعلى، يمين، أسفل) لمنطقة عمل الشاشة التي فيها النافذة النشطة """
    user32 = ctypes.windll.user32
    try:
        monitor = user32.MonitorFromWindow(user32.GetForegroundWindow(), MONITOR_DEFAULTTONEAREST)
        info = _MONITORINFO()
        info.cbSize = ctypes.sizeof(_MONITORINFO)
        if monitor and user32.GetMonitorInfoW(monitor, ctypes.byref(info)):
            area = info.rcWork
            return area.left, area.top, area.right, area.bottom
    except Exception as e:
        log.warning("تعذّر قراءة منطقة العمل: %s", e)
    return 0, 0, user32.GetSystemMetrics(0), user32.GetSystemMetrics(1)


class Overlay:
    """ كبسولة عائمة تُظهر حالة التسجيل؛ كل عمل Tk يمر عبر خيط القائمة """

    WIDTH = 160
    HEIGHT = 40
    BOTTOM_MARGIN = 24
    PAD = 12
    DOT = 10

    def __init__(self, menu, icon_image):
        self.menu = menu
        self._icon = icon_image.resize((20, 20))
        self._icon_photo = None
        self._window = None
        self._photo = None
        self._dot = None
        self._oval = None
        self._text = None
        self._theme = None
        self._rtl = True
        self._started = 0.0
        self._blink_on = False
        self._state = None
        self._jobs = []

    # ---------- واجهة تُستدعى من أي خيط ----------
    def show_recording(self):
        self._safe(lambda: self._show("recording"))

    def show_processing(self):
        self._safe(lambda: self._show("processing"))

    def show_done(self):
        self._safe(lambda: self._show("done"))

    def hide(self):
        self._safe(self._destroy)

    def _safe(self, fn):
        def call():
            try:
                fn()
            except Exception as e:  # لا يجوز أن يُسقط المؤشر التسجيل أو اللصق
                log.warning("تعذّر رسم مؤشر التسجيل: %s", e)

        try:
            self.menu.run_on_ui(call)
        except Exception as e:
            log.warning("تعذّر طلب تحديث مؤشر التسجيل: %s", e)

    # ---------- على خيط Tk ----------
    def _show(self, state):
        if self._window is None:
            self._build()
        self._cancel_jobs()
        self._state = state
        theme = self._theme
        self._dot.itemconfigure(self._oval, fill=RED if state == "recording" else theme["muted"])
        if state == "recording":
            self._started = time.monotonic()
            self._tick()
            self._blink()
        else:
            self._text.configure(text=t("overlay_processing" if state == "processing" else "overlay_off"))
            if state == "done":
                self._jobs.append(self._window.after(1200, self._destroy))

    def _build(self):
        self._theme = DARK if _is_dark_theme() else LIGHT
        self._rtl = is_rtl()
        theme = self._theme
        window = tk.Toplevel()
        self._window = window
        window.overrideredirect(True)
        window.attributes("-topmost", True)
        window.configure(bg=TRANSPARENT_KEY)
        try:
            window.wm_attributes("-transparentcolor", TRANSPARENT_KEY)
        except tk.TclError:
            pass

        capsule = Image.new("RGB", (self.WIDTH, self.HEIGHT), TRANSPARENT_KEY)
        draw = ImageDraw.Draw(capsule)
        draw.rounded_rectangle([0, 0, self.WIDTH - 1, self.HEIGHT - 1], radius=self.HEIGHT // 2,
                               fill=theme["bg"], outline=theme["border"])
        self._photo = ImageTk.PhotoImage(capsule)
        backdrop = tk.Label(window, image=self._photo, bd=0, bg=TRANSPARENT_KEY)
        backdrop.place(x=0, y=0, relwidth=1, relheight=1)

        self._icon_photo = ImageTk.PhotoImage(self._icon)
        icon = tk.Label(window, image=self._icon_photo, bd=0, bg=theme["bg"])
        self._dot = tk.Canvas(window, width=self.DOT, height=self.DOT, bd=0,
                              highlightthickness=0, bg=theme["bg"])
        self._oval = self._dot.create_oval(0, 0, self.DOT, self.DOT, outline="", fill=theme["muted"])
        self._text = tk.Label(window, text="", bd=0, bg=theme["bg"], fg=theme["fg"],
                              font=(FONT_FAMILY, 10, "bold"))

        y_icon = (self.HEIGHT - 20) // 2
        y_dot = (self.HEIGHT - self.DOT) // 2
        y_text = (self.HEIGHT - 18) // 2
        if self._rtl:
            icon.place(x=self.WIDTH - self.PAD - 20, y=y_icon)
            self._dot.place(x=self.WIDTH - self.PAD - 20 - 8 - self.DOT, y=y_dot)
            self._text.place(x=self.WIDTH - self.PAD - 20 - 8 - self.DOT - 8, y=y_text, anchor="e")
        else:
            icon.place(x=self.PAD, y=y_icon)
            self._dot.place(x=self.PAD + 20 + 8, y=y_dot)
            self._text.place(x=self.PAD + 20 + 8 + self.DOT + 8, y=y_text, anchor="w")

        left, _top, right, bottom = work_area()
        x = left + ((right - left) - self.WIDTH) // 2
        y = bottom - self.HEIGHT - self.BOTTOM_MARGIN
        window.geometry(f"{self.WIDTH}x{self.HEIGHT}+{x}+{max(0, y)}")
        window.update_idletasks()
        self._no_activate()

    def _no_activate(self):
        """ بلا تركيز، بلا ظهور في Alt+Tab، والنقرات تمر إلى ما تحت """
        user32 = ctypes.windll.user32
        hwnd = user32.GetParent(self._window.winfo_id()) or self._window.winfo_id()
        style = user32.GetWindowLongW(hwnd, GWL_EXSTYLE)
        user32.SetWindowLongW(hwnd, GWL_EXSTYLE, style | WS_EX_NOACTIVATE | WS_EX_TOOLWINDOW
                              | WS_EX_TRANSPARENT | WS_EX_LAYERED)

    def _tick(self):
        if self._window is None or self._state != "recording":
            return
        elapsed = max(0, int(time.monotonic() - self._started))
        self._text.configure(text=f"{t('overlay_on')} {elapsed // 60}:{elapsed % 60:02d}")
        self._jobs.append(self._window.after(1000, self._tick))

    def _blink(self):
        if self._window is None or self._state != "recording":
            return
        self._blink_on = not self._blink_on
        self._dot.itemconfigure(self._oval, fill=RED if self._blink_on else DIM_RED)
        self._jobs.append(self._window.after(500, self._blink))

    def _cancel_jobs(self):
        for job in self._jobs:
            try:
                self._window.after_cancel(job)
            except Exception:
                pass
        self._jobs.clear()

    def _destroy(self):
        self._cancel_jobs()
        if self._window is not None:
            try:
                self._window.destroy()
            except tk.TclError:
                pass
            self._window = None
