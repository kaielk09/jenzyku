"""Task-aware dataset ingestion and deterministic quota balancing for 321 AI."""
from __future__ import annotations
import csv, json, random
from pathlib import Path
from typing import Any

ALIASES = {
    "programowanie": {"programowanie", "programming", "code", "coding", "developer"},
    "rozmowa": {"rozmowa", "conversation", "chat", "dialogue"},
    "rozumowanie": {"rozumowanie", "reasoning", "logic", "math", "problem_solving"},
}

def _category(record: dict[str, Any]) -> str | None:
    raw = record.get("category", record.get("task", record.get("type", record.get("tag"))))
    if raw is None: return None
    value = str(raw).strip().lower().replace("-", "_").replace(" ", "_")
    for canonical, aliases in ALIASES.items():
        if value in aliases or value == canonical: return canonical
    return None

def _record_text(record: dict[str, Any]) -> str:
    messages = record.get("messages")
    if isinstance(messages, list):
        lines = []
        for message in messages:
            if not isinstance(message, dict) or not message.get("content"): continue
            role = str(message.get("role", "")).lower()
            label = "Użytkownik" if role in {"user", "human"} else "AI" if role in {"assistant", "bot"} else "System"
            lines.append(f"{label}: {message['content']}")
        return "\n".join(lines)
    prompt = record.get("prompt", record.get("instruction", record.get("input", "")))
    answer = record.get("completion", record.get("output", record.get("response", "")))
    if prompt or answer: return f"Użytkownik: {prompt}\nAI: {answer}"
    return str(record.get("text", record.get("content", ""))).strip()

def _read_records(path: Path) -> list[tuple[str | None, str]]:
    records = []
    suffix = path.suffix.lower()
    if suffix in {".txt", ".md"}:
        raw = path.read_text(encoding="utf-8-sig")
        cleaned = "\n".join(line.rstrip() for line in raw.splitlines() if line.strip() and not line.lstrip().startswith("#"))
        if cleaned: records.append((None, cleaned))
    elif suffix == ".jsonl":
        with path.open("r", encoding="utf-8-sig") as stream:
            for number, line in enumerate(stream, 1):
                if not line.strip(): continue
                try: item = json.loads(line)
                except json.JSONDecodeError as exc: raise ValueError(f"Błędny JSONL w linii {number}: {exc}") from exc
                if isinstance(item, str): records.append((None, item))
                elif isinstance(item, dict):
                    value = _record_text(item)
                    if value: records.append((_category(item), value))
    elif suffix == ".csv":
        with path.open("r", encoding="utf-8-sig", newline="") as stream:
            for row in csv.DictReader(stream):
                value = _record_text(row)
                if value: records.append((_category(row), value))
    else: raise ValueError("Obsługiwane formaty danych: .txt, .md, .jsonl, .csv")
    return records

def load_task_training_text(project: Path, cfg: dict[str, Any]) -> tuple[str, list[str]]:
    filename = str(cfg.get("dataset_file", "dataset.txt"))
    dataset = (project / filename).resolve()
    if project.resolve() not in dataset.parents or not dataset.is_file():
        raise ValueError(f"Nie znaleziono pliku danych: {filename}")
    records = _read_records(dataset)
    if not records: raise ValueError("Zbiór danych nie zawiera żadnych przykładów tekstowych.")
    requested = cfg.get("task_mix") or {}
    quotas = {key: int(value) for key, value in requested.items() if key in ALIASES and int(value) > 0}
    if not quotas:
        return "\n\n".join(value for _, value in records), [f"Dane: {len(records):,} rekordów; bez podziału na zadania."]
    rng = random.Random(int(cfg.get("seed", 321)))
    tagged = {key: [value for category, value in records if category == key] for key in quotas}
    generic = [value for category, value in records if category is None]
    selected = []
    report = [f"Dane źródłowe: {len(records):,} rekordów."]
    for task, target in quotas.items():
        available = tagged[task]
        if not available and generic:
            report.append(f"UWAGA: brak oznaczonych przykładów „{task}”; używam wspólnego tekstu ogólnego.")
            available = generic
        if not available:
            raise ValueError(f"Brak przykładów dla zadania „{task}”. Dodaj rekordy JSONL/CSV z polem category/task albo wyłącz to zadanie.")
        rng.shuffle(available)
        selected.extend(available[i % len(available)] for i in range(target))
        mode = "powielanie" if target > len(tagged[task]) else "bez powielania"
        report.append(f"{task}: {len(tagged[task]):,} źródłowych → {target:,} użytych ({mode}).")
    rng.shuffle(selected)
    report.append(f"Łącznie do treningu: {len(selected):,} przykładów po balansowaniu.")
    return "\n\n".join(selected), report
