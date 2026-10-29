"""Despacho explícito das ações do MVP."""
from .apps import ALIASES, launch_app
from .commands import normalize, parse
from .navigation import open_url, search_url, validate_url

HELP = "Comandos Sugeridos: abrir calculadora | abrir YouTube | abrir github.com | pesquisar previsão do tempo em Campina Grande | sair/encerrar Icaro"


def handle(text: str, config: dict, respond=print) -> bool:
    command = parse(text)
    if command.action == "exit":
        respond("Icaro encerrado.")
        return False
    try:
        if command.action == "search":
            open_url(search_url(command.target))
            respond("Pesquisa aberta no navegador.")
        elif command.action == "open":
            key = normalize(command.target)
            if key in config["apps"] or key in ALIASES:
                launch_app(key, config["apps"])
                respond(f"Aplicativo aberto: {command.target}")
            elif key == "navegador":
                open_url("https://www.google.com")
                respond("Navegador aberto.")
            elif key in config["sites"]:
                open_url(config["sites"][key])
                respond(f"Página aberta: {command.target}")
            else:
                try:
                    url = validate_url(command.target)
                except ValueError:
                    respond("Site/endereço desconhecido ou inválido. " + HELP)
                else:
                    open_url(url)
                    respond("Página aberta no navegador.")
        else:
            respond(HELP)
    except (OSError, ValueError) as error:
        respond(f"Não foi possível executar: {error}")
    return True
