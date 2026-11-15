"""Reliable, resumable trainer for the educational 321 TinyGPT model."""
from __future__ import annotations

import csv
import json
import math
import sys
import time
from pathlib import Path
from typing import Any


def load_training_text(project: Path, cfg: dict[str, Any]) -> str:
    filename = str(cfg.get("dataset_file", "dataset.txt"))
    dataset = (project / filename).resolve()
    if project.resolve() not in dataset.parents or not dataset.is_file():
        raise ValueError(f"Nie znaleziono pliku danych: {filename}")
    suffix = dataset.suffix.lower()
    if suffix in {".txt", ".md"}:
        raw = dataset.read_text(encoding="utf-8-sig")
        return "\n".join(line.rstrip() for line in raw.splitlines() if line.strip() and not line.lstrip().startswith("#"))
    if suffix == ".jsonl":
        records = []
        with dataset.open("r", encoding="utf-8-sig") as stream:
            for number, line in enumerate(stream, 1):
                if not line.strip():
                    continue
                try:
                    item = json.loads(line)
                except json.JSONDecodeError as exc:
                    raise ValueError(f"Błędny JSONL w linii {number}: {exc}") from exc
                if isinstance(item, dict) and isinstance(item.get("messages"), list):
                    for message in item["messages"]:
                        if isinstance(message, dict) and message.get("content"):
                            role = str(message.get("role", ""))
                            label = "Użytkownik" if role in {"user", "human"} else "AI" if role in {"assistant", "bot"} else "System"
                            records.append(f"{label}: {message['content']}")
                elif isinstance(item, dict):
                    prompt = item.get("prompt", item.get("instruction", item.get("input", "")))
                    answer = item.get("completion", item.get("output", item.get("response", "")))
                    if prompt or answer:
                        records.append(f"Użytkownik: {prompt}\nAI: {answer}")
                elif isinstance(item, str):
                    records.append(item)
        return "\n".join(records)
    if suffix == ".csv":
        records = []
        with dataset.open("r", encoding="utf-8-sig", newline="") as stream:
            for row in csv.DictReader(stream):
                prompt = row.get("prompt") or row.get("instruction") or row.get("input") or ""
                answer = row.get("completion") or row.get("output") or row.get("response") or ""
                if prompt or answer:
                    records.append(f"Użytkownik: {prompt}\nAI: {answer}")
                else:
                    records.append(" ".join(str(value) for value in row.values() if value))
        return "\n".join(records)
    raise ValueError("Obsługiwane formaty danych: .txt, .md, .jsonl, .csv")


def main(argv=None):
    args = sys.argv[1:] if argv is None else argv
    if len(args) != 1:
        print("Użycie: 321 ai train ścieżka/do/projektu")
        return 2
    project = Path(args[0]).expanduser().resolve()
    cfg_path = project / "config.json"
    if not cfg_path.is_file():
        print("Brak config.json.")
        return 2
    try:
        cfg = json.loads(cfg_path.read_text(encoding="utf-8"))
        raw = load_training_text(project, cfg)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"Błąd danych treningowych: {exc}")
        return 2
    data = raw.encode("utf-8")
    if len(data) < 2048:
        print("Zbiór jest za mały. Minimum techniczne: 2048 bajtów; sensowny model wymaga dużo większego i czystego zbioru.")
        return 2
    try:
        import torch
        from torch.nn import functional as F
        try:
            from .ai_model import TinyGPT
        except ImportError:
            from code321.ai_model import TinyGPT
    except ImportError as exc:
        print("Brak PyTorch. Zainstaluj: python -m pip install torch")
        print(exc)
        return 2

    try:
        steps = int(cfg.get("training_steps", 10000))
        width = int(cfg.get("width", 256))
        layers = int(cfg.get("layers", 6))
        heads = int(cfg.get("heads", 8))
        context = int(cfg.get("context", 256))
        batch = int(cfg.get("batch_size", 8))
        lr = float(cfg.get("learning_rate", 0.0003))
        dropout = float(cfg.get("dropout", 0.1))
        seed = int(cfg.get("seed", 321))
        eval_interval = max(1, int(cfg.get("eval_interval", max(10, min(500, steps // 50)))))
        save_interval = max(1, int(cfg.get("save_interval", eval_interval)))
        grad_accum = int(cfg.get("gradient_accumulation", 1))
    except (TypeError, ValueError) as exc:
        print(f"Nieprawidłowe parametry: {exc}")
        return 2
    valid = (
        1 <= steps <= 1_000_000 and 64 <= width <= 1024 and
        1 <= layers <= 24 and 1 <= heads <= 16 and width % heads == 0 and
        32 <= context <= 1024 and 1 <= batch <= 32 and
        0.00001 <= lr <= 0.01 and 0 <= dropout < 1 and
        1 <= grad_accum <= 32 and len(data) > context + 2
    )
    if not valid:
        print("Parametry poza dozwolonym zakresem lub dane krótsze niż kontekst.")
        return 2

    preference = str(cfg.get("device_preference", "auto")).strip().lower()
    cuda_available = torch.cuda.is_available()
    mps_available = bool(getattr(torch.backends, "mps", None) and torch.backends.mps.is_available())
    if preference in {"cpu"}:
        device = "cpu"
    elif preference in {"cuda", "cuda (nvidia)", "nvidia"}:
        if not cuda_available:
            print("Wybrano CUDA, ale PyTorch nie wykrywa zgodnej karty NVIDIA/CUDA.")
            return 2
        device = "cuda"
    elif preference in {"mps", "mps (apple)"}:
        if not mps_available:
            print("Wybrano MPS, ale PyTorch nie wykrywa obsługi Apple Silicon.")
            return 2
        device = "mps"
    else:
        device = "cuda" if cuda_available else "mps" if mps_available else "cpu"
    torch.manual_seed(seed)
    if device == "cuda":
        torch.cuda.manual_seed_all(seed)
        try:
            torch.cuda.set_per_process_memory_fraction(0.85)
        except (AttributeError, RuntimeError):
            pass
    ids = torch.tensor(list(data), dtype=torch.long)
    split = min(len(ids) - context - 1, max(context + 2, int(len(ids) * 0.95)))
    train_ids = ids[:split]
    val_ids = ids[split:]
    if len(val_ids) < context + 2:
        val_ids = train_ids[-min(len(train_ids), context * 4):]
    model_cfg = {
        "vocab_size": 256, "width": width, "layers": layers, "heads": heads,
        "context": context, "dropout": dropout,
    }
    model = TinyGPT(**model_cfg).to(device)
    optimizer = torch.optim.AdamW(model.parameters(), lr=lr, weight_decay=float(cfg.get("weight_decay", 0.1)))
    checkpoint_dir = project / "checkpoints"
    checkpoint_dir.mkdir(parents=True, exist_ok=True)
    latest = checkpoint_dir / "latest.pt"
    best_path = checkpoint_dir / "best.pt"
    start_step = 0
    best_val = math.inf
    if latest.exists() and cfg.get("resume", True):
        try:
            saved = torch.load(latest, map_location=device, weights_only=True)
            if saved.get("config") == model_cfg:
                model.load_state_dict(saved["state_dict"])
                optimizer.load_state_dict(saved["optimizer"])
                start_step = int(saved.get("step", 0))
                best_val = float(saved.get("best_val", math.inf))
                print(f"Wznowiono od kroku {start_step}.")
            else:
                print("Checkpoint ma inną architekturę — rozpoczynam nowy trening.")
        except Exception as exc:
            print(f"Checkpoint pominięty: {exc}")

    def make_batch(source):
        starts = torch.randint(0, len(source) - context - 1, (batch,))
        x = torch.stack([source[index:index + context] for index in starts]).to(device)
        y = torch.stack([source[index + 1:index + context + 1] for index in starts]).to(device)
        return x, y

    @torch.no_grad()
    def evaluate():
        model.eval()
        scores = []
        for _ in range(3):
            x, y = make_batch(val_ids)
            scores.append(F.cross_entropy(model(x).reshape(-1, 256), y.reshape(-1)).item())
        model.train()
        return sum(scores) / len(scores)

    parameters = sum(parameter.numel() for parameter in model.parameters())
    started = time.monotonic()
    print("=" * 68)
    print(f"321 AI TRAINER | {cfg.get('name', project.name)}")
    print(f"Urządzenie: {device.upper()} | Parametry: {parameters:,} | Dane: {len(data):,} bajtów")
    print(f"Architektura: {width=} {layers=} {heads=} {context=} {dropout=}")
    print(f"Trening: {steps:,} kroków | batch: {batch} × akumulacja: {grad_accum}")
    print("Checkpoint: co", save_interval, "kroków | Walidacja:", eval_interval)
    print("=" * 68, flush=True)

    model.train()
    last_loss = 0.0
    for step in range(start_step, steps):
        optimizer.zero_grad(set_to_none=True)
        for _ in range(grad_accum):
            x, y = make_batch(train_ids)
            logits = model(x)
            loss = F.cross_entropy(logits.reshape(-1, 256), y.reshape(-1))
            (loss / grad_accum).backward()
            last_loss = float(loss.detach())
        torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
        optimizer.step()
        current = step + 1
        should_eval = current % eval_interval == 0 or current == 1 or current == steps
        should_save = current % save_interval == 0 or current == steps
        val_loss = evaluate() if should_eval else None
        if val_loss is not None:
            improved = val_loss < best_val
            if improved:
                best_val = val_loss
                torch.save({"state_dict": model.state_dict(), "config": model_cfg, "step": current, "val_loss": best_val}, best_path)
            elapsed = time.monotonic() - started
            print(f"Krok {current:>7,}/{steps:,} | train {last_loss:.4f} | val {val_loss:.4f} | najlepszy {best_val:.4f} | {elapsed:.0f}s", flush=True)
        if should_save:
            torch.save({
                "state_dict": model.state_dict(), "optimizer": optimizer.state_dict(),
                "step": current, "config": model_cfg, "best_val": best_val,
            }, latest)

    model_dir = project / "model"
    model_dir.mkdir(parents=True, exist_ok=True)
    chosen = latest
    if best_path.exists():
        try:
            candidate = torch.load(best_path, map_location=device, weights_only=True)
            if candidate.get("config") == model_cfg:
                chosen = best_path
        except Exception:
            pass
    final = torch.load(chosen, map_location=device, weights_only=True)
    model.load_state_dict(final["state_dict"])
    model.cpu()
    torch.save({"state_dict": model.state_dict(), "config": model_cfg}, model_dir / "model.pt")
    info = {
        "name": cfg.get("name", project.name),
        "architecture": "321-TinyGPT (byte-level causal Transformer)",
        "trained_from_scratch": True,
        "training_steps": steps,
        "training_device": device,
        "dataset_file": cfg.get("dataset_file", "dataset.txt"),
        "dataset_bytes": len(data),
        "parameters": parameters,
        "model_config": model_cfg,
        "best_validation_loss": None if math.isinf(best_val) else best_val,
        "chat_format": "Użytkownik: ...\nAI: ...",
        "limitations": "Eksperymentalny model edukacyjny; nie jest modelem foundation ani zamiennikiem dużego pretrained LLM.",
    }
    (model_dir / "model_info.json").write_text(json.dumps(info, ensure_ascii=False, indent=2), encoding="utf-8")
    (project / "status.json").write_text(json.dumps({"status": "trained", "completed_steps": steps}, indent=2), encoding="utf-8")
    print(f"\nGotowe. Najlepszy model zapisano w: {model_dir}")
    print(f"Czat: 321 ai chat {project}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
