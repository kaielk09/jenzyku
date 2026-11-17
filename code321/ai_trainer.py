"""Train a small 321code GPT from UTF-8 text, with validation and resumable checkpoints."""
from __future__ import annotations

import json
import math
import random
import sys
import time
from pathlib import Path


def _load_dataset(path: Path) -> bytes:
    text = path.read_text(encoding="utf-8-sig")
    blocks = [part.strip() for part in text.replace("\r\n", "\n").split("\n\n") if part.strip()]
    if not blocks:
        raise ValueError("Zbiór danych jest pusty.")
    # Keep conversation/example blocks together when possible.
    return "\n\n".join(blocks).encode("utf-8")


def _atomic_save(torch, payload: dict, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    torch.save(payload, temporary)
    temporary.replace(path)


def main(argv=None) -> int:
    args = sys.argv[1:] if argv is None else argv
    if len(args) != 1:
        print("Użycie: 321 ai train ścieżka/do/projektu")
        return 2
    project = Path(args[0]).expanduser().resolve()
    cfg_path, dataset = project / "config.json", project / "dataset.txt"
    if not cfg_path.is_file() or not dataset.is_file():
        print("Brak config.json lub dataset.txt.")
        return 2
    try:
        cfg = json.loads(cfg_path.read_text(encoding="utf-8"))
        raw = _load_dataset(dataset)
    except (OSError, UnicodeError, json.JSONDecodeError, ValueError) as exc:
        print(f"Nie można wczytać danych: {exc}")
        return 2
    if len(raw) < 2048:
        print("Za mało danych: minimum techniczne to 2048 bajtów UTF-8.")
        return 2

    try:
        import torch
        from torch.nn import functional as F
        try:
            from .ai_model import TinyGPT
        except ImportError:
            from code321.ai_model import TinyGPT
    except ImportError:
        print("Brak PyTorch. Zainstaluj: python -m pip install torch")
        return 2

    try:
        steps = int(cfg.get("training_steps", 10000))
        width = int(cfg.get("width", 256))
        layers = int(cfg.get("layers", 6))
        heads = int(cfg.get("heads", 8))
        context = int(cfg.get("context", 256))
        batch_size = int(cfg.get("batch_size", 8))
        accumulation = int(cfg.get("gradient_accumulation", 1))
        learning_rate = float(cfg.get("learning_rate", 0.0003))
        min_lr = float(cfg.get("min_learning_rate", learning_rate * 0.1))
        seed = int(cfg.get("seed", 321))
    except (TypeError, ValueError) as exc:
        print(f"Nieprawidłowa konfiguracja: {exc}")
        return 2
    if not (1 <= steps <= 1_000_000 and 64 <= width <= 1024 and
            1 <= layers <= 24 and 1 <= heads <= 16 and width % heads == 0 and
            32 <= context <= 1024 and 1 <= batch_size <= 32 and
            1 <= accumulation <= 32 and 0.000001 <= learning_rate <= 0.01 and
            0 <= min_lr <= learning_rate):
        print("Parametry treningu są poza dozwolonym zakresem.")
        return 2
    if len(raw) <= context * 2 + 16:
        print("Zbiór danych jest za krótki dla wybranego kontekstu.")
        return 2

    random.seed(seed)
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)
    preference = str(cfg.get("device_preference", "auto")).lower()
    if preference == "cuda" and not torch.cuda.is_available():
        print("Wybrano CUDA, ale PyTorch nie wykrywa zgodnego GPU.")
        return 2
    device = "cuda" if preference != "cpu" and torch.cuda.is_available() else "cpu"
    if device == "cuda":
        torch.backends.cuda.matmul.allow_tf32 = True
        torch.backends.cudnn.allow_tf32 = True

    # Prefer splitting on blank-line boundaries so a conversation is not split in half.
    blocks = [part.strip().encode("utf-8") for part in dataset.read_text(encoding="utf-8-sig").replace("\r\n", "\n").split("\n\n") if part.strip()]
    if len(blocks) >= 5:
        random.shuffle(blocks)
        val_count = max(1, int(len(blocks) * 0.2))
        val_bytes = b"\n\n".join(blocks[:val_count])
        train_bytes = b"\n\n".join(blocks[val_count:])
    else:
        split = int(len(raw) * 0.8)
        train_bytes, val_bytes = raw[:split], raw[split:]
    train_ids = torch.tensor(list(train_bytes), dtype=torch.long)
    val_ids = torch.tensor(list(val_bytes), dtype=torch.long)
    if len(train_ids) <= context + 1 or len(val_ids) <= context + 1:
        print("Za mało danych treningowych lub walidacyjnych. Dodaj więcej przykładów.")
        return 2

    model_cfg = {"vocab_size": 256, "width": width, "layers": layers,
                 "heads": heads, "context": context}
    model = TinyGPT(**model_cfg).to(device)
    optimizer = torch.optim.AdamW(model.parameters(), lr=learning_rate, weight_decay=0.1)
    scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=max(1, steps), eta_min=min_lr)
    checkpoint_dir = project / "checkpoints"
    latest_path, best_path = checkpoint_dir / "latest.pt", checkpoint_dir / "best.pt"
    metrics_path = project / "training_metrics.jsonl"
    start_step, best_val = 0, float("inf")

    if latest_path.is_file():
        try:
            saved = torch.load(latest_path, map_location=device, weights_only=True)
            if saved.get("config") == model_cfg:
                model.load_state_dict(saved["state_dict"])
                if "optimizer" in saved:
                    optimizer.load_state_dict(saved["optimizer"])
                if "scheduler" in saved:
                    scheduler.load_state_dict(saved["scheduler"])
                start_step = int(saved.get("step", 0))
                best_val = float(saved.get("best_val", best_val))
                print(f"Wznowiono trening od kroku {start_step}.")
            else:
                print("Checkpoint ma inną architekturę — rozpoczynam nowy trening.")
        except Exception as exc:
            print(f"Nie udało się wznowić checkpointu: {exc}")

    if start_step == 0:
        metrics_path.write_text("", encoding="utf-8")

    def sample_batch(source):
        starts = torch.randint(0, len(source) - context - 1, (batch_size,))
        x = torch.stack([source[i:i + context] for i in starts]).to(device)
        y = torch.stack([source[i + 1:i + context + 1] for i in starts]).to(device)
        return x, y

    @torch.no_grad()
    def validate():
        model.eval()
        scores = []
        for _ in range(8):
            x, y = sample_batch(val_ids)
            logits = model(x)
            scores.append(F.cross_entropy(logits.reshape(-1, 256), y.reshape(-1)).item())
        model.train()
        return sum(scores) / len(scores)

    parameter_count = sum(p.numel() for p in model.parameters())
    interval = max(1, min(250, steps // 50 or 1))
    started = time.time()
    model.train()
    print(f"321 AI | {cfg.get('name', project.name)} | {device} | {parameter_count:,} parametrów")
    print(f"Dane: {len(raw):,} bajtów | trening: {len(train_ids):,} | walidacja: {len(val_ids):,}")
    print(f"Efektywny batch: {batch_size * accumulation} | cel: {steps:,} kroków")
    optimizer.zero_grad(set_to_none=True)

    for step in range(start_step, steps):
        total_loss = 0.0
        for _ in range(accumulation):
            x, y = sample_batch(train_ids)
            logits = model(x)
            loss = F.cross_entropy(logits.reshape(-1, 256), y.reshape(-1))
            (loss / accumulation).backward()
            total_loss += loss.item()
        torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
        optimizer.step()
        optimizer.zero_grad(set_to_none=True)
        scheduler.step()

        if (step + 1) % interval == 0 or step == start_step or step + 1 == steps:
            val_loss = validate()
            elapsed = time.time() - started
            current_lr = optimizer.param_groups[0]["lr"]
            record = {"step": step + 1, "train_loss": total_loss / accumulation,
                      "validation_loss": val_loss, "learning_rate": current_lr,
                      "elapsed_seconds": round(elapsed, 2)}
            with metrics_path.open("a", encoding="utf-8") as log:
                log.write(json.dumps(record) + "\n")
            payload = {"state_dict": model.state_dict(), "optimizer": optimizer.state_dict(),
                       "scheduler": scheduler.state_dict(), "step": step + 1,
                       "best_val": min(best_val, val_loss), "config": model_cfg, "seed": seed}
            _atomic_save(torch, payload, latest_path)
            if val_loss < best_val:
                best_val = val_loss
                _atomic_save(torch, {"state_dict": model.state_dict(), "config": model_cfg,
                                     "step": step + 1, "validation_loss": best_val}, best_path)
            print(f"Krok {step + 1:,}/{steps:,} | train {total_loss / accumulation:.4f} | "
                  f"val {val_loss:.4f} | lr {current_lr:.2g} | {elapsed:.0f}s", flush=True)

    model_dir = project / "model"
    model_dir.mkdir(parents=True, exist_ok=True)
    model.cpu()
    _atomic_save(torch, {"state_dict": model.state_dict(), "config": model_cfg,
                         "training_steps": steps, "validation_loss": best_val}, model_dir / "model.pt")
    info = {
        "name": cfg.get("name", project.name),
        "architecture": "321-TinyGPT (byte-level causal Transformer)",
        "trained_from_scratch": True,
        "training_steps": steps,
        "training_device": device,
        "dataset_bytes": len(raw),
        "parameters": parameter_count,
        "model_config": model_cfg,
        "best_validation_loss": best_val,
        "chat_format": "Użytkownik: ...\nAI: ...",
        "checkpoint": str(latest_path),
    }
    (model_dir / "model_info.json").write_text(json.dumps(info, ensure_ascii=False, indent=2), encoding="utf-8")
    (project / "status.json").write_text(json.dumps(
        {"status": "trained", "completed_steps": steps, "best_validation_loss": best_val},
        ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\nGotowe. Model zapisano w: {model_dir}\nTest: 321 ai chat {project}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
