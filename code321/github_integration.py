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
    # gh repo create --source expects a local Git repository with a commit.
    identity = subprocess.run(
        [executable, "api", "user", "--jq", ".login"],
        capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=20,
    )
    if identity.returncode or not identity.stdout.strip():
        raise RuntimeError("Nie udało się odczytać profilu zalogowanego GitHub.")
    login = identity.stdout.strip()
    if not (project / ".git").exists():
        init = subprocess.run(["git", "init", "-b", "main"], cwd=project,
                              capture_output=True, text=True, timeout=30)
        if init.returncode:
            init = subprocess.run(["git", "init"], cwd=project,
                                  capture_output=True, text=True, timeout=30)
        if init.returncode:
            raise RuntimeError("Nie udało się zainicjalizować Git: " + init.stderr.strip())
    ignore = project / ".gitignore"
    if not ignore.exists():
        ignore.write_text("checkpoints/*.pt\\n__pycache__/\\n*.pyc\\n", encoding="utf-8")
    added = subprocess.run(["git", "add", "-A"], cwd=project,
                           capture_output=True, text=True, timeout=60)
    if added.returncode:
        raise RuntimeError("git add nie powiódł się: " + added.stderr.strip())
    committed = subprocess.run(
        ["git", "-c", f"user.name={login}", "-c",
         f"user.email={login}@users.noreply.github.com",
         "commit", "-m", "Create 321 AI model project"],
        cwd=project, capture_output=True, text=True, encoding="utf-8",
        errors="replace", timeout=60,
    )
    if committed.returncode and "nothing to commit" not in (committed.stdout + committed.stderr).lower():
        raise RuntimeError("Nie udało się przygotować commita: " + (committed.stderr or committed.stdout).strip())
    result = subprocess.run(
        [executable, "repo", "create", repository, visibility,
         "--source", str(project), "--remote", "origin", "--push"],
        cwd=project, capture_output=True, text=True, encoding="utf-8",
        errors="replace", timeout=180,
    )
    if result.returncode:
        raise RuntimeError((result.stderr or result.stdout or "Nie udało się utworzyć repozytorium.").strip())
    return (result.stdout or f"Utworzono https://github.com/{repository}").strip()
