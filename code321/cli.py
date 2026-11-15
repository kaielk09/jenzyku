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
        from .ai_studio_v2 import main as creator_main
        return creator_main()
    action, *rest = args
    if action in {"help", "pomoc"}:
        print(paint("321 AI — tworzenie własnych modeli językowych", "purple"))
        print("  321 ai                 Otwórz kreator modelu")
        print("  321 ai train <folder>  Wytrenuj model z dataset.txt")
        print("  321 ai chat <folder>   Otwórz okno czatu wytrenowanego modelu")
        print("  321 ai serve <folder>  Uruchom lokalne API HTTP")
        print("  321 ai web             Otwórz panel WWW 321 AI Creator")
        print("  321 ai publish-hf <folder> --repo-id USER/MODEL")
        print("  321 ai download-dataset USER/DATASET <plik.jsonl>")
        print("  321 ai train-images <folder-obrazow> --output <folder-modelu>")
        print("  321 ai generate-image <folder-modelu> --count 1")
        return 0
    if action == "train":
        from .ai_trainer import main as trainer_main
        return trainer_main(rest)
    if action == "chat":
        from .ai_chat import main as chat_main
        return chat_main(rest)
    if action == "serve":
        from .ai_api import main as api_main
        return api_main(rest)
    if action == "web":
        from .ai_web_studio import main as web_main
        return web_main(rest)
    if action == "publish-hf":
        import argparse
        from .ai_hub import publish_model
        parser=argparse.ArgumentParser(prog="321 ai publish-hf")
        parser.add_argument("project"); parser.add_argument("--repo-id",required=True)
        parser.add_argument("--public",action="store_true")
        opts=parser.parse_args(rest)
        try:
            print("Model opublikowany: "+publish_model(opts.project,opts.repo_id,private=not opts.public))
            return 0
        except Exception as exc:
            error(str(exc)); return 2
    if action == "download-dataset":
        import argparse
        from .ai_hub import download_dataset
        parser=argparse.ArgumentParser(prog="321 ai download-dataset")
        parser.add_argument("repo_id"); parser.add_argument("output")
        parser.add_argument("--split",default="train"); parser.add_argument("--max-examples",type=int,default=10000)
        opts=parser.parse_args(rest)
        try:
            path,note=download_dataset(opts.repo_id,opts.output,opts.split,opts.max_examples)
            success(note); info(f"Plik: {path}"); return 0
        except Exception as exc:
            error(str(exc)); return 2
    if action == "train-images":
        from .ai_image_trainer import main as image_train_main
        return image_train_main(rest)
    if action == "generate-image":
        from .ai_image_generate import main as image_generate_main
        return image_generate_main(rest)
    error("Nieznana komenda AI. Wpisz: 321 ai help")
    return 2


def security_command(args: list[str]) -> int:
    from .security_scanner import (
        load_scan_folder, print_report, save_scan_folder, scan_folder, scan_website,
    )
    if not args:
        error("Użycie: 321 cd <folder> | 321 sprawdź | 321 sprawdź internet <URL>")
        return 2
    action = args[0].lower()
    try:
        if action == "cd":
            folder = " ".join(args[1:]).strip().strip('"')
            if not folder:
                error("Użycie: 321 cd C:\\ścieżka\\do\\folderu")
                return 2
            target = save_scan_folder(folder)
            success(f"Zapamiętano folder skanowania: {target}")
            info("Ustawienie jest trwałe i przetrwa zamknięcie CMD.")
            return 0
        if action in {"sprawdź", "sprawdz"}:
            if len(args) >= 2 and args[1].lower() in {"internet", "www", "url"}:
                if len(args) != 3:
                    error("Użycie: 321 sprawdź internet https://example.com")
                    return 2
                print_report(scan_website(args[2]), website=True)
                return 0
            if len(args) != 1:
                error("Użycie: 321 sprawdź")
                return 2
            report = scan_folder(load_scan_folder())
            print_report(report)
            return 1 if report["timed_out"] else 0
    except (ValueError, OSError) as exc:
        error(str(exc))
        return 1
    error("Nieznana komenda ochrony. Wpisz: 321 sprawdź")
    return 2


def show_help() -> None:
    print(paint(f"321code {__version__} — język, AI i narzędzia", "purple"))
    print(paint("Użycie: 321 <komenda> [argumenty]", "cyan"))
    print("\nKomendy:")
    for item in load_catalogue()["commands"]:
        print(f"  {paint(item['name'], 'green'):<24} {item['description']}")
    print("\nPlik języka: 321 run plik.321")
    print("Studio GUI: 321 studio")
    print("\n321 Security Scanner:")
    print("  321 cd <folder>                 Zapamiętaj folder do skanowania")
    print("  321 sprawdź                     Przeskanuj zapamiętany folder")
    print("  321 sprawdź internet <URL>      Przeanalizuj publiczną stronę WWW")


def main(argv: list[str] | None = None) -> int:
    enable_colors()
    parser = argparse.ArgumentParser(prog="321", description="Interpreter i narzędzia 321code")
    parser.add_argument("command", nargs="?", default="help")
    parser.add_argument("args", nargs="*")
    ns = parser.parse_args(argv)
    cmd = ns.command.lower()
    if cmd in {"help", "pomoc", "--help"}:
        show_help()
        return 0
    if cmd in {"version", "wersja", "--version"}:
        print(paint(f"321code {__version__}", "green"))
        return 0
    if cmd in {"run", "uruchom"}:
        if len(ns.args) != 1:
            error("Użycie: 321 run plik.321")
            return 2
        return run_file(Path(ns.args[0]))
    if cmd in {"start", "build"}:
        return run_script(cmd)
    if cmd == "ai":
        return ai_command(ns.args)
    if cmd in {"studio", "gui", "app"}:
        from .studio import main as studio_main
        return studio_main()
    if cmd in {"cd", "sprawdź", "sprawdz"}:
        return security_command([cmd, *ns.args])
    if cmd in {"install", "init", "clear"}:
        if cmd == "clear":
            os.system("cls" if os.name == "nt" else "clear")
            return 0
        if cmd == "init":
            path = Path("321code.json")
            if path.exists():
                error("321code.json już istnieje.")
                return 1
            path.write_text(json.dumps({"name": Path.cwd().name, "scripts": {}}, indent=2), encoding="utf-8")
            success("Utworzono 321code.json")
            return 0
        print("Menedżer pakietów jest w przygotowaniu. Nie pobrano żadnych plików.")
        return 0
    error(f"Nieznana komenda: {cmd}. Wpisz '321 help'.")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
