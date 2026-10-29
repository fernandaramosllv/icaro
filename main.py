"""Ponto de entrada do Icaro."""
import argparse
from pathlib import Path
from icaro.assistant import HELP, handle
from icaro.config import load_config
from icaro.speaker import create_speaker

ROOT = Path(__file__).resolve().parent


def main() -> int:
    parser = argparse.ArgumentParser(description="Icaro: assistente local de terminal")
    parser.add_argument("--text", action="store_true", help="Testar sem microfone/dependências de voz")
    parser.add_argument("--config", type=Path, help="Arquivo pessoal; modelo relativo à pasta desse arquivo")
    parser.add_argument("--list-devices", action="store_true", help="Listar dispositivos de áudio")
    parser.add_argument("--device", help="Índice ou nome do microfone")
    parser.add_argument("--mute", action="store_true", help="Desativar respostas faladas")
    args = parser.parse_args()
    try:
        if args.list_devices:
            from icaro.voice import list_devices
            list_devices()
            return 0
        path = args.config.resolve() if args.config else ROOT / "config.local.json"
        config = load_config(path, required=args.config is not None)
        print("Icaro pronto. " + HELP)
        if args.text:
            while handle(input("Você> "), config):
                pass
        else:
            from icaro.voice import listen
            model = Path(config["voice"]["model_path"])
            if not model.is_absolute():
                model = path.parent / model
            device = args.device if args.device is not None else config["voice"]["device"]
            if isinstance(device, str) and device.isdecimal():
                device = int(device)
            speak = None if args.mute else create_speaker()

            def respond(message: str) -> None:
                print(message)
                if speak is not None:
                    speak(message)

            respond("Icaro pronto. Pode falar.")
            listen(model, device, lambda text: handle(text, config, respond=respond))
    except (EOFError, KeyboardInterrupt):
        print("\nIcaro encerrado.")
    except (ValueError, OSError, RuntimeError) as error:
        print(f"Erro: {error}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
