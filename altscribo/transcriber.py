import io
import threading

import numpy as np
import scipy.io.wavfile as wav
import speech_recognition as sr

from . import punctuation
from .config import MODELS_DIR, log

# نص تمهيدي عربي مُرقَّم يشجّع Whisper على وضع علامات الترقيم
WHISPER_PROMPT = "مرحبًا، كيف حالك؟ هذا نص عربي مكتوب بعلامات ترقيم صحيحة."


class NoSpeech(Exception):
    pass


class NetworkError(Exception):
    pass


class EngineError(Exception):
    pass


def whisper_available():
    try:
        import faster_whisper  # noqa: F401
        return True
    except Exception:
        return False


class GoogleEngine:
    punctuated = False

    def __init__(self, sample_rate, language, timeout):
        self.sample_rate = sample_rate
        self.language = language
        self.recognizer = sr.Recognizer()
        self.recognizer.operation_timeout = timeout

    def transcribe(self, recording):
        wav_io = io.BytesIO()
        wav.write(wav_io, self.sample_rate, recording)
        wav_io.seek(0)
        with sr.AudioFile(wav_io) as source:
            audio = self.recognizer.record(source)
        try:
            return self.recognizer.recognize_google(audio, language=self.language)
        except sr.UnknownValueError:
            raise NoSpeech("لم يتم التعرف على كلام واضح")
        except sr.RequestError as e:
            raise NetworkError(str(e))


class WhisperEngine:
    """ تعرّف محلي بلا إنترنت؛ يُنزَّل النموذج مرة واحدة ثم يعمل دون اتصال """
    punctuated = True

    def __init__(self, sample_rate, language, model_name, notify):
        self.sample_rate = sample_rate
        self.language = language.split("-")[0]
        self.model_name = model_name
        self.notify = notify
        self._model = None
        self._lock = threading.Lock()

    def load(self):
        with self._lock:
            if self._model is not None:
                return self._model
            try:
                from faster_whisper import WhisperModel
            except Exception as e:
                raise EngineError(f"مكتبة faster-whisper غير مثبّتة: {e}")
            kwargs = dict(device="cpu", compute_type="int8", download_root=MODELS_DIR)
            try:
                self._model = WhisperModel(self.model_name, local_files_only=True, **kwargs)
            except Exception:
                self.notify(f"جارٍ تنزيل نموذج Whisper ({self.model_name}) لأول مرة، قد يستغرق دقائق")
                try:
                    self._model = WhisperModel(self.model_name, **kwargs)
                except Exception as e:
                    raise EngineError(f"تعذّر تحميل نموذج Whisper: {e}")
                self.notify("اكتمل تنزيل نموذج Whisper، صار التعرف يعمل بلا إنترنت")
            log.info("حُمّل نموذج Whisper: %s", self.model_name)
            return self._model

    def transcribe(self, recording):
        model = self.load()
        audio = recording.astype(np.float32).flatten() / 32768.0
        segments, _ = model.transcribe(
            audio, language=self.language, beam_size=5, vad_filter=True,
            initial_prompt=WHISPER_PROMPT, condition_on_previous_text=False,
        )
        return " ".join(s.text.strip() for s in segments)


class Transcriber:
    def __init__(self, settings, notify):
        self.settings = settings
        self.max_gain = float(settings["max_gain"])
        self.google = GoogleEngine(settings["sample_rate"], settings["language"], settings["timeout_seconds"])
        self.whisper = WhisperEngine(settings["sample_rate"], settings["language"],
                                     settings["whisper_model"], notify)

    @property
    def engine(self):
        return self.whisper if self.settings["engine"] == "whisper" else self.google

    def preload(self):
        """ يحمّل نموذج Whisper في الخلفية حتى لا ينتظر أول إملاء """
        if self.engine is self.whisper:
            threading.Thread(target=self._preload, daemon=True).start()

    def _preload(self):
        try:
            self.whisper.load()
        except EngineError as e:
            log.error("%s", e)
            self.whisper.notify("تعذّر تحميل نموذج Whisper، راجع السجلّ")

    def transcribe(self, frames):
        """ يحوّل المقاطع إلى نص؛ يرمي NoSpeech أو NetworkError أو EngineError """
        if not frames:
            raise NoSpeech("لم يتم تسجيل أي صوت")

        recording = np.concatenate(frames, axis=0)

        # مضاعفة حساسية الصوت الخافت
        max_val = np.max(np.abs(recording))
        if max_val > 0:
            gain = min(32767.0 / max_val, self.max_gain)
            recording = (recording * gain).astype(np.int16)

        engine = self.engine
        text = (engine.transcribe(recording) or "").strip()
        if not text:
            raise NoSpeech("لم يتم التعرف على كلام واضح")
        text = punctuation.process(
            text,
            spoken=self.settings["spoken_punctuation"],
            auto=self.settings["auto_punctuation"] and not engine.punctuated,
        )
        return text if text.endswith("\n") else text + " "
