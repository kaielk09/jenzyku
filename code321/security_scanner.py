"""Defensive, static-first security checks for 321code.

The scanner never executes inspected files. Results are indicators, not a verdict.
"""
from __future__ import annotations

import ipaddress
import json
import os
import re
import socket
import ssl
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any

MAX_SECONDS = 20.0
MAX_FILE_BYTES = 8 * 1024 * 1024
MAX_WEB_BYTES = 1_500_000
MAX_FILES = 5000

API_CATALOG: dict[str, tuple[str, ...]] = {
    "OpenAI": ("api.openai.com", "platform.openai.com"),
    "TostHost": ("my.tosthost.pl", "api.tosthost.pl", "tosthost.pl"),
    "Hugging Face": ("huggingface.co", "api-inference.huggingface.co"),
    "Discord": ("discord.com/api", "discordapp.com/api", "discordapp.com"),
    "GitHub": ("api.github.com", "github.com"),
    "Google": ("googleapis.com", "accounts.google.com"),
    "Microsoft": ("graph.microsoft.com", "login.microsoftonline.com"),
    "Cloudflare": ("api.cloudflare.com", "cloudflare.com"),
    "Stripe": ("api.stripe.com", "stripe.com"),
    "Roblox": ("apis.roblox.com", "roblox.com"),
    "Replit": ("replit.com", "replit.dev"),
}

INDICATORS: tuple[tuple[str, str, str], ...] = (
    ("Persistence / autostart", r"\\currentversion\\run|\\startup\\|schtasks\\s+/create", "high"),
    ("PowerShell with hidden window", r"powershell.{0,100}(-windowstyle\\s+hidden|-w\\s+hidden)", "high"),
    ("Encoded PowerShell command", r"powershell.{0,100}-enc(odedcommand)?\\s+[a-z0-9+/=]{20,}", "high"),
    ("Credential/browser data access hint", r"login data|cookies\\.sqlite|\\bpasswords?\\b.{0,40}decrypt", "medium"),
    ("Suspicious download-and-run pattern", r"(invoke-webrequest|downloadstring|urlopen).{0,160}(start-process|\\biex\\b|subprocess)", "high"),
    ("Dynamic code execution", r"\\beval\\s*\\(|new\\s+Function\\s*\\(|exec\\s*\\(", "medium"),
    ("Obfuscated content marker", r"frombase64string|\\batob\\s*\\(|base64\\.b64decode", "low"),
)
COMPILED_INDICATORS = tuple((name, re.compile(pattern, re.I), severity) for name, pattern, severity in INDICATORS)
SECRET_PATTERNS = (
    re.compile(r"sk-[A-Za-z0-9_-]{16,}"),
    re.compile(r"gh[pousr]_[A-Za-z0-9]{20,}"),
    re.compile(r"(?i)(api[_-]?key|secret|token)\\s*[:=]\\s*['\"][^'\"\\s]{8,}"),
)


def config_path() -> Path:
    if os.name == "nt":
        root = Path(os.environ.get("APPDATA", Path.home() / "AppData/Roaming"))
    else:
        root = Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config"))
    return root / "321code" / "security.json"


def save_scan_folder(folder: str) -> Path:
    target = Path(folder).expanduser().resolve()
    if not target.exists() or not target.is_dir():
        raise ValueError(f"Folder nie istnieje lub nie jest katalogiem: {target}")
    path = config_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(".tmp")
    temporary.write_text(json.dumps({"scan_folder": str(target)}, ensure_ascii=False, indent=2), encoding="utf-8")
    temporary.replace(path)
    return target


def load_scan_folder() -> Path:
    path = config_path()
    if not path.is_file():
        raise ValueError("Nie wybrano folderu. Najpierw wpisz: 321 cd <ścieżka>")
    try:
        folder = json.loads(path.read_text(encoding="utf-8")).get("scan_folder")
    except (OSError, json.JSONDecodeError, AttributeError):
        raise ValueError("Nie można odczytać ustawień skanera. Ustaw folder ponownie: 321 cd <ścieżka>")
    target = Path(folder).expanduser()
    if not target.is_dir():
        raise ValueError(f"Zapamiętany folder już nie istnieje: {target}")
    return target.resolve()


def _extract_strings(data: bytes) -> str:
    """Extract printable ASCII and UTF-16LE strings without executing the file."""
    parts = [data.decode("utf-8", errors="ignore")]
    parts.append(data.decode("utf-16le", errors="ignore"))
    parts.append(" ".join(x.decode("ascii", errors="ignore") for x in re.findall(rb"[ -~]{5,}", data)))
    return "\n".join(parts)


def _analyse_text(text: str) -> dict[str, Any]:
    lowered = text.lower()
    services = [name for name, needles in API_CATALOG.items() if any(n.lower() in lowered for n in needles)]
    findings = []
    for name, pattern, severity in COMPILED_INDICATORS:
        if pattern.search(text):
            findings.append({"name": name, "severity": severity})
    secrets = sum(1 for pattern in SECRET_PATTERNS if pattern.search(text))
    return {"apis": services, "findings": findings, "secret_patterns": secrets}


def scan_folder(folder: Path, seconds: float = MAX_SECONDS) -> dict[str, Any]:
    started = time.monotonic()
    deadline = started + min(max(seconds, 0.1), MAX_SECONDS)
    result: dict[str, Any] = {
        "target": str(folder), "files_seen": 0, "files_analysed": 0,
        "apis": set(), "findings": [], "secret_files": [], "skipped": 0,
        "timed_out": False,
    }
    for root, dirs, files in os.walk(folder):
        dirs[:] = [d for d in dirs if d not in {".git", "__pycache__", "node_modules", ".venv", "venv"}]
        for filename in files:
            if time.monotonic() >= deadline or result["files_seen"] >= MAX_FILES:
                result["timed_out"] = True
                break
            result["files_seen"] += 1
            path = Path(root) / filename
            try:
                if path.is_symlink() or not path.is_file() or path.stat().st_size > MAX_FILE_BYTES:
                    result["skipped"] += 1
                    continue
                data = path.read_bytes()
            except (OSError, PermissionError):
                result["skipped"] += 1
                continue
            analysis = _analyse_text(_extract_strings(data))
            result["files_analysed"] += 1
            result["apis"].update(analysis["apis"])
            if analysis["secret_patterns"]:
                result["secret_files"].append(str(path))
            if analysis["findings"]:
                result["findings"].append({
                    "file": str(path), "items": analysis["findings"]
                })
        if result["timed_out"]:
            break
    result["apis"] = sorted(result["apis"])
    result["elapsed"] = round(time.monotonic() - started, 2)
    result["severity"] = _overall_severity(result["findings"])
    return result


def _overall_severity(findings: list[dict[str, Any]]) -> str:
    levels = {item["severity"] for entry in findings for item in entry["items"]}
    if "high" in levels:
        return "HIGH"
    if "medium" in levels:
        return "MEDIUM"
    if "low" in levels:
        return "LOW"
    return "NO INDICATORS"


def _public_host(host: str) -> None:
    if not host or host.lower() in {"localhost", "localhost.localdomain"}:
        raise ValueError("Skanowanie adresów lokalnych jest zablokowane.")
    try:
        addresses = {ipaddress.ip_address(host)}
    except ValueError:
        try:
            addresses = {ipaddress.ip_address(item[4][0]) for item in socket.getaddrinfo(host, None)}
        except OSError as exc:
            raise ValueError(f"Nie można rozpoznać domeny: {host}") from exc
    if not addresses or any(not addr.is_global for addr in addresses):
        raise ValueError("Adres prowadzi do sieci prywatnej lub specjalnej — skanowanie zablokowane.")


class _SafeRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        parsed = urllib.parse.urlparse(newurl)
        if parsed.scheme not in {"http", "https"}:
            raise urllib.error.HTTPError(newurl, code, "Niedozwolony protokół przekierowania", headers, fp)
        _public_host(parsed.hostname or "")
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def scan_website(url: str, seconds: float = MAX_SECONDS) -> dict[str, Any]:
    started = time.monotonic()
    deadline = started + min(max(seconds, 0.1), MAX_SECONDS)
    parsed = urllib.parse.urlparse(url if "://" in url else "https://" + url)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        raise ValueError("Podaj poprawny adres http:// lub https://")
    _public_host(parsed.hostname)
    request_url = urllib.parse.urlunparse(parsed)
    request = urllib.request.Request(
        request_url, headers={"User-Agent": "321code-SecurityScanner/1.0", "Accept": "text/html,*/*;q=0.8"}
    )
    opener = urllib.request.build_opener(_SafeRedirect(), urllib.request.HTTPSHandler(context=ssl.create_default_context()))
    try:
        with opener.open(request, timeout=max(0.5, deadline - time.monotonic())) as response:
            body = response.read(MAX_WEB_BYTES + 1)
            if len(body) > MAX_WEB_BYTES:
                body = body[:MAX_WEB_BYTES]
            text = body.decode(response.headers.get_content_charset() or "utf-8", errors="replace")
            headers = {key.lower(): value for key, value in response.headers.items()}
            final_url = response.geturl()
            status = response.status
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        raise ValueError(f"Nie udało się pobrać strony: {exc}") from exc
    analysis = _analyse_text(text)
    links = sorted(set(re.findall(r"""(?:src|href)=["']([^"'#]+)["']""", text, re.I)))
    domains = set()
    for link in links:
        absolute = urllib.parse.urljoin(final_url, link)
        host = urllib.parse.urlparse(absolute).hostname
        if host and host != urllib.parse.urlparse(final_url).hostname:
            domains.add(host)
    security_headers = {
        "strict-transport-security": "HSTS",
        "content-security-policy": "CSP",
        "x-content-type-options": "X-Content-Type-Options",
        "x-frame-options": "X-Frame-Options",
        "referrer-policy": "Referrer-Policy",
    }
    return {
        "url": request_url, "final_url": final_url, "status": status,
        "https": urllib.parse.urlparse(final_url).scheme == "https",
        "security_headers": {label: key in headers for key, label in security_headers.items()},
        "apis": analysis["apis"], "findings": analysis["findings"],
        "external_domains": sorted(domains)[:50],
        "content_truncated": len(body) >= MAX_WEB_BYTES,
        "elapsed": round(time.monotonic() - started, 2),
        "severity": _overall_severity([{"items": analysis["findings"]}]) if analysis["findings"] else "NO INDICATORS",
        "note": "Analiza statyczna pobranej odpowiedzi. Brak wskaźników nie gwarantuje bezpieczeństwa.",
    }


def print_report(report: dict[str, Any], website: bool = False) -> None:
    line = "═" * 62
    print("\n" + line)
    print("  321 SECURITY SCANNER  |  RAPORT ANALIZY")
    print(line)
    if website:
        print(f"  Adres:       {report['url']}")
        print(f"  Końcowy URL: {report['final_url']}")
        print(f"  HTTP:        {report['status']}   HTTPS: {'TAK' if report['https'] else 'NIE'}")
        print("\n  NAGŁÓWKI BEZPIECZEŃSTWA")
        for name, present in report["security_headers"].items():
            print(f"  {'[OK]' if present else '[--]'} {name}")
        print(f"  Domeny zewnętrzne: {len(report['external_domains'])}")
    else:
        print(f"  Folder:      {report['target']}")
        print(f"  Pliki:       {report['files_analysed']}/{report['files_seen']} przeanalizowano")
        print(f"  Pominięte:   {report['skipped']}")
        if report["timed_out"]:
            print("  STATUS:      NIEPEŁNE SKANOWANIE (limit czasu/liczby plików)")
    print("\n  WYKRYTE USŁUGI / API")
    for api in report["apis"]:
        print(f"  [+] {api}")
    if not report["apis"]:
        print("  Nie znaleziono znanych identyfikatorów usług.")
    print("\n  PODEJRZANE WSKAŹNIKI")
    findings = report["findings"]
    if not findings:
        print("  Nie znaleziono wskaźników z użytych reguł.")
    for entry in findings[:30]:
        print(f"  [!] {entry.get('file', 'strona internetowa')}")
        for item in entry["items"]:
            print(f"      - {item['name']} ({item['severity'].upper()})")
    if not website and report["secret_files"]:
        print("\n  WZORCE POTENCJALNYCH SEKRETÓW (wartości ukryte)")
        for path in report["secret_files"][:20]:
            print(f"  [!] {path}")
    print(f"\n  OCENA WSKAŹNIKÓW: {report['severity']}")
    print(f"  Czas: {report['elapsed']} s")
    print("  Uwaga: wynik nie jest certyfikatem bezpieczeństwa.")
    print(line)
