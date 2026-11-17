"""Command line interface for 321code."""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

from . import __version__
from .runtime import run_file

RESET = "\033[0m"
COLORS = {
    "cyan": "\033[96m", "green": "\033[92m", "yellow": "\033[93m",
    "red": "\033[91m", "purple": "\033[95m", "blue": "\033[94m",
}

# Aliases are handled here, not only displayed in the command catalogue.
ALIASES = {
    "pomoc": "help",
    "wersja": "version",
    "uruchom": "run",
    "create": "init",
    "add": "install",
    "cls": "clear",
    "pkg": "packages",
}


def enable_colors() -> None:
    """Enable ANSI virtual-terminal sequences in Windows CMD."""
    if os.name == "nt":
        try:
            import ctypes
            kernel32 = ctypes.windll.kernel32
            handle = kernel32.GetStdHandle(-11)
            mode = ctypes.c_uint()
            if kernel32.GetConsoleMode(handle, ctypes.byref(mode)):
                kernel32.SetConsoleMode(handle, mode.value | 0x0004)
        except Exception:
            pass


def paint(message: str, color: str = "cyan") -> str:
    if not sys.stdout.isatty():
        return message
    return f"{COLORS.get(color, COLORS['cyan'])}{message}{RESET}"


def info(message: str) -> None:
    print(paint(message, "cyan"))


def success(message: str) -> None:
    print(paint(message, "green"))


def error(message: str) -> None:
    print(paint(message, "red"), file=sys.stderr)


def load_catalogue() -> dict:
    path = Path(__file__).with_name("commands.json")
    return json.loads(path.read_text(encoding="utf-8"))


def project_config() -> dict:
    path = Path("321code.json")
    if not path.exists():
        raise SystemExit("Nie znaleziono 321code.json. Utwórz plik konfiguracji projektu.")
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise SystemExit(f"Błędny 321code.json: {exc}") from exc


def run_script(name: str) -> int:
    scripts = project_config().get("scripts", {})
    command = scripts.get(name)
    if not isinstance(command, list) or not command or not all(isinstance(x, str) for x in command):
        raise SystemExit(f"Brak poprawnego skryptu '{name}' w 321code.json.")
    info(f"321code: uruchamiam skrypt '{name}'")
    result = subprocess.run(command, check=False)
    return result.returncode


def ai_command(args: list[str]) -> int:
    if not args:
        from .ai_app import main as creator_main
        return creator_main()
    action, *rest = args
    if action in {"help", "pomoc", "--help", "-h"}:
        print(paint("321 AI — tworzenie i obsługa własnych modeli", "purple"))
        print("  321 ai       Otwórz kreator nowego modelu")
        print("  321 ai chat  Otwórz bibliotekę modeli, eksport i czat")
        print("  321 ai help  Pokaż tę pomoc")
        return 0
    if action == "chat" and not rest:
        from .ai_hub import main as studio_main
        return studio_main()
    error("Nieznana komenda AI. Wpisz: 321 ai help")
    return 2


def show_help() -> None:
    print(paint(f"321code {__version__} — własny język i narzędzia", "purple"))
    print(paint("Użycie: 321 <komenda> [argumenty]", "cyan"))
    print("\nKomendy główne:")
    for item in load_catalogue()["commands"]:
        aliases = item.get("aliases", [])
        alias_text = f" (alias: {', '.join(aliases)})" if aliases else ""
        print(f"  {item['name']:<18} {item['description']}{alias_text}")
    print("\nZarządzanie pakietami:")
    print("  321 packages help")
    print("  321 packages init <folder> <nazwa>")
    print("  321 packages install <nazwa|plik.zip>")
    print("  321 packages list")
    print("  321 packages remove <nazwa>")
    print("  321 packages update [nazwa]")
    print("  321 packages pack <folder> [plik.zip]")
    print("\n321 AI:")
    print("  321 ai")
    print("  321 ai chat")
    print("\nPlik języka: 321 run plik.321")


def main(argv: list[str] | None = None) -> int:
    enable_colors()
    raw_args = list(sys.argv[1:] if argv is None else argv)

    # Handle standard Python-like flags ourselves so they show the 321code help.
    if not raw_args or raw_args[0] in {"help", "pomoc", "--help", "-h"}:
        show_help()
        return 0
    if raw_args[0] in {"version", "wersja", "--version", "-V"}:
        print(paint(f"321code {__version__}", "green"))
        return 0

    parser = argparse.ArgumentParser(
        prog="321",
        description="Interpreter języka 321code",
        add_help=False,
    )
    parser.add_argument("command")
    parser.add_argument("args", nargs="*")
    try:
        ns = parser.parse_args(raw_args)
    except SystemExit as exc:
        return int(exc.code)

    cmd = ALIASES.get(ns.command.lower(), ns.command.lower())
    if cmd == "run":
        if len(ns.args) != 1:
            error("Użycie: 321 run plik.321")
            return 2
        return run_file(Path(ns.args[0]))
    if cmd in {"start", "build"}:
        if ns.args:
            error(f"Użycie: 321 {cmd}")
            return 2
        return run_script(cmd)
    if cmd == "ai":
        return ai_command(ns.args)
    if cmd == "packages":
        from .packages import main as packages_main
        return packages_main(ns.args)
    if cmd == "install":
        from .packages import main as packages_main
        return packages_main(["install", *ns.args])
    if cmd == "clear":
        if ns.args:
            error("Użycie: 321 clear")
            return 2
        os.system("cls" if os.name == "nt" else "clear")
        return 0
    if cmd == "init":
        if ns.args:
            error("Użycie: 321 init")
            return 2
        path = Path("321code.json")
        if path.exists():
            error("321code.json już istnieje.")
            return 1
        path.write_text(
            json.dumps({"name": Path.cwd().name, "scripts": {}}, indent=2),
            encoding="utf-8",
        )
        success("Utworzono 321code.json")
        return 0

    error(f"Nieznana komenda: {cmd}. Wpisz '321 help'.")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
