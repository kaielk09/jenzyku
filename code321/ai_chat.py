"""Polished desktop chat for a trained 321 AI model."""
from __future__ import annotations

import sys
import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk


BG = "#0b0b12"
PANEL = "#151522"
PANEL_ALT = "#1c1b2b"
PURPLE = "#9565f5"
TEXT = "#f4f1ff"
MUTED = "#aaa4bd"
BORDER = "#2b2940"


class Chat:
    def __init__(self, root: tk.Tk, project: Path):
        self.root, self.project = root, project
        root.title(f"321 AI Studio — {project.name}")
        root.geometry("920x700")
        root.minsize(680, 520)
        root.configure(bg=BG)
        self.temperature = tk.DoubleVar(value=0.85)
        self.max_tokens = tk.IntVar(value=240)
        self.status = tk.StringVar(value="Ładowanie modelu…")
        self.busy = False
        self._layout()
        self.model = None
        self.load_model()

    def label(self, parent, text, size=10, color=TEXT, bold=False):
        return tk.Label(parent, text=text, bg=parent.cget("bg"), fg=color,
                        font=("Segoe UI", size, "bold" if bold else "normal"))

    def button(self, parent, text, command, primary=False):
        return tk.Button(parent, text=text, command=command,
                         bg=PURPLE if primary else PANEL_ALT, fg="white",
                         activebackground="#7045cf", activeforeground="white",
                         relief="flat", bd=0, padx=16, pady=9,
                         font=("Segoe UI", 9, "bold"), cursor="hand2")

    def _layout(self):
        header = tk.Frame(self.root, bg=BG)
        header.pack(fill="x", padx=22, pady=(18, 12))
        self.label(header, "321 AI", 19, TEXT, True).pack(side="left")
        self.label(header, self.project.name, 10, MUTED).pack(side="left", padx=12, pady=(6, 0))
        self.label(header, "MODEL CHAT", 8, "#c4b5fd", True).pack(side="right", pady=(8, 0))

        self.output = tk.Text(self.root, bg=PANEL, fg=TEXT, insertbackground=TEXT,
                              wrap="word", relief="flat", font=("Segoe UI", 10),
                              padx=18, pady=16, spacing1=4, spacing3=8,
                              highlightthickness=1, highlightbackground=BORDER)
        self.output.pack(fill="both", expand=True, padx=22, pady=(0, 12))
        self.output.tag_configure("user", foreground="#c4b5fd", font=("Segoe UI", 10, "bold"))
        self.output.tag_configure("assistant", foreground="#7ee0b0", font=("Segoe UI", 10, "bold"))
        self.output.tag_configure("body", foreground=TEXT)
        self.output.insert("end", "321 AI\n", "assistant")
        self.output.insert("end", "To lokalny czat z wytrenowanym modelem. Jakość odpowiedzi zależy od danych treningowych.\n\n", "body")
        self.output.configure(state="disabled")

        controls = tk.Frame(self.root, bg=BG)
        controls.pack(fill="x", padx=22, pady=(0, 8))
        self.label(controls, "Temperatura", 8, MUTED).pack(side="left")
        ttk.Scale(controls, from_=0.2, to=1.5, variable=self.temperature,
                  orient="horizontal", length=120).pack(side="left", padx=(8, 16))
        self.label(controls, "Maks. tokenów", 8, MUTED).pack(side="left")
        ttk.Combobox(controls, textvariable=self.max_tokens, values=(64, 128, 240, 400, 600),
                     width=6, state="readonly").pack(side="left", padx=8)
        self.button(controls, "Wyczyść", self.clear).pack(side="right")
        self.button(controls, "Eksportuj", self.export).pack(side="right", padx=8)

        bottom = tk.Frame(self.root, bg=BG)
        bottom.pack(fill="x", padx=22, pady=(0, 8))
        self.entry = tk.Text(bottom, height=3, bg=PANEL_ALT, fg=TEXT,
                             insertbackground=TEXT, wrap="word", relief="flat",
                             font=("Segoe UI", 10), padx=12, pady=10,
                             highlightthickness=1, highlightbackground=BORDER)
        self.entry.pack(side="left", fill="x", expand=True)
        self.entry.bind("<Control-Return>", lambda _event: self.send())
        self.button(bottom, "WYŚLIJ  ↑", self.send, True).pack(side="left", padx=(10, 0), fill="y")
        footer = tk.Frame(self.root, bg=BG)
        footer.pack(fill="x", padx=22, pady=(0, 12))
        tk.Label(footer, textvariable=self.status, bg=BG, fg=MUTED,
                 font=("Segoe UI", 8)).pack(side="left")
        self.label(footer, "Ctrl + Enter aby wysłać", 8, MUTED).pack(side="right")

    def append(self, speaker: str, text: str):
        self.output.configure(state="normal")
        tag = "user" if speaker == "Ty" else "assistant"
        self.output.insert("end", speaker + "\n", tag)
        self.output.insert("end", text + "\n\n", "body")
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
            self.status.set(f"Model gotowy • {sum(p.numel() for p in self.model.parameters()):,} parametrów")
        except Exception as exc:
            messagebox.showerror("321 AI", f"Nie udało się otworzyć modelu: {exc}")
            self.root.destroy()

    def generate(self, prompt: str) -> str:
        torch = self.torch
        prefix = ("Użytkownik: " + prompt + "\nAI:").encode("utf-8")
        ids = torch.tensor([list(prefix)], dtype=torch.long)
        temperature = max(0.2, min(1.5, float(self.temperature.get())))
        limit = max(16, min(800, int(self.max_tokens.get())))
        with torch.inference_mode():
            for _ in range(limit):
                logits = self.model(ids[:, -self.context:])[:, -1, :] / temperature
                logits[:, :9] = -float("inf")
                values, indices = torch.topk(logits, k=min(40, logits.shape[-1]), dim=-1)
                probabilities = torch.softmax(values, dim=-1)
                next_token = indices.gather(-1, torch.multinomial(probabilities, num_samples=1))
                ids = torch.cat([ids, next_token], dim=1)
                if bytes(ids[0].tolist()).endswith(b"\nU"):
                    break
        generated = bytes(ids[0].tolist()).decode("utf-8", errors="replace")
        answer = generated.split("\nAI:", 1)[-1].split("\nUżytkownik:", 1)[0].strip()
        return answer or "(Model nie wygenerował odpowiedzi.)"

    def send(self):
        if self.busy or self.model is None:
            return
        prompt = self.entry.get("1.0", "end-1c").strip()
        if not prompt:
            return
        self.entry.delete("1.0", "end")
        self.append("Ty", prompt)
        self.busy = True
        self.status.set("Model generuje odpowiedź…")
        def work():
            try:
                answer = self.generate(prompt)
            except Exception as exc:
                answer = f"Błąd generowania: {exc}"
            self.root.after(0, lambda: self._finish(answer))
        threading.Thread(target=work, daemon=True).start()

    def _finish(self, answer: str):
        self.append("321 AI", answer)
        self.busy = False
        self.status.set("Gotowy")

    def clear(self):
        self.output.configure(state="normal")
        self.output.delete("1.0", "end")
        self.output.insert("end", "Historia została wyczyszczona.\n\n", "body")
        self.output.configure(state="disabled")

    def export(self):
        path = filedialog.asksaveasfilename(
            title="Zapisz rozmowę", defaultextension=".txt",
            filetypes=[("Plik tekstowy", "*.txt")],
            initialfile=f"{self.project.name}_chat.txt",
        )
        if path:
            content = self.output.get("1.0", "end-1c")
            Path(path).write_text(content, encoding="utf-8")
            self.status.set("Zapisano rozmowę")


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
