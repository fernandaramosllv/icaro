"""Reconhecimento local Vosk; áudio não é gravado nem enviado à rede."""
import json
from pathlib import Path
import queue
from typing import Callable


def audio_module():
    try:
        import sounddevice
        return sounddevice
    except (ImportError, OSError) as error:
        raise RuntimeError("Áudio indisponível. Instale requirements.txt com Python 3.11 x64; use --text para testar.") from error


def list_devices() -> None:
    sd = audio_module()
    try:
        print(sd.query_devices())
    except sd.PortAudioError as error:
        raise RuntimeError(f"Não foi possível listar os dispositivos: {error}") from error


def listen(model_path: Path, device: int | str | None, on_text: Callable[[str], bool]) -> None:
    if not model_path.is_dir() or not any(
        (model_path / name).is_file() for name in ("am/final.mdl", "final.mdl")
    ):
        raise RuntimeError(f"Modelo Vosk não encontrado ou incompleto: {model_path}. Consulte o README.")
    sd = audio_module()
    try:
        from vosk import KaldiRecognizer, Model, SetLogLevel
    except (ImportError, OSError) as error:
        raise RuntimeError("Vosk indisponível. Instale requirements.txt com Python 3.11 x64.") from error
    # A fila limitada impede crescimento ilimitado se o processamento atrasar.
    audio = queue.Queue(maxsize=32)
    overflow = False

    def callback(indata, frames, time_info, status):
        nonlocal overflow
        if status:
            overflow = True
        try:
            audio.put_nowait(bytes(indata))
        except queue.Full:
            overflow = True

    try:
        info = sd.query_devices(device, "input")
        rate = int(info["default_samplerate"])
        sd.check_input_settings(device=device, channels=1, dtype="int16", samplerate=rate)
        SetLogLevel(-1)
        model = Model(str(model_path))
        recognizer = KaldiRecognizer(model, rate)
        with sd.RawInputStream(samplerate=rate, blocksize=4000, device=device,
                               dtype="int16", channels=1, callback=callback) as stream:
            print("Microfone ativo. Fale um comando e faça uma pausa. Para encerrar: sair ou Ctrl+C.")
            while True:
                try:
                    chunk = audio.get(timeout=0.5)
                except queue.Empty:
                    continue
                if overflow:
                    # Não interpretar áudio truncado como se fosse uma frase completa.
                    raise RuntimeError("Houve perda de áudio. Feche programas pesados e reinicie a escuta.")
                if recognizer.AcceptWaveform(chunk):
                    text = json.loads(recognizer.Result()).get("text", "").strip()
                    if text:
                        print(f"Você (voz)> {text}")
                        # Suspende captura antes de falar, evitando comandos pela própria voz.
                        stream.stop()
                        while not audio.empty():
                            audio.get_nowait()
                        if not on_text(text):
                            return
                        recognizer.Reset()
                        overflow = False
                        stream.start()
    except sd.PortAudioError as error:
        raise RuntimeError(f"Falha no microfone: {error}. Use --list-devices e --device.") from error
    except (OSError, ValueError) as error:
        raise RuntimeError(f"Falha no reconhecimento de voz: {error}") from error
    except Exception as error:
        # Vosk usa Exception genérica para falhas de carga do modelo.
        if type(error) is Exception:
            raise RuntimeError(f"Falha ao carregar/processar modelo Vosk: {error}") from error
        raise
