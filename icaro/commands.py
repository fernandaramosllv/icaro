"""Interpretação determinística compartilhada por voz e texto."""
import unicodedata
from dataclasses import dataclass


def normalize(text: str) -> str:
    return " ".join("".join(c for c in unicodedata.normalize("NFD", text.casefold())
                            if not unicodedata.combining(c)).split())


@dataclass(frozen=True)
class Command:
    action: str
    target: str = ""


def parse(text: str) -> Command:
    key = normalize(text)
    if key in {"sair", "encerrar", "encerrar icaro", "tchau"}:
        return Command("exit")
    if key in {"ajuda", "comandos"}:
        return Command("help")
    parts = text.strip().split(maxsplit=1)
    if len(parts) == 2:
        verb = normalize(parts[0])
        if verb in {"abrir", "acessar"}:
            return Command("open", parts[1].strip())
        if verb in {"pesquisar", "buscar"}:
            return Command("search", parts[1].strip())
    return Command("unknown")
