from pathlib import Path

from code321.security_scanner import _analyse_text, save_scan_folder, load_scan_folder


def test_detects_known_api_provider():
    result = _analyse_text("client = 'https://api.openai.com/v1/responses'")
    assert "OpenAI" in result["apis"]


def test_detects_multiple_providers():
    result = _analyse_text("https://api.github.com and https://my.tosthost.pl/api")
    assert "GitHub" in result["apis"]
    assert "TostHost" in result["apis"]


def test_reports_suspicious_indicators():
    result = _analyse_text("powershell -windowstyle hidden")
    assert any(item["severity"] == "high" for item in result["findings"])


def test_folder_selection_persists(monkeypatch, tmp_path):
    config = tmp_path / "321code" / "security.json"
    monkeypatch.setattr("code321.security_scanner.config_path", lambda: config)
    selected = tmp_path / "project"
    selected.mkdir()
    assert save_scan_folder(str(selected)) == selected.resolve()
    assert load_scan_folder() == selected.resolve()
