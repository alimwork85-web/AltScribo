import io

import numpy as np
import scipy.io.wavfile as wav
import speech_recognition as sr


class NoSpeech(Exception):
    pass


class NetworkError(Exception):
    pass


class Transcriber:
    def __init__(self, sample_rate, language, timeout, max_gain):
        self.sample_rate = sample_rate
        self.language = language
        self.max_gain = max_gain
        self.recognizer = sr.Recognizer()
        self.recognizer.operation_timeout = timeout

    def transcribe(self, frames):
        """ يحوّل المقاطع إلى نص؛ يرمي NoSpeech أو NetworkError """
        if not frames:
            raise NoSpeech("لم يتم تسجيل أي صوت")

        recording = np.concatenate(frames, axis=0)

        # مضاعفة حساسية الصوت الخافت
        max_val = np.max(np.abs(recording))
        if max_val > 0:
            gain = min(32767.0 / max_val, self.max_gain)
            recording = (recording * gain).astype(np.int16)

        wav_io = io.BytesIO()
        wav.write(wav_io, self.sample_rate, recording)
        wav_io.seek(0)

        with sr.AudioFile(wav_io) as source:
            audio = self.recognizer.record(source)
        try:
            text = self.recognizer.recognize_google(audio, language=self.language)
        except sr.UnknownValueError:
            raise NoSpeech("لم يتم التعرف على كلام واضح")
        except sr.RequestError as e:
            raise NetworkError(str(e))
        text = (text or "").strip()
        if not text:
            raise NoSpeech("لم يتم التعرف على كلام واضح")
        return text + " "
