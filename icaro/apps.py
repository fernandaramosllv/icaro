"""Descoberta limitada a executáveis conhecidos ou configurados."""
import os
from pathlib import Path
import shutil
import subprocess

ALIASES = {
    "calculadora": "calculator", "bloco de notas": "notepad",
    "explorador": "explorer", "explorador de arquivos": "explorer",
    "terminal": "terminal", "vscode": "vscode", "vs code": "vscode",
    "visual studio code": "vscode",
}


def resolve_app(name: str, configured: dict) -> Path | None:
    if name in configured:
        path = Path(configured[name])
        return path if path.is_file() else None
    kind = ALIASES.get(name)
    system = Path(os.environ.get("SystemRoot", r"C:\Windows"))
    candidates = {
        "calculator": [system / "System32/calc.exe"],
        "notepad": [system / "System32/notepad.exe"],
        "explorer": [system / "explorer.exe"],
    }.get(kind, [])
    executable = {"terminal": "wt.exe", "vscode": "Code.exe"}.get(kind)
    if executable:
        found = shutil.which(executable)
        if found:
            candidates.append(Path(found))
    if kind == "terminal":
        candidates.append(system / "System32/WindowsPowerShell/v1.0/powershell.exe")
    if kind == "vscode":
        for env, suffix in (("LOCALAPPDATA", "Programs/Microsoft VS Code/Code.exe"), ("ProgramFiles", "Microsoft VS Code/Code.exe")):
            if os.environ.get(env):
                candidates.append(Path(os.environ[env]) / suffix)
    return next((p for p in candidates if p.is_file()), None)


def launch_app(name: str, configured: dict) -> Path:
    path = resolve_app(name, configured)
    if path is None:
        raise FileNotFoundError(f"Aplicativo '{name}' não encontrado. Configure seu caminho em config.local.json.")
    subprocess.Popen([str(path)], shell=False)
    return path
