"""Desktop chat window for a trained 321 AI model."""
from __future__ import annotations

import sys
import threading
import tkinter as tk
from pathlib import Path
from tkinter import messagebox


class Chat:
    def __init__(self, root: tk.Tk, project: Path):
        self.root, self.project = root, project
        root.title(f"321 AI — {project.name}")
        root.geometry("760x600")
        root.configure(bg="#101018")
        self.output = tk.Text(root, bg="#191827", fg="#eeeafc", insertbackground="white",
                              wrap="word", relief="flat", font=("Arial", 11), padx=12, pady=12)
        self.output.pack(fill="both", expand=True, padx=14, pady=(14, 8))
        self.output.insert("end", f"321 AI: Witaj! Testujesz model {project.name}.\n")
        self.output.configure(state="disabled")
        bottom = tk.Frame(root, bg="#101018")
        bottom.pack(fill="x", padx=14, pady=(0, 14))
        self.entry = tk.Entry(bottom, bg="#242333", fg="white", insertbackground="white",
                              relief="flat", font=("Arial", 12))
        self.entry.pack(side="left", fill="x", expand=True, ipady=12)
        self.entry.bind("<Return>", lambda _event: self.send())
        tk.Button(bottom, text="WYŚLIJ", command=self.send, bg="#7c3aed", fg="white",
                  relief="flat", font=("Arial", 10, "bold"), padx=20, pady=10).pack(side="left", padx=(8, 0))
        self.model = None
        self.load_model()

    def append(self, text: str):
        self.output.configure(state="normal")
        self.output.insert("end", text + "\n")
        self.output.see("end")
        self.output.configure(state="disabled")

    def load_model(self):
        try:
            import torch
            try:
                from .ai_model import TinyGPT
            except ImportError:
                from code321.ai_model import TinyGPT
            saved = torch.load(self.project / "model" / "model.pt", map_location="cpu", weights_only=True)
            self.model = TinyGPT(**saved["config"])
            self.model.load_state_dict(saved["state_dict"])
            self.model.eval()
            self.torch = torch
        except Exception as exc:
            messagebox.showerror("321 AI", f"Nie udało się otworzyć modelu: {exc}")
            self.root.destroy()

    def generate(self, prompt: str) -> str:
        torch = self.torch
        ids = torch.tensor([list(("Użytkownik: " + prompt + "\nAI:").encode("utf-8"))], dtype=torch.long)
        with torch.no_grad():
            for _ in range(240):
                logits = self.model(ids[:, -128:])[:, -1, :] / 0.9
                logits[:, :9] = -float("inf")
                values, indices = torch.topk(logits, k=30, dim=-1)
                probs = torch.softmax(values, dim=-1)
                nxt = indices.gather(-1, torch.multinomial(probs, num_samples=1))
                ids = torch.cat([ids, nxt], dim=1)
                if bytes(ids[0].tolist()).endswith(b"\nUżytkownik:"):
                    break
        generated = bytes(ids[0].tolist()).decode("utf-8", errors="replace")
        answer = generated.split("\nAI:", 1)[-1].split("\nUżytkownik:", 1)[0].strip()
        return answer or "(Model nie wygenerował odpowiedzi.)"

    def send(self):
        prompt = self.entry.get().strip()
        if not prompt:
            return
        self.entry.delete(0, "end")
        self.append("Ty: " + prompt)
        self.append("321 AI: generuję odpowiedź...")
        def work():
            try:
                answer = self.generate(prompt)
            except Exception as exc:
                answer = f"Błąd generowania: {exc}"
            self.root.after(0, lambda: self.append("321 AI: " + answer))
        threading.Thread(target=work, daemon=True).start()


def main(argv: list[str] | None = None) -> int:
    args = sys.argv[1:] if argv is None else argv
    if len(args) != 1:
        print("Użycie: 321 ai chat ścieżka/do/projektu")
        return 2
    project = Path(args[0]).expanduser().resolve()
    if not (project / "model" / "model.pt").is_file():
        print("Nie znaleziono wytrenowanego modelu. Najpierw: 321 ai train " + str(project))
        return 2
    root = tk.Tk()
    Chat(root, project)
    root.mainloop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
