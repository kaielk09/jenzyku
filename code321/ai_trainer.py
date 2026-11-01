"""Train a small GPT-style model from a user-supplied text corpus."""
from __future__ import annotations

import json
import sys
from pathlib import Path


def main(argv: list[str] | None = None) -> int:
    args = sys.argv[1:] if argv is None else argv
    if len(args) != 1:
        print("Użycie: 321 ai train ścieżka/do/projektu")
        return 2
    project = Path(args[0]).expanduser().resolve()
    config_path, dataset = project / "config.json", project / "dataset.txt"
    if not config_path.is_file() or not dataset.is_file():
        print("Nie znaleziono config.json lub dataset.txt w folderze projektu.")
        return 2
    cfg = json.loads(config_path.read_text(encoding="utf-8"))
    raw = dataset.read_text(encoding="utf-8")
    text = "\n".join(line for line in raw.splitlines()
                      if line.strip() and not line.lstrip().startswith("#"))
    data = text.encode("utf-8")
    if len(data) < 512:
        print("Za mało danych. Dodaj co najmniej 512 bajtów sensownego tekstu do dataset.txt.")
        print("Dla modelu konwersacyjnego używaj przykładów w formacie:")
        print("Użytkownik: pytanie\nAI: odpowiedź")
        return 2
    try:
        import torch
        from torch.nn import functional as F
        try:
            from .ai_model import TinyGPT
        except ImportError:
            from code321.ai_model import TinyGPT
    except ImportError as exc:
        print("Brak PyTorch. Zainstaluj go poleceniem: python -m pip install torch")
        print(f"Szczegóły: {exc}")
        return 2
    steps = int(cfg.get("training_steps", 1000))
    if not 1 <= steps <= 1_000_000:
        print("Nieprawidłowa liczba kroków treningu.")
        return 2
    device = "cuda" if torch.cuda.is_available() else "cpu"
    if device == "cuda":
        try:
            torch.cuda.set_per_process_memory_fraction(0.70)
        except (AttributeError, RuntimeError):
            pass
    print(f"321 AI | Model: {cfg.get('name', project.name)}")
    print(f"Urządzenie: {device} | GPU wpisane w formularzu: {cfg.get('gpu_label', 'Auto')}")
    print(f"Dane: {len(data):,} bajtów | Kroki: {steps:,}")
    print("Trening modelu GPT od zera. Czas zależy od sprzętu i danych.")
    print("Mały model eksperymentalny nie osiągnie poziomu dużych chatbotów.")
    torch.manual_seed(321)
    ids = torch.tensor(list(data), dtype=torch.long)
    context, batch = 128, 8
    model = TinyGPT(context=context).to(device)
    optimizer = torch.optim.AdamW(model.parameters(), lr=3e-4, weight_decay=0.1)
    model.train()
    for step in range(steps):
        starts = torch.randint(0, len(ids) - context - 1, (batch,))
        x = torch.stack([ids[s:s + context] for s in starts]).to(device)
        y = torch.stack([ids[s + 1:s + context + 1] for s in starts]).to(device)
        logits = model(x)
        loss = F.cross_entropy(logits.reshape(-1, 256), y.reshape(-1))
        optimizer.zero_grad(set_to_none=True)
        loss.backward()
        torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
        optimizer.step()
        if (step + 1) % max(1, steps // 20) == 0 or step == 0:
            print(f"Krok {step + 1:,}/{steps:,} | loss={loss.item():.4f}", flush=True)
    model_dir = project / "model"
    model_dir.mkdir(exist_ok=True)
    torch.save({"state_dict": model.cpu().state_dict(),
                "config": {"vocab_size": 256, "width": 128, "layers": 4, "heads": 4, "context": context}},
               model_dir / "model.pt")
    info = {"name": cfg.get("name", project.name),
            "architecture": "321-TinyGPT (byte-level Transformer)",
            "trained_from_scratch": True, "training_steps": steps,
            "training_device": device, "dataset_bytes": len(data),
            "chat_format": "Użytkownik: ...\\nAI: ..."}
    (model_dir / "model_info.json").write_text(json.dumps(info, ensure_ascii=False, indent=2), encoding="utf-8")
    (project / "status.json").write_text(json.dumps({"status": "trained"}, indent=2), encoding="utf-8")
    print(f"Gotowe. Model zapisano w: {model_dir}")
    print(f"Aby go przetestować: 321 ai chat {project}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
