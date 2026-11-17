"""Secure local and registry package manager for 321code.

Registry format:
{
  "packages": {
    "example": {
      "version": "1.0.0",
      "url": "https://.../example-1.0.0.zip",
      "sha256": "<64 hex chars>",
      "dependencies": {}
    }
  }
}
A package ZIP must contain package.json at its root and .321 modules.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import tempfile
import urllib.error
import urllib.request
import zipfile
from pathlib import Path, PurePosixPath

REGISTRY_URL = "https://raw.githubusercontent.com/kaielk09/jenzyku/main/packages/index.json"
MAX_ARCHIVE_BYTES = 50 * 1024 * 1024
MAX_UNPACKED_BYTES = 200 * 1024 * 1024
NAME_RE = re.compile(r"^[a-zA-Z0-9][a-zA-Z0-9_.-]{0,63}$")
LOCK_NAME = "321code.lock"


class PackageError(Exception):
    """Expected package-manager error."""


def project_root(start: Path | None = None) -> Path:
    current = (start or Path.cwd()).resolve()
    for candidate in (current, *current.parents):
        if (candidate / "321code.json").is_file():
            return candidate
    raise PackageError("Nie znaleziono 321code.json. Uruchom 321 init w folderze projektu.")


def _read_json(path: Path, fallback):
    if not path.is_file():
        return fallback
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise PackageError(f"Nie można odczytać {path.name}: {exc}") from exc


def _write_json(path: Path, data) -> None:
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _valid_name(name: str) -> str:
    if not NAME_RE.fullmatch(name) or name in {".", ".."}:
        raise PackageError(f"Niepoprawna nazwa pakietu: {name!r}")
    return name


def _download(url: str, destination: Path, limit: int) -> None:
    if not url.startswith("https://"):
        raise PackageError("Pakiety z rejestru muszą być pobierane przez HTTPS.")
    request = urllib.request.Request(url, headers={"User-Agent": "321code-package-manager/1.0"})
    try:
        with urllib.request.urlopen(request, timeout=30) as response, destination.open("wb") as output:
            length = response.headers.get("Content-Length")
            if length and int(length) > limit:
                raise PackageError("Pobrany plik przekracza dozwolony rozmiar.")
            total = 0
            while True:
                chunk = response.read(1024 * 1024)
                if not chunk:
                    break
                total += len(chunk)
                if total > limit:
                    raise PackageError("Pobrany plik przekracza dozwolony rozmiar.")
                output.write(chunk)
    except (urllib.error.URLError, TimeoutError, OSError, ValueError) as exc:
        raise PackageError(f"Nie udało się pobrać pakietu: {exc}") from exc


def _safe_extract(archive: Path, destination: Path) -> None:
    total = 0
    root = destination.resolve()
    try:
        with zipfile.ZipFile(archive) as bundle:
            for item in bundle.infolist():
                name = item.filename.replace("\\", "/")
                relative = PurePosixPath(name)
                if relative.is_absolute() or not relative.parts or ":" in relative.parts[0] or any(part in ("", ".", "..") for part in relative.parts):
                    raise PackageError(f"Niebezpieczna ścieżka w archiwum: {name}")
                # ZIP symlinks are not needed for source packages; reject them.
                mode = (item.external_attr >> 16) & 0xFFFF
                if mode and (mode & 0o170000) == 0o120000:
                    raise PackageError("Pakiet zawiera niedozwolony dowiązany plik.")
                total += item.file_size
                if total > MAX_UNPACKED_BYTES:
                    raise PackageError("Rozpakowany pakiet przekracza limit 200 MB.")
                target = (root / Path(*relative.parts)).resolve()
                if root not in target.parents and target != root:
                    raise PackageError(f"Ścieżka wychodzi poza folder pakietu: {name}")
                if item.is_dir():
                    target.mkdir(parents=True, exist_ok=True)
                else:
                    target.parent.mkdir(parents=True, exist_ok=True)
                    with bundle.open(item) as source, target.open("wb") as output:
                        shutil.copyfileobj(source, output)
    except zipfile.BadZipFile as exc:
        raise PackageError("Pobrany plik nie jest poprawnym archiwum ZIP.") from exc


def _manifest(folder: Path) -> dict:
    manifest = _read_json(folder / "package.json", None)
    if not isinstance(manifest, dict):
        raise PackageError("Pakiet nie zawiera poprawnego package.json.")
    name = _valid_name(str(manifest.get("name", "")))
    version = str(manifest.get("version", "")).strip()
    if not version or len(version) > 64:
        raise PackageError("package.json musi zawierać wersję pakietu.")
    if not any(folder.rglob("*.321")):
        raise PackageError("Pakiet musi zawierać przynajmniej jeden plik .321.")
    return {"name": name, "version": version, "dependencies": manifest.get("dependencies", {})}


def _registry() -> dict:
    with tempfile.TemporaryDirectory(prefix="321-registry-") as temp:
        target = Path(temp) / "index.json"
        _download(REGISTRY_URL, target, 2 * 1024 * 1024)
        data = _read_json(target, {})
    if not isinstance(data, dict) or not isinstance(data.get("packages"), dict):
        raise PackageError("Rejestr pakietów ma niepoprawny format.")
    return data["packages"]


def _lock(root: Path) -> dict:
    data = _read_json(root / LOCK_NAME, {"lock_version": 1, "packages": {}})
    if not isinstance(data, dict) or not isinstance(data.get("packages"), dict):
        raise PackageError("Niepoprawny plik 321code.lock.")
    return data


def _install_archive(archive: Path, root: Path, expected_name: str | None = None,
                     expected_sha256: str | None = None) -> dict:
    if not archive.is_file() or archive.stat().st_size > MAX_ARCHIVE_BYTES:
        raise PackageError("Archiwum nie istnieje lub przekracza limit 50 MB.")
    digest = hashlib.sha256(archive.read_bytes()).hexdigest()
    if expected_sha256 and digest.lower() != expected_sha256.lower():
        raise PackageError("Kontrola SHA-256 nie powiodła się. Pakiet może być uszkodzony.")
    packages_dir = root / ".321code" / "packages"
    packages_dir.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="321pkg-", dir=packages_dir) as temp:
        unpacked = Path(temp) / "package"
        unpacked.mkdir()
        _safe_extract(archive, unpacked)
        manifest = _manifest(unpacked)
        if expected_name and manifest["name"] != expected_name:
            raise PackageError("Nazwa w package.json nie zgadza się z nazwą w rejestrze.")
        final = packages_dir / manifest["name"]
        if final.exists():
            shutil.rmtree(final)
        shutil.copytree(unpacked, final)
    lock = _lock(root)
    lock["lock_version"] = 1
    lock["packages"][manifest["name"]] = {
        "version": manifest["version"],
        "sha256": digest,
        "source": "local" if not expected_sha256 else "registry",
    }
    _write_json(root / LOCK_NAME, lock)
    return manifest


def _install_registry(name: str, root: Path, registry: dict, stack: set[str]) -> list[str]:
    name = _valid_name(name)
    if name in stack:
        raise PackageError("Wykryto cykl zależności: " + " -> ".join([*stack, name]))
    entry = registry.get(name)
    if not isinstance(entry, dict):
        raise PackageError(f"Nie znaleziono pakietu '{name}' w rejestrze.")
    url, digest = entry.get("url"), entry.get("sha256")
    if not isinstance(url, str) or not isinstance(digest, str) or not re.fullmatch(r"[0-9a-fA-F]{64}", digest):
        raise PackageError(f"Wpis pakietu '{name}' nie ma poprawnego URL lub SHA-256.")
    messages = []
    stack.add(name)
    dependencies = entry.get("dependencies", {})
    if not isinstance(dependencies, dict):
        raise PackageError(f"Niepoprawna lista zależności pakietu '{name}'.")
    for dependency, required_version in sorted(dependencies.items()):
        dependency = _valid_name(str(dependency))
        dependency_entry = registry.get(dependency)
        if not isinstance(dependency_entry, dict):
            raise PackageError(f"Brak zależności '{dependency}' wymaganej przez '{name}'.")
        if required_version not in (None, "*", dependency_entry.get("version")):
            raise PackageError(f"Zależność '{dependency}' wymaga wersji {required_version}, "
                               f"a rejestr udostępnia {dependency_entry.get('version')}.")
        messages.extend(_install_registry(dependency, root, registry, stack))
    stack.remove(name)
    with tempfile.TemporaryDirectory(prefix="321pkg-download-") as temp:
        archive = Path(temp) / "package.zip"
        _download(url, archive, MAX_ARCHIVE_BYTES)
        manifest = _install_archive(archive, root, expected_name=name, expected_sha256=digest)
    messages.append(f"Zainstalowano {manifest['name']}@{manifest['version']}.")
    return messages


def install(spec: str, root: Path | None = None) -> str:
    project = project_root(root)
    candidate = Path(spec).expanduser()
    if candidate.is_file():
        manifest = _install_archive(candidate.resolve(), project)
        return f"Zainstalowano {manifest['name']}@{manifest['version']} z pliku."
    name = _valid_name(spec)
    messages = _install_registry(name, project, _registry(), set())
    return "\n".join(messages)


def list_packages(root: Path | None = None) -> list[dict]:
    project = project_root(root)
    lock = _lock(project)
    result = []
    for name, info in sorted(lock["packages"].items()):
        folder = project / ".321code" / "packages" / name
        result.append({"name": name, "version": info.get("version", "?"), "installed": folder.is_dir()})
    return result


def remove(name: str, root: Path | None = None) -> str:
    project = project_root(root)
    name = _valid_name(name)
    lock = _lock(project)
    if name not in lock["packages"]:
        raise PackageError(f"Pakiet '{name}' nie jest zainstalowany.")
    folder = project / ".321code" / "packages" / name
    if folder.exists():
        shutil.rmtree(folder)
    del lock["packages"][name]
    _write_json(project / LOCK_NAME, lock)
    return f"Usunięto pakiet {name}."


def update(name: str | None = None, root: Path | None = None) -> list[str]:
    project = project_root(root)
    lock = _lock(project)
    selected = [_valid_name(name)] if name else sorted(lock["packages"])
    messages = []
    for package in selected:
        if package not in lock["packages"]:
            raise PackageError(f"Pakiet '{package}' nie jest zainstalowany.")
        if lock["packages"][package].get("source") == "local":
            messages.append(f"Pominięto {package}: pakiet lokalny nie pochodzi z rejestru.")
            continue
        messages.append(install(package, project))
    return messages


def init_package(folder: str, name: str) -> Path:
    target = Path(folder).expanduser().resolve()
    package_name = _valid_name(name)
    if target.exists():
        raise PackageError("Folder docelowy już istnieje.")
    target.mkdir(parents=True)
    _write_json(target / "package.json", {
        "name": package_name,
        "version": "1.0.0",
        "description": "Pakiet dla 321code",
        "dependencies": {},
    })
    (target / "main.321").write_text(f'print "Witaj z pakietu {package_name}"\n', encoding="utf-8")
    return target


def pack(folder: str, output: str | None = None) -> Path:
    source = Path(folder).expanduser().resolve()
    if not source.is_dir():
        raise PackageError("Folder pakietu nie istnieje.")
    manifest = _manifest(source)
    destination = Path(output).expanduser().resolve() if output else Path.cwd() / f"{manifest['name']}-{manifest['version']}.zip"
    destination.parent.mkdir(parents=True, exist_ok=True)
    import zipfile
    with zipfile.ZipFile(destination, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for path in sorted(source.rglob("*")):
            if path.is_file() and ".git" not in path.parts and "__pycache__" not in path.parts:
                archive.write(path, path.relative_to(source).as_posix())
    digest = hashlib.sha256(destination.read_bytes()).hexdigest()
    return destination


def main(args: list[str]) -> int:
    import sys
    try:
        if not args or args[0] in {"help", "--help", "pomoc"}:
            print("321 packages: init <folder> <nazwa> | install <nazwa|plik.zip> | list | remove <nazwa> | update [nazwa] | pack <folder> [plik.zip]")
            return 0
        action, *rest = args
        if action in {"install", "add"} and len(rest) == 1:
            print(install(rest[0]))
        elif action in {"list", "ls"} and not rest:
            rows = list_packages()
            if not rows:
                print("Brak zainstalowanych pakietów.")
            for row in rows:
                print(f"{row['name']}  {row['version']}  {'OK' if row['installed'] else 'BRAK PLIKÓW'}")
        elif action in {"remove", "uninstall"} and len(rest) == 1:
            print(remove(rest[0]))
        elif action == "update" and len(rest) <= 1:
            messages = update(rest[0] if rest else None)
            print("\n".join(messages) if messages else "Brak pakietów do aktualizacji.")
        elif action == "init" and len(rest) == 2:
            print(f"Utworzono szkielet pakietu: {init_package(rest[0], rest[1])}")
        elif action == "pack" and 1 <= len(rest) <= 2:
            result = pack(rest[0], rest[1] if len(rest) == 2 else None)
            print(f"Utworzono: {result}")
            print("SHA-256:", hashlib.sha256(result.read_bytes()).hexdigest())
        else:
            print("Niepoprawne argumenty. Użyj: 321 packages help", file=sys.stderr)
            return 2
        return 0
    except (PackageError, OSError, ValueError) as exc:
        print(f"321 packages: {exc}", file=sys.stderr)
        return 1
