"""Desktop chat for a trained 321code GPT model."""
from __future__ import annotations

import sys
import threading
import tkinter as tk
from pathlib import Path
from tkinter import messagebox


class Chat:
    def __init__(self, root: tk.Tk, project: Path):
        self.root, self.project = root, project
        self.history: list[tuple[str, str]] = []
        root.title(f"321 AI — {project.name}")
        root.geometry("1100x760")
        root.minsize(680, 500)
        root.configure(bg="#101018")
        if sys.platform == "win32":
            try:
                root.state("zoomed")
            except tk.TclError:
                pass
        root.bind("<F11>", self.toggle_maximize)
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
        self.send_button = tk.Button(bottom, text="WYŚLIJ", command=self.send, bg="#7c3aed", fg="white",
                                      relief="flat", font=("Arial", 10, "bold"), padx=20, pady=10)
        self.send_button.pack(side="left", padx=(8, 0))
        self.model = None
        self.load_model()

    def toggle_maximize(self, _event=None):
        try:
            self.root.state("normal" if self.root.state() == "zoomed" else "zoomed")
        except tk.TclError:
            pass

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
            self.context = int(saved["config"].get("context", 128))
            self.model.load_state_dict(saved["state_dict"])
            self.model.eval()
            self.torch = torch
        except Exception as exc:
            messagebox.showerror("321 AI", f"Nie udało się otworzyć modelu: {exc}")
            self.root.destroy()

    def generate(self, prompt: str) -> str:
        torch = self.torch
        previous = self.history[-4:]
        conversation = "".join(f"Użytkownik: {q}\nAI: {a}\n" for q, a in previous)
        conversation += f"Użytkownik: {prompt}\nAI:"
        ids = torch.tensor([list(conversation.encode("utf-8"))], dtype=torch.long)
        temperature = 0.8
        top_k = 40
        max_new_tokens = 400
        with torch.inference_mode():
            for _ in range(max_new_tokens):
                logits = self.model(ids[:, -self.context:])[:, -1, :] / max(temperature, 0.05)
                # Avoid control bytes while retaining all valid UTF-8 bytes.
                logits[:, :9] = -float("inf")
                if top_k:
                    values, indices = torch.topk(logits, k=min(top_k, logits.shape[-1]), dim=-1)
                    filtered = torch.full_like(logits, -float("inf"))
                    filtered.scatter_(1, indices, values)
                    logits = filtered
                probs = torch.softmax(logits, dim=-1)
                next_token = torch.multinomial(probs, num_samples=1)
                ids = torch.cat([ids, next_token], dim=1)
                generated = bytes(ids[0].tolist())
                if generated.endswith(b"\nU\xc5\xbcytkownik:"):
                    break
        generated_text = bytes(ids[0].tolist()).decode("utf-8", errors="replace")
        answer = generated_text.rsplit("\nAI:", 1)[-1].split("\nUżytkownik:", 1)[0].strip()
        return answer or "(Model nie wygenerował odpowiedzi.)"

    def send(self):
        prompt = self.entry.get().strip()
        if not prompt:
            return
        self.entry.delete(0, "end")
        self.append("Ty: " + prompt)
        self.append("321 AI: generuję odpowiedź...")
        self.send_button.configure(state="disabled")
        def work():
            try:
                answer = self.generate(prompt)
                self.history.append((prompt, answer))
            except Exception as exc:
                answer = f"Błąd generowania: {exc}"
            def finish():
                self.append("321 AI: " + answer)
                self.send_button.configure(state="normal")
            self.root.after(0, finish)
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
