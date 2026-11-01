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
    print(f"321code: uruchamiam skrypt '{name}'")
    result = subprocess.run(command, check=False)
    return result.returncode


def ai_command(args: list[str]) -> int:
    if not args:
        from .ai_app import main as creator_main
        return creator_main()
    action, *rest = args
    if action in {"help", "pomoc"}:
        print("321 AI — tworzenie własnych modeli językowych")
        print("  321 ai              Otwórz kreator modelu")
        print("  321 ai train <folder>  Wytrenuj model z dataset.txt")
        print("  321 ai chat <folder>   Otwórz okno czatu wytrenowanego modelu")
        return 0
    if action == "train":
        from .ai_trainer import main as trainer_main
        return trainer_main(rest)
    if action == "chat":
        from .ai_chat import main as chat_main
        return chat_main(rest)
    print("Nieznana komenda AI. Wpisz: 321 ai help", file=sys.stderr)
    return 2


def show_help() -> None:
    print(f"321code {__version__} — własny język i narzędzia")
    print("Użycie: 321 <komenda> [argumenty]")
    print("  ai             Twórz i trenuj własne modele AI")
    print("\nKomendy:")
    for item in load_catalogue()["commands"]:
        print(f"  {item['name']:<14} {item['description']}")
    print("\nPlik języka: 321 run plik.321")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="321", description="Interpreter języka 321code")
    parser.add_argument("command", nargs="?", default="help")
    parser.add_argument("args", nargs="*")
    ns = parser.parse_args(argv)
    cmd = ns.command.lower()
    if cmd in {"help", "pomoc", "--help"}:
        show_help()
        return 0
    if cmd in {"version", "wersja", "--version"}:
        print(f"321code {__version__}")
        return 0
    if cmd in {"run", "uruchom"}:
        if len(ns.args) != 1:
            print("Użycie: 321 run plik.321", file=sys.stderr)
            return 2
        return run_file(Path(ns.args[0]))
    if cmd in {"start", "build"}:
        return run_script(cmd)
    if cmd == "ai":
        return ai_command(ns.args)
    if cmd in {"install", "init", "clear"}:
        if cmd == "clear":
            os.system("cls" if os.name == "nt" else "clear")
            return 0
        if cmd == "init":
            path = Path("321code.json")
            if path.exists():
                print("321code.json już istnieje.")
                return 1
            path.write_text(json.dumps({"name": Path.cwd().name, "scripts": {}}, indent=2), encoding="utf-8")
            print("Utworzono 321code.json")
            return 0
        print("Menedżer pakietów jest w przygotowaniu. Nie pobrano żadnych plików.")
        return 0
    print(f"Nieznana komenda: {cmd}. Wpisz '321 help'.", file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
