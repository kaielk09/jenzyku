"""321 AI Studio: library, export, continued training and chat."""
import json
import sys
import tkinter as tk
import zipfile
from pathlib import Path
from tkinter import filedialog, messagebox, ttk
from . import ai_model
from .ai_app import Creator, APP_DIR, BG, PANEL, PANEL_ALT, PURPLE, TEXT, MUTED, BORDER

MODELS = APP_DIR / "ai"
LEGACY_MODELS = Path.cwd() / "ai"
MODEL_DIRS = [MODELS] + ([LEGACY_MODELS] if LEGACY_MODELS.resolve() != MODELS.resolve() else [])

def read_json(path):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}

def trained(path):
    return (path / "model" / "model.pt").is_file()

def step_count(path, info, status):
    step = int(status.get("completed_steps", info.get("training_steps", 0)) or 0)
    metrics = path / "training_metrics.jsonl"
    if metrics.is_file():
        try:
            for line in metrics.read_text(encoding="utf-8").splitlines():
                if line.strip():
                    step = max(step, int(json.loads(line).get("step", 0)))
        except (OSError, ValueError, TypeError):
            pass
    return step

def export_zip(project, destination):
    source = Path(ai_model.__file__).resolve().parent
    with zipfile.ZipFile(destination, "w", zipfile.ZIP_DEFLATED) as z:
        z.write(source / "ai_model.py", "model-code/ai_model.py")
        if (source / "__init__.py").is_file():
            z.write(source / "__init__.py", "model-code/__init__.py")
        if (project / "config.json").is_file():
            z.write(project / "config.json", "model-code/config.json")
        z.writestr("model-code/README.md",
            "321 AI byte-level TinyGPT. Wlasna architektura PyTorch trenowana od zera. "
            "Nie jest bezposrednio zgodna z Transformers AutoModel.\n")
        for rel in ("model/model.pt", "model/model_info.json",
                    "checkpoints/latest.pt", "checkpoints/best.pt",
                    "training_metrics.jsonl", "status.json"):
            p = project / rel
            if p.is_file():
                z.write(p, "model-weights/" + p.name)

class Studio:
    def __init__(self, root):
        self.root, self.selected = root, None
        root.title("321 AI Studio")
        root.geometry("1080x720")
        root.minsize(850, 600)
        root.configure(bg=BG)
        # Prawdziwe maksymalizowanie Windows; systemowy pasek tytulu zostaje.
        if sys.platform == "win32":
            try:
                root.state("zoomed")
            except tk.TclError:
                pass
        root.bind("<F11>", self.toggle_maximize)
        self.build()
        self.refresh()

    def toggle_maximize(self, _event=None):
        try:
            self.root.state("normal" if self.root.state() == "zoomed" else "zoomed")
        except tk.TclError:
            pass

    def button(self, parent, text, command, primary=False):
        return tk.Button(parent, text=text, command=command,
            bg=PURPLE if primary else PANEL_ALT, fg="white",
            activebackground="#7545df", activeforeground="white",
            relief="flat", bd=0, font=("Segoe UI", 10, "bold"),
            cursor="hand2", padx=14, pady=10)

    def build(self):
        header = tk.Frame(self.root, bg=BG)
        header.pack(fill="x", padx=24, pady=20)
        tk.Label(header, text="321 AI STUDIO", bg=BG, fg=TEXT,
                 font=("Segoe UI", 21, "bold")).pack(side="left")
        self.button(header, "+ NOWY MODEL", self.new_model, True).pack(side="right")
        body = tk.Frame(self.root, bg=BG)
        body.pack(fill="both", expand=True, padx=24, pady=(0, 24))
        left = tk.Frame(body, bg=PANEL, highlightthickness=1, highlightbackground=BORDER)
        left.pack(side="left", fill="both", expand=True, padx=(0, 12))
        tk.Label(left, text="BIBLIOTEKA MODELI", bg=PANEL, fg=TEXT,
                 font=("Segoe UI", 11, "bold")).pack(anchor="w", padx=16, pady=14)
        self.tree = ttk.Treeview(left, columns=("state", "steps"), show="tree headings")
        self.tree.heading("#0", text="MODEL")
        self.tree.heading("state", text="STATUS")
        self.tree.heading("steps", text="KROKI")
        self.tree.column("#0", width=220)
        self.tree.column("state", width=100, anchor="center")
        self.tree.column("steps", width=90, anchor="center")
        style = ttk.Style()
        style.theme_use("clam")
        style.configure("Treeview", background=PANEL, fieldbackground=PANEL,
                        foreground=TEXT, rowheight=34)
        style.configure("Treeview.Heading", background=PANEL_ALT, foreground=TEXT)
        style.map("Treeview", background=[("selected", "#39265e")])
        self.tree.pack(fill="both", expand=True, padx=12, pady=(0, 12))
        self.tree.bind("<<TreeviewSelect>>", self.select)
        right = tk.Frame(body, bg=PANEL, width=360, highlightthickness=1, highlightbackground=BORDER)
        right.pack(side="right", fill="both")
        right.pack_propagate(False)
        tk.Label(right, text="SZCZEGÓŁY MODELU", bg=PANEL, fg=TEXT,
                 font=("Segoe UI", 11, "bold")).pack(anchor="w", padx=18, pady=18)
        self.title = tk.Label(right, text="Wybierz model", bg=PANEL, fg=TEXT,
                              font=("Segoe UI", 17, "bold"), wraplength=315)
        self.title.pack(anchor="w", padx=18)
        self.meta = tk.Label(right, text="Utwórz model, aby pojawił się na liście.",
                             bg=PANEL, fg=MUTED, justify="left", wraplength=315)
        self.meta.pack(anchor="w", padx=18, pady=14)
        ttk.Separator(right).pack(fill="x", padx=18, pady=6)
        self.download_btn = self.button(right, "↓  POBIERZ ZIP", self.download)
        self.download_btn.pack(fill="x", padx=18, pady=(16, 7))
        self.resume_btn = self.button(right, "↻  TRENUJ DALEJ", self.resume)
        self.resume_btn.pack(fill="x", padx=18, pady=7)
        self.chat_btn = self.button(right, "◉  CZAT Z MODELEM", self.chat, True)
        self.chat_btn.pack(fill="x", padx=18, pady=7)
        tk.Label(right, text="ZIP zawiera dwa foldery: model-code oraz model-weights. Pliki można ręcznie umieścić w GitHub i Hugging Face. Publikacja nie jest automatyczna.",
                 bg=PANEL, fg=MUTED, wraplength=315, justify="left",
                 font=("Segoe UI", 8)).pack(anchor="w", padx=18, pady=18)
        self.actions(False)

    def actions(self, enabled):
        for b in (self.download_btn, self.resume_btn, self.chat_btn):
            b.configure(state="normal" if enabled else "disabled")

    def refresh(self):
        old = str(self.selected) if self.selected else None
        for item in self.tree.get_children():
            self.tree.delete(item)
        MODELS.mkdir(parents=True, exist_ok=True)
        found = []
        candidates = []
        for folder in MODEL_DIRS:
            if folder.exists():
                candidates.extend(folder.iterdir())
        seen = set()
        for p in sorted(candidates, key=lambda x: x.name.lower()):
            if not p.is_dir() or not (p / "config.json").is_file() or p.resolve() in seen:
                continue
            seen.add(p.resolve())
            cfg = read_json(p / "config.json")
            info = read_json(p / "model" / "model_info.json")
            status = read_json(p / "status.json")
            step = step_count(p, info, status)
            state = "Gotowy" if trained(p) else ("Checkpoint" if (p / "checkpoints" / "latest.pt").exists() else "Utworzony")
            self.tree.insert("", "end", iid=str(p), text=cfg.get("name", p.name),
                             values=(state, f"{step:,}"))
            found.append(p)
        if old and self.tree.exists(old):
            self.tree.selection_set(old)
        elif found:
            self.tree.selection_set(found[0].name)
        else:
            self.selected = None
            self.title.configure(text="Brak modeli")
            self.meta.configure(text="Kliknij NOWY MODEL, aby rozpocząć.")
            self.actions(False)
        if self.tree.selection():
            self.select()
        self.root.after(4000, self.refresh)

    def select(self, _event=None):
        selection = self.tree.selection()
        if not selection:
            return
        p = Path(selection[0])
        self.selected = p
        cfg = read_json(p / "config.json")
        info = read_json(p / "model" / "model_info.json")
        status = read_json(p / "status.json")
        n = step_count(p, info, status)
        size = (p / "dataset.txt").stat().st_size if (p / "dataset.txt").exists() else 0
        meta = (f"Status: {'wytrenowany' if trained(p) else 'w trakcie / nieukończony'}\n"
                f"Kroki: {n:,}\nArchitektura: {info.get('architecture', '321 TinyGPT')}\n"
                f"Warstwy: {cfg.get('layers', '?')} • Głowice: {cfg.get('heads', '?')}\n"
                f"Szerokość: {cfg.get('width', '?')} • Kontekst: {cfg.get('context', '?')}\n"
                f"Dane: {size:,} bajtów")
        if info.get("best_validation_loss") is not None:
            meta += f"\nStrata walidacyjna: {info['best_validation_loss']:.4f}"
        self.title.configure(text=cfg.get("name", p.name))
        self.meta.configure(text=meta)
        self.actions(True)
        self.chat_btn.configure(state="normal" if trained(p) else "disabled")
        self.download_btn.configure(state="normal" if trained(p) else "disabled")
        self.resume_btn.configure(state="normal" if (p / "checkpoints" / "latest.pt").exists() else "disabled")

    def new_model(self):
        Creator(tk.Toplevel(self.root))

    def resume(self):
        if self.selected and (self.selected / "checkpoints" / "latest.pt").is_file():
            Creator(tk.Toplevel(self.root), resume_project=self.selected)
        else:
            messagebox.showinfo("321 AI", "Brak checkpointu do wznowienia.")

    def chat(self):
        if self.selected and trained(self.selected):
            from .ai_chat import Chat
            Chat(tk.Toplevel(self.root), self.selected)

    def download(self):
        if not self.selected or not trained(self.selected):
            return
        dest = filedialog.asksaveasfilename(parent=self.root,
            initialfile=self.selected.name + ".zip", defaultextension=".zip",
            filetypes=[("Archiwum ZIP", "*.zip")])
        if not dest:
            return
        try:
            export_zip(self.selected, Path(dest))
            messagebox.showinfo("321 AI", "Zapisano ZIP:\n" + dest)
        except OSError as exc:
            messagebox.showerror("321 AI", str(exc))

def main():
    root = tk.Tk()
    Studio(root)
    root.mainloop()
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
