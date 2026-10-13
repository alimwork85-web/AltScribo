import threading

import sounddevice as sd


class Recorder:
    """ تسجيل من الميكروفون؛ start() يفتح التدفق وstop() يُرجع المقاطع المسجلة """

    def __init__(self, sample_rate):
        self.sample_rate = sample_rate
        self.is_recording = False
        self._frames = []
        self._stream = None
        self.lock = threading.Lock()

    def _callback(self, indata, frames, time_info, status):
        if self.is_recording:
            self._frames.append(indata.copy())

    def start(self):
        """ يرمي استثناءً إن فشل فتح الميكروفون """
        self._frames = []
        stream = sd.InputStream(
            samplerate=self.sample_rate, channels=1, dtype="int16", callback=self._callback
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
