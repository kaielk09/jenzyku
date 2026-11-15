"""Shared inference runtime for trained 321 byte-level language models."""
from __future__ import annotations
import json
from pathlib import Path
from typing import Any

class ModelRuntime:
    def __init__(self, project: str | Path, device: str = "auto"):
        try:
            import torch
            from .ai_model import TinyGPT
        except ImportError as exc:
            raise RuntimeError("Uruchom: python -m pip install torch") from exc
        self.torch = torch
        self.project = Path(project).expanduser().resolve()
        artifact = self.project / "model" / "model.pt"
        if not artifact.is_file():
            raise FileNotFoundError(f"Brak wag modelu: {artifact}")
        self.device = self._device(device)
        saved = torch.load(artifact, map_location=self.device, weights_only=True)
        config = saved.get("config")
        if not isinstance(config, dict):
            raise ValueError("Checkpoint nie zawiera poprawnej konfiguracji.")
        self.model = TinyGPT(**config).to(self.device)
        self.model.load_state_dict(saved["state_dict"])
        self.model.eval()
        self.config = config
        info_path = self.project / "model" / "model_info.json"
        self.info = json.loads(info_path.read_text(encoding="utf-8")) if info_path.exists() else {}

    def _device(self, preference: str) -> str:
        torch = self.torch
        if preference == "auto":
            return "cuda" if torch.cuda.is_available() else "mps" if getattr(torch.backends, "mps", None) and torch.backends.mps.is_available() else "cpu"
        if preference == "cuda" and not torch.cuda.is_available():
            raise RuntimeError("CUDA nie jest dostępne.")
        if preference == "mps" and not (getattr(torch.backends, "mps", None) and torch.backends.mps.is_available()):
            raise RuntimeError("MPS nie jest dostępne.")
        if preference not in {"cpu", "cuda", "mps"}:
            raise ValueError("Urządzenie musi być auto/cpu/cuda/mps.")
        return preference

    @property
    def parameter_count(self) -> int:
        return sum(p.numel() for p in self.model.parameters())

    def generate(self, prompt: str, max_new_tokens: int = 160, temperature: float = 0.8,
                 top_k: int = 40, history: list[dict[str, str]] | None = None) -> str:
        if not isinstance(prompt, str) or not prompt.strip():
            raise ValueError("Prompt nie może być pusty.")
        if not 1 <= max_new_tokens <= 1024:
            raise ValueError("max_new_tokens musi należeć do zakresu 1–1024.")
        if not 0.05 <= temperature <= 2.0:
            raise ValueError("temperature musi należeć do zakresu 0.05–2.0.")
        if not 1 <= top_k <= 256:
            raise ValueError("top_k musi należeć do zakresu 1–256.")
        turns = []
        if history:
            for item in history[-8:]:
                role, content = item.get("role"), item.get("content")
                if role in {"user", "assistant"} and isinstance(content, str):
                    turns.append(("Użytkownik" if role == "user" else "AI") + ": " + content)
        turns.append("Użytkownik: " + prompt.strip() + "\nAI:")
        prefix = ("\n".join(turns)).encode("utf-8")[-max(32, self.config["context"] * 3):]
        torch = self.torch
        tokens = torch.tensor([list(prefix)], dtype=torch.long, device=self.device)
        with torch.inference_mode():
            for _ in range(max_new_tokens):
                logits = self.model(tokens[:, -self.config["context"]:])[:, -1, :] / temperature
                # Prevent most control bytes while retaining UTF-8 continuation bytes.
                logits[:, 0] = float("-inf")
                values, indices = torch.topk(logits, k=min(top_k, logits.shape[-1]), dim=-1)
                probs = torch.softmax(values, dim=-1)
                next_token = indices.gather(-1, torch.multinomial(probs, 1))
                tokens = torch.cat((tokens, next_token), dim=1)
                raw = bytes(tokens[0].tolist())
                if raw.endswith(b"\nUżytkownik:") or raw.endswith(b"\nU"):
                    break
        decoded = bytes(tokens[0].tolist()).decode("utf-8", errors="replace")
        answer = decoded.split("\nAI:", 1)[-1].split("\nUżytkownik:", 1)[0].strip()
        return answer or "(Model nie wygenerował odpowiedzi.)"
