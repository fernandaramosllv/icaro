"""Ponto de entrada com I/O e áudio simulados."""
import contextlib
import io
import sys
import unittest
from unittest.mock import patch
import main


class CliTests(unittest.TestCase):
    def invoke(self, args, **kwargs):
        output = io.StringIO()
        with patch.object(sys, "argv", ["main.py", *args]), contextlib.redirect_stdout(output):
            code = main.main()
        return code, output.getvalue()

    @patch("builtins.input", side_effect=["ajuda", "desconhecido", "sair"])
    def test_text(self, input_mock):
        code, output = self.invoke(["--text"])
        self.assertEqual(code, 0)
        self.assertIn("Icaro encerrado", output)

    @patch("builtins.input", side_effect=EOFError)
    def test_eof(self, input_mock):
        self.assertEqual(self.invoke(["--text"])[0], 0)

    @patch("builtins.input", side_effect=KeyboardInterrupt)
    def test_ctrl_c(self, input_mock):
        self.assertEqual(self.invoke(["--text"])[0], 0)

    def test_missing_explicit_config(self):
        code, output = self.invoke(["--text", "--config", "config.inexistente.local.json"])
        self.assertEqual(code, 1)
        self.assertIn("Configuração", output)

    @patch("icaro.voice.list_devices")
    def test_list_devices(self, devices):
        self.assertEqual(self.invoke(["--list-devices"])[0], 0)
        devices.assert_called_once()

    @patch("main.create_speaker", return_value=None)
    @patch("icaro.voice.listen")
    def test_voice_arguments(self, listen, speaker):
        self.assertEqual(self.invoke(["--device", "2"])[0], 0)
        path, device, handler = listen.call_args.args
        self.assertEqual(path, main.ROOT / "models/vosk-model-small-pt-0.3")
        self.assertEqual(device, 2)
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertFalse(handler("sair"))

    @patch("main.create_speaker")
    @patch("icaro.voice.listen")
    def test_mute_skips_speech(self, listen, speaker):
        self.assertEqual(self.invoke(["--mute"])[0], 0)
        speaker.assert_not_called()

    @patch("main.create_speaker", return_value=None)
    @patch("icaro.voice.listen", side_effect=RuntimeError("modelo ausente"))
    def test_voice_error(self, listen, speaker):
        code, output = self.invoke([])
        self.assertEqual(code, 1)
        self.assertIn("modelo ausente", output)


if __name__ == "__main__":
    unittest.main()
