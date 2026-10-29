"""Testes sem abrir aplicativos ou páginas reais."""
import contextlib
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from icaro.commands import parse, normalize
from icaro.config import load_config
from icaro.navigation import validate_url, search_url, open_url
from icaro.apps import launch_app, resolve_app
from icaro.assistant import handle


class CommandsTests(unittest.TestCase):
    def test_portuguese(self):
        for phrase in ("ABRIR calculadora", "  abrir   bloco de notas ", "acessar YouTube"):
            with self.subTest(phrase=phrase):
                self.assertEqual(parse(phrase).action, "open")
        self.assertEqual(normalize("ÍCARO EXPLORÁDOR"), "icaro explorador")
        self.assertEqual(parse("pesquisar previsão do tempo em Fortaleza").target,
                         "previsão do tempo em Fortaleza")

    def test_exit_and_help(self):
        for phrase in ("sair", "ENCERRAR ÍCARO", "tchau"):
            self.assertEqual(parse(phrase).action, "exit")
        self.assertEqual(parse("ajuda").action, "help")

    def test_unknown(self):
        for phrase in ("", "abrir", "pesquisar", "abra calculadora", "execute calc.exe", "sair agora"):
            with self.subTest(phrase=phrase):
                self.assertEqual(parse(phrase).action, "unknown")


class NavigationTests(unittest.TestCase):
    def test_valid(self):
        for address, expected in (("github.com", "https://github.com"),
                                  ("https://example.com/a?q=1#x", "https://example.com/a?q=1#x"),
                                  ("http://127.0.0.1:8000", "http://127.0.0.1:8000"),
                                  ("https://[::1]/", "https://[::1]/"),
                                  ("https://ação.com", "https://xn--ao-siap.com")):
            with self.subTest(address=address):
                self.assertEqual(validate_url(address), expected)

    def test_invalid(self):
        for address in ("", "youtube", "javaScript:alert(1)", "file:///C:/Windows", "ftp://host.com",
                        "https://user:pass@example.com", "https://example.com:99999",
                        "https://bad_host.com", "https://-bad.com", "https://example.com/a b",
                        "https://example.com\n", "https://", "https://[bad", "999.999.999.999",
                        "https://example.com\\@evil.com", "https://.com"):
            with self.subTest(address=address):
                with self.assertRaises(ValueError):
                    validate_url(address)

    def test_search_round_trip(self):
        from urllib.parse import parse_qs, urlsplit
        text = "previsão em Fortaleza & café + #?"
        url = search_url(text)
        self.assertEqual(parse_qs(urlsplit(url).query)["q"], [text])
        self.assertIn("%26", url)
        with self.assertRaises(ValueError):
            search_url(" ")

    @patch("icaro.navigation.webbrowser.open", return_value=True)
    def test_open(self, browser):
        open_url("github.com")
        browser.assert_called_once_with("https://github.com", new=2)

    @patch("icaro.navigation.webbrowser.open", return_value=False)
    def test_browser_failure(self, browser):
        with self.assertRaises(OSError):
            open_url("github.com")

    @patch("icaro.navigation.webbrowser.open")
    def test_invalid_never_opens(self, browser):
        with self.assertRaises(ValueError):
            open_url("file:///test")
        browser.assert_not_called()


class ConfigTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name) / "config.local.json"

    def write(self, data):
        self.path.write_text(json.dumps(data), encoding="utf-8")

    def test_defaults_are_independent(self):
        first = load_config(self.path)
        first["sites"].clear()
        self.assertIn("youtube", load_config(self.path)["sites"])

    def test_missing_explicit(self):
        with self.assertRaises(ValueError):
            load_config(self.path, required=True)

    def test_valid_and_spaces(self):
        exe = str(Path(self.temp.name) / "Meu Editor" / "editor.exe")
        self.write({"sites": {"Notícias": "example.com"}, "apps": {"Editor": exe},
                    "voice": {"device": 2}})
        config = load_config(self.path)
        self.assertEqual(config["sites"]["noticias"], "https://example.com")
        self.assertEqual(config["apps"]["editor"], exe)
        self.assertEqual(config["voice"]["device"], 2)

    def test_bad_configs(self):
        for data in ([], {"unknown": {}}, {"apps": []}, {"voice": {"device": True}},
                     {"voice": {"device": -1}}, {"voice": {"device": ""}},
                     {"voice": {"model_path": 1}}, {"voice": {"sample_rate": 1}},
                     {"apps": {"a": "relative.exe"}}, {"apps": {"a": "C:/x.cmd"}},
                     {"sites": {"a": "file:///x"}}, {"sites": {"": "example.com"}},
                     {"sites": {"café": "a.com", "cafe": "b.com"}},
                     {"sites": {"calculadora": "example.com"}},
                     {"apps": {"navegador": str(Path(self.temp.name) / "x.exe")}}):
            with self.subTest(data=data):
                self.write(data)
                with self.assertRaises(ValueError):
                    load_config(self.path)

    def test_malformed_and_encoding(self):
        for content in ('{"sites":', '{"sites": NaN}'):
            self.path.write_text(content, encoding="utf-8")
            with self.assertRaises(ValueError):
                load_config(self.path)
        self.path.write_bytes(b"\xff")
        with self.assertRaises(ValueError):
            load_config(self.path)


class AppsTests(unittest.TestCase):
    @patch("icaro.apps.subprocess.Popen")
    def test_path_with_spaces(self, popen):
        with tempfile.TemporaryDirectory() as folder:
            exe = Path(folder) / "Meu Editor" / "editor.exe"
            exe.parent.mkdir()
            exe.touch()
            self.assertEqual(launch_app("editor", {"editor": str(exe)}), exe)
            popen.assert_called_once_with([str(exe)], shell=False)

    @patch("icaro.apps.subprocess.Popen")
    def test_missing(self, popen):
        with self.assertRaises(FileNotFoundError):
            launch_app("editor", {"editor": "Z:/missing/editor.exe"})
        self.assertIsNone(resolve_app("desconhecido", {}))
        popen.assert_not_called()

    @patch("icaro.apps.Path.is_file", return_value=False)
    @patch("icaro.apps.shutil.which", return_value=None)
    @patch("icaro.apps.subprocess.Popen")
    def test_missing_builtin(self, popen, which, exists):
        for name in ("calculadora", "terminal", "vs code"):
            with self.assertRaises(FileNotFoundError):
                launch_app(name, {})
        popen.assert_not_called()

    @patch("icaro.apps.subprocess.Popen", side_effect=PermissionError("negado"))
    @patch("icaro.apps.resolve_app", return_value=Path("C:/Program Files/Editor/editor.exe"))
    def test_launch_failure(self, resolve, popen):
        with self.assertRaises(PermissionError):
            launch_app("editor", {})


class DispatchTests(unittest.TestCase):
    def setUp(self):
        self.config = {"sites": {"youtube": "https://www.youtube.com"}, "apps": {}}
        self.output = io.StringIO()
        self.redirect = contextlib.redirect_stdout(self.output)
        self.redirect.__enter__()
        self.addCleanup(self.redirect.__exit__, None, None, None)

    @patch("icaro.assistant.launch_app")
    @patch("icaro.assistant.open_url")
    def test_routes(self, browser, launch):
        for phrase in ("abrir YouTube", "abrir github.com", "abrir navegador",
                       "pesquisar previsão do tempo em Fortaleza"):
            self.assertTrue(handle(phrase, self.config))
        self.assertEqual(browser.call_count, 4)
        handle("abrir bloco de notas", self.config)
        launch.assert_called_once_with("bloco de notas", {})
        self.assertFalse(handle("encerrar", self.config))

    @patch("icaro.assistant.launch_app")
    @patch("icaro.assistant.open_url")
    def test_unknown_has_no_effect(self, browser, launch):
        for phrase in ("abrir youtub", "execute calc.exe", "abrir file:///test", "sair agora"):
            self.assertTrue(handle(phrase, self.config))
        browser.assert_not_called()
        launch.assert_not_called()
        self.assertIn("Comandos Sugeridos:", self.output.getvalue())

    @patch("icaro.assistant.launch_app", side_effect=FileNotFoundError("não encontrado"))
    def test_error_is_friendly(self, launch):
        self.assertTrue(handle("abrir calculadora", self.config))
        self.assertIn("não encontrado", self.output.getvalue())


if __name__ == "__main__":
    unittest.main()
