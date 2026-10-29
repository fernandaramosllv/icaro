"""Ciclo de vida da escuta sem microfone ou modelo reais."""
from pathlib import Path
import tempfile
import types
import unittest
from unittest.mock import MagicMock, patch

from icaro.voice import listen


class VoiceTests(unittest.TestCase):
    def test_missing_model(self):
        with self.assertRaisesRegex(RuntimeError, "Modelo Vosk"):
            listen(Path("modelo-inexistente"), None, lambda text: False)

    def exercise(self, side_effect=None, result="sair", overflow=False, resume=False):
        with tempfile.TemporaryDirectory() as folder:
            model = Path(folder)
            (model / "am").mkdir()
            (model / "am/final.mdl").touch()
            sd = MagicMock()
            sd.PortAudioError = type("PortAudioError", (Exception,), {})
            sd.query_devices.return_value = {"default_samplerate": 48000}
            stream = MagicMock()
            def open_stream(**kwargs):
                kwargs["callback"](b"audio", 1, None, overflow)
                stream.__enter__.return_value.start.side_effect = lambda: kwargs["callback"](b"audio", 1, None, False)
                return stream
            sd.RawInputStream.side_effect = open_stream
            recognizer = MagicMock()
            recognizer.AcceptWaveform.return_value = True
            recognizer.Result.return_value = '{"text": "' + result + '"}'
            vosk = types.SimpleNamespace(Model=MagicMock(), SetLogLevel=MagicMock(),
                                         KaldiRecognizer=MagicMock(return_value=recognizer))
            handler = MagicMock(return_value=False, side_effect=[True, False] if resume else side_effect)
            with patch("icaro.voice.audio_module", return_value=sd), patch.dict("sys.modules", vosk=vosk):
                if side_effect is not None:
                    with self.assertRaises(type(side_effect)):
                        listen(model, 2, handler)
                elif overflow:
                    with self.assertRaisesRegex(RuntimeError, "perda de áudio"):
                        listen(model, 2, handler)
                else:
                    listen(model, 2, handler)
                    if resume:
                        self.assertEqual(handler.call_count, 2)
                        recognizer.Reset.assert_called_once()
                        stream.__enter__.return_value.start.assert_called_once()
                    else:
                        handler.assert_called_once_with(result)
                    self.assertEqual(stream.__enter__.return_value.stop.call_count, handler.call_count)
            stream.__exit__.assert_called_once()
            return handler

    def test_legacy_model_layout(self):
        with tempfile.TemporaryDirectory() as folder:
            model = Path(folder)
            (model / "final.mdl").touch()
            with patch("icaro.voice.audio_module", side_effect=RuntimeError("audio simulado")):
                with self.assertRaisesRegex(RuntimeError, "audio simulado"):
                    listen(model, None, lambda text: False)

    def test_exit_releases_stream(self):
        self.exercise()

    def test_resume_after_response(self):
        self.exercise(resume=True)

    def test_interrupt_releases_stream(self):
        self.exercise(KeyboardInterrupt())

    def test_handler_failure_releases_stream(self):
        self.exercise(RuntimeError("falhou"))

    def test_overflow_does_not_execute(self):
        handler = self.exercise(overflow=True)
        handler.assert_not_called()


if __name__ == "__main__":
    unittest.main()
