"""Navegação HTTP(S) e pesquisa codificada."""
import ipaddress
import re
import webbrowser
from urllib.parse import urlencode, urlsplit, urlunsplit


def validate_url(value: str) -> str:
    if not isinstance(value, str) or not value or any(c.isspace() or ord(c) < 32 for c in value):
        raise ValueError("Endereço vazio ou com espaços/caracteres de controle.")
    if "\\" in value or any(c in value for c in '<>"'):
        raise ValueError("Endereço inválido.")
    if "://" not in value:
        value = "https://" + value
    try:
        url = urlsplit(value)
        if url.scheme not in {"http", "https"} or not url.hostname or url.username is not None or url.password is not None:
            raise ValueError("Use HTTP ou HTTPS, sem credenciais.")
        host = url.hostname.encode("idna").decode("ascii")
        try:
            ipaddress.ip_address(host)
        except ValueError:
            labels = host.split(".")
            if len(labels) < 2 or not all(re.fullmatch(r"[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?", x) for x in labels):
                raise ValueError("Informe um domínio completo ou IP válido.")
            if labels[-1].isdigit():
                raise ValueError("IP inválido.")
        port = url.port
        authority = f"[{host}]" if ":" in host else host
        if port is not None:
            authority += f":{port}"
        return urlunsplit((url.scheme, authority, url.path, url.query, url.fragment))
    except (ValueError, UnicodeError) as error:
        raise ValueError(f"Endereço inválido: {error}") from error


def search_url(terms: str) -> str:
    if not terms.strip():
        raise ValueError("Informe o que pesquisar.")
    return "https://www.google.com/search?" + urlencode({"q": terms.strip()})


def open_url(url: str) -> None:
    if not webbrowser.open(validate_url(url), new=2):
        raise OSError("O navegador padrão não aceitou a abertura.")
