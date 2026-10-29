"""Voz neural simulada: sem rede ou reprodução real."""
from array import array
import asyncio
import contextlib
import io
import unittest
from unittest.mock import MagicMock, patch

from icaro.speaker import create_speaker, _synthesize, _play_audio, VOICE


class SpeakerTests(unittest.TestCase):
    def setUp(self):
        self.edge = MagicMock()
        async def stream():
            yield {"type": "WordBoundary", "text": "Olá"}
            yield {"type": "audio", "data": b"mp3"}
        self.edge.Communicate.return_value.stream = stream
        self.decoder = MagicMock()
        self.decoder.decode.return_value.samples = array("h", [0] * 20)
        self.sd = MagicMock()
        self.sd.query_devices.return_value = {"default_samplerate": 48000}
        deps = patch("icaro.speaker._load_dependencies", return_value=(self.edge, self.decoder, self.sd))
        deps.start()
        self.addCleanup(deps.stop)
        output = contextlib.redirect_stdout(io.StringIO())
        self.output = output.__enter__()
        self.addCleanup(output.__exit__, None, None, None)

    def test_male_voice_and_repeated_responses(self):
        speak = create_speaker()
        speak("Olá.")
        speak("<texto> & pesquisa")
        self.assertEqual(self.edge.Communicate.call_count, 2)
        self.edge.Communicate.assert_called_with(
            "<texto> & pesquisa", VOICE, rate="-5%", connect_timeout=10, receive_timeout=15,
        )
        self.assertEqual(VOICE, "pt-BR-AntonioNeural")
        self.assertEqual(self.sd.RawOutputStream.call_count, 2)
        self.assertIn("online", self.output.getvalue())

    @patch("icaro.speaker._load_dependencies", side_effect=ImportError("ausente"))
    def test_missing_dependencies(self, dependencies):
        self.assertIsNone(create_speaker())

    def test_empty_audio(self):
        async def stream():
            yield {"type": "WordBoundary"}
        self.edge.Communicate.return_value.stream = stream
        with self.assertRaisesRegex(RuntimeError, "não retornou áudio"):
            asyncio.run(_synthesize("Olá", self.edge))

    @patch("icaro.speaker.MAX_AUDIO_BYTES", 2)
    def test_audio_limit(self):
        with self.assertRaisesRegex(RuntimeError, "limite"):
            asyncio.run(_synthesize("Olá", self.edge))

    def test_network_failure_disables_speech(self):
        self.edge.Communicate.side_effect = OSError("sem conexão")
        speak = create_speaker()
        speak("Olá")
        speak("Outra resposta")
        self.edge.Communicate.assert_called_once()
        self.sd.RawOutputStream.assert_not_called()
        self.assertIn("sem conexão", self.output.getvalue())

    def test_output_failure_closes_stream(self):
        self.sd.RawOutputStream.return_value.__enter__.return_value.write.side_effect = OSError("sem saída")
        speak = create_speaker()
        speak("Olá")
        self.sd.RawOutputStream.return_value.__exit__.assert_called_once()
        self.assertIn("sem saída", self.output.getvalue())

    def test_keyboard_interrupt_closes_stream(self):
        self.sd.RawOutputStream.return_value.__enter__.return_value.write.side_effect = KeyboardInterrupt()
        with self.assertRaises(KeyboardInterrupt):
            _play_audio(b"mp3", self.decoder, self.sd)
        self.sd.RawOutputStream.return_value.__exit__.assert_called_once()

    @patch("icaro.speaker.SYNTHESIS_TIMEOUT", 0.01)
    def test_timeout_keeps_terminal_responses(self):
        async def slow_stream():
            await asyncio.sleep(1)
            yield {"type": "audio", "data": b"mp3"}
        self.edge.Communicate.return_value.stream = slow_stream
        create_speaker()("Olá")
        self.sd.RawOutputStream.assert_not_called()
        self.assertIn("TimeoutError", self.output.getvalue())

    def test_long_response_does_not_use_network(self):
        create_speaker()("a" * 4001)
        self.edge.Communicate.assert_not_called()

    def test_blank_response_does_not_use_network(self):
        create_speaker()(" ")
        self.edge.Communicate.assert_not_called()


if __name__ == "__main__":
    unittest.main()
