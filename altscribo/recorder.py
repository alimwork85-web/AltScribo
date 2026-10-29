import threading

import sounddevice as sd

from .config import log


def input_devices():
    """ أسماء أجهزة الإدخال المتاحة بلا تكرار """
    try:
        devices = sd.query_devices()
    except Exception as e:
        log.warning("تعذّر قراءة أجهزة الصوت: %s", e)
        return []
    seen, names = set(), []
    for dev in devices:
        name = dev.get("name", "")
        if name and dev.get("max_input_channels", 0) > 0 and name not in seen:
            seen.add(name)
            names.append(name)
    return names


class Recorder:
    """ تسجيل من الميكروفون؛ start() يفتح التدفق وstop() يُرجع المقاطع المسجلة """

    def __init__(self, sample_rate):
        self.sample_rate = sample_rate
        self.input_device = ""  # اسم جهاز الإدخال، و"" تعني الافتراضي
        self.is_recording = False
        self._frames = []
        self._stream = None
        self.lock = threading.Lock()

    def _device_index(self):
        """ رقم الجهاز المطابق للاسم، أو None للافتراضي (الأرقام تتغير بين الجلسات) """
        if not self.input_device:
            return None
        try:
            for index, dev in enumerate(sd.query_devices()):
                if dev.get("name") == self.input_device and dev.get("max_input_channels", 0) > 0:
                    return index
        except Exception as e:
            log.warning("تعذّر قراءة أجهزة الصوت: %s", e)
        log.warning("الميكروفون %s غير موجود، يُستخدم الافتراضي", self.input_device)
        return None

    def _callback(self, indata, frames, time_info, status):
        if self.is_recording:
            self._frames.append(indata.copy())

    def start(self):
        """ يرمي استثناءً إن فشل فتح الميكروفون """
        self._frames = []
        stream = sd.InputStream(
            samplerate=self.sample_rate, channels=1, dtype="int16",
            device=self._device_index(), callback=self._callback
        )
        stream.start()
        self._stream = stream
        self.is_recording = True

    def stop(self):
        self.is_recording = False
        if self._stream is not None:
            try:
                self._stream.stop()
                self._stream.close()
            finally:
                self._stream = None
        frames, self._frames = self._frames, []
        return frames
