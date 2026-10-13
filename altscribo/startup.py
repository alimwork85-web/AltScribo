import os
import subprocess
import sys

from .config import APP_NAME, ICON_PATH, log

STARTUP_DIR = os.path.join(
    os.environ.get("APPDATA") or os.path.expanduser("~"),
    "Microsoft", "Windows", "Start Menu", "Programs", "Startup",
)
SHORTCUT_PATH = os.path.join(STARTUP_DIR, f"{APP_NAME}.lnk")

# المسارات تُمرَّر عبر متغيرات البيئة لتجنّب مشاكل الاقتباس والأحرف العربية
_PS_CREATE = (
    "$s = (New-Object -ComObject WScript.Shell).CreateShortcut($env:AS_LNK);"
    "$s.TargetPath = $env:AS_TARGET;"
    "$s.Arguments = $env:AS_ARGS;"
    "$s.WorkingDirectory = $env:AS_DIR;"
    "$s.IconLocation = $env:AS_ICON;"
    "$s.Description = 'AltScribo';"
    "$s.Save()"
)


def _launch_command():
    """ (الهدف، الوسائط، مجلد العمل) لتشغيل الأداة بلا نافذة طرفية """
    if getattr(sys, "frozen", False):
        return sys.executable, "", os.path.dirname(sys.executable)
    exe_dir = os.path.dirname(sys.executable)
    pythonw = os.path.join(exe_dir, "pythonw.exe")
    if not os.path.exists(pythonw):
        pythonw = sys.executable
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    return pythonw, f'"{os.path.join(root, "main.py")}"', root


def is_enabled():
    return os.path.exists(SHORTCUT_PATH)


def enable():
    target, args, workdir = _launch_command()
    icon = ICON_PATH if os.path.exists(ICON_PATH) else target
    env = dict(os.environ, AS_LNK=SHORTCUT_PATH, AS_TARGET=target, AS_ARGS=args,
               AS_DIR=workdir, AS_ICON=icon)
    os.makedirs(STARTUP_DIR, exist_ok=True)
    result = subprocess.run(
        ["powershell", "-NoProfile", "-NonInteractive", "-Command", _PS_CREATE],
        env=env, capture_output=True, text=True, timeout=20,
        creationflags=subprocess.CREATE_NO_WINDOW,
    )
    if result.returncode != 0 or not is_enabled():
        raise OSError(result.stderr.strip() or "تعذّر إنشاء الاختصار")
    log.info("أُضيف اختصار التشغيل التلقائي: %s", SHORTCUT_PATH)


def disable():
    if is_enabled():
        os.remove(SHORTCUT_PATH)
        log.info("أُزيل اختصار التشغيل التلقائي")
