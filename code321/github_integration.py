"""GitHub publishing helpers using the official GitHub CLI (gh).

321code never asks for or stores a GitHub password/token. Authentication is
handled by GitHub CLI's browser/device flow and its secure credential store.
"""
from __future__ import annotations

import shutil
import subprocess
from pathlib import Path


def gh_path() -> str | None:
    return shutil.which("gh")


def auth_status() -> tuple[bool, str]:
    executable = gh_path()
    if not executable:
        return False, "Nie znaleziono GitHub CLI (gh). Zainstaluj GitHub CLI i uruchom ponownie."
    result = subprocess.run(
        [executable, "auth", "status"], capture_output=True, text=True,
        encoding="utf-8", errors="replace", timeout=20,
    )
    message = (result.stdout + "\n" + result.stderr).strip()
    return result.returncode == 0, message or "Brak aktywnej sesji GitHub."


def login_command() -> list[str]:
    executable = gh_path()
    if not executable:
        raise FileNotFoundError("Zainstaluj GitHub CLI: https://cli.github.com/")
    return [executable, "auth", "login", "--web", "--git-protocol", "https"]


def publish_repository(project: Path, repository: str, private: bool = True) -> str:
    executable = gh_path()
    if not executable:
        raise FileNotFoundError("Nie znaleziono GitHub CLI (gh).")
    project = project.resolve()
    if not (project / "config.json").is_file():
        raise ValueError("To nie wygląda na projekt 321 AI.")
    status, detail = auth_status()
    if not status:
        raise RuntimeError("Najpierw połącz konto GitHub w 321 AI. " + detail)
    visibility = "--private" if private else "--public"
    result = subprocess.run(
        [executable, "repo", "create", repository, visibility,
         "--source", str(project), "--remote", "origin", "--push"],
        cwd=project, capture_output=True, text=True, encoding="utf-8",
        errors="replace", timeout=180,
    )
    if result.returncode:
        raise RuntimeError((result.stderr or result.stdout or "Nie udało się utworzyć repozytorium.").strip())
    return (result.stdout or f"Utworzono https://github.com/{repository}").strip()
