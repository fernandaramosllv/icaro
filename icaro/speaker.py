"""Resposta neural masculina online; reconhecimento de voz continua local."""
import asyncio
from typing import Callable

VOICE = "pt-BR-AntonioNeural"
RATE = "-5%"
MAX_AUDIO_BYTES = 10 * 1024 * 1024
SYNTHESIS_TIMEOUT = 30


def _load_dependencies():
    import edge_tts
    import miniaudio
    import sounddevice
    return edge_tts, miniaudio, sounddevice


async def _synthesize(text: str, edge_tts) -> bytes:
    audio = bytearray()
    communication = edge_tts.Communicate(
        text, VOICE, rate=RATE, connect_timeout=10, receive_timeout=15,
    )
    async for chunk in communication.stream():
        if chunk["type"] == "audio":
            audio.extend(chunk["data"])
            if len(audio) > MAX_AUDIO_BYTES:
                raise RuntimeError("Resposta de áudio maior que o limite permitido.")
    if not audio:
        raise RuntimeError("O serviço de voz não retornou áudio.")
    return bytes(audio)


def _play_audio(audio: bytes, decoder, sd) -> None:
    rate = int(sd.query_devices(kind="output")["default_samplerate"])
    decoded = decoder.decode(
        audio, output_format=decoder.SampleFormat.SIGNED16,
        nchannels=1, sample_rate=rate,
    )
    pcm = decoded.samples.tobytes()
    with sd.RawOutputStream(samplerate=rate, channels=1, dtype="int16") as stream:
        # Blocos curtos permitem interromper a reprodução com Ctrl+C.
        for offset in range(0, len(pcm), 8192):
            stream.write(pcm[offset:offset + 8192])


def create_speaker() -> Callable[[str], None] | None:
    try:
        edge_tts, decoder, sd = _load_dependencies()
    except (ImportError, OSError) as error:
        print(f"Voz neural indisponível: {error}. Instale requirements.txt; respostas apenas no terminal.")
        return None
    print("Voz de resposta: Antônio neural (masculina, online). Textos das respostas são enviados ao serviço Microsoft.")
    enabled = True

    async def generate(text: str) -> bytes:
        return await asyncio.wait_for(_synthesize(text, edge_tts), timeout=SYNTHESIS_TIMEOUT)

    def speak(text: str) -> None:
        nonlocal enabled
        if not enabled or not text.strip():
            return
        try:
            if len(text) > 4000:
                raise ValueError("Resposta longa demais para a síntese.")
            audio = asyncio.run(generate(text))
            _play_audio(audio, decoder, sd)
        except Exception as error:
            # Falhas de rede/serviço/saída não interrompem os comandos.
            print(f"Falha na voz neural: {type(error).__name__}: {error}. Respostas apenas no terminal até reiniciar.")
            enabled = False

    return speak
