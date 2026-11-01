"""321 AI Creator desktop application."""
from __future__ import annotations

import json
import re
import shutil
import subprocess
import sys
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox

APP_DIR = Path.cwd()


def safe_name(value: str) -> str:
    value = re.sub(r"[^A-Za-z0-9_-]+", "_", value.strip()).strip("_")
    if not value:
        raise ValueError("Wpisz nazwę z literami lub cyframi.")
    return value[:48]


class Creator:
    def __init__(self, root: tk.Tk):
        self.root = root
        root.title("321 AI Creator")
        root.geometry("560x690")
        root.resizable(False, False)
        root.configure(bg="#101018")
        tk.Label(root, text="A", font=("Arial", 76, "bold"), fg="#a78bfa", bg="#101018").pack(pady=(8, 0))
        tk.Label(root, text="321 AI CREATOR", font=("Arial", 19, "bold"), fg="white", bg="#101018").pack(pady=(0, 12))
        self.name = self.field("Nazwa nowego modelu AI", "MojModel")
        self.steps = self.field("Liczba kroków treningu", "29000")
        self.gpu = self.field("Model karty graficznej (informacyjnie)", "Auto")
        tk.Label(root, text="Rodzaj urządzenia", fg="#d8d4e8", bg="#101018",
                 font=("Arial", 11, "bold")).pack(anchor="w", padx=42, pady=(12, 5))
        self.machine = tk.StringVar(value="Komputer")
        row = tk.Frame(root, bg="#101018")
        row.pack(anchor="w", padx=42)
        for value in ("Komputer", "Laptop"):
            tk.Radiobutton(row, text=value, value=value, variable=self.machine, fg="white",
                           selectcolor="#29243a", bg="#101018", activebackground="#101018",
                           activeforeground="white").pack(side="left", padx=(0, 18))
        tk.Label(root, text="Wybierz plik TXT z danymi, na których model ma się uczyć.",
                 fg="#d8d4e8", bg="#101018", wraplength=440, justify="left").pack(anchor="w", padx=42, pady=(18, 6))
        self.dataset = tk.StringVar()
        dsrow = tk.Frame(root, bg="#101018")
        dsrow.pack(fill="x", padx=42)
        tk.Entry(dsrow, textvariable=self.dataset, bg="#242333", fg="white",
                 insertbackground="white", relief="flat").pack(side="left", fill="x", expand=True, ipady=9)
        tk.Button(dsrow, text="WYBIERZ", command=self.browse, bg="#38304e", fg="white",
                  relief="flat").pack(side="left", padx=(6, 0), ipady=5)
        tk.Label(root, text="Model powstaje od zera. Jego wiedza i jakość będą zależeć od dostarczonych danych.",
                 wraplength=450, fg="#aaa6bb", bg="#101018", font=("Arial", 9)).pack(pady=18)
        tk.Button(root, text="CREATE MODEL", command=self.create, bg="#7c3aed", fg="white",
                  activebackground="#6d28d9", activeforeground="white", relief="flat",
                  font=("Arial", 14, "bold"), width=26, height=2).pack(pady=8)

    def field(self, label: str, default: str) -> tk.Entry:
        tk.Label(self.root, text=label, fg="#d8d4e8", bg="#101018",
                 font=("Arial", 11, "bold")).pack(anchor="w", padx=42, pady=(8, 5))
        entry = tk.Entry(self.root, bg="#242333", fg="white", insertbackground="white",
                         relief="flat", font=("Arial", 12))
        entry.pack(fill="x", padx=42, ipady=9)
        entry.insert(0, default)
        return entry

    def browse(self):
        path = filedialog.askopenfilename(title="Wybierz dane treningowe",
            filetypes=[("Pliki tekstowe", "*.txt"), ("Wszystkie pliki", "*.*")])
        if path:
            self.dataset.set(path)

    def create(self):
        try:
            name = safe_name(self.name.get())
            steps = int(self.steps.get().replace(" ", "").replace("_", ""))
            if not 1 <= steps <= 1_000_000:
                raise ValueError("Liczba kroków musi być od 1 do 1 000 000.")
            source = Path(self.dataset.get()).expanduser()
            if not source.is_file() or source.suffix.lower() != ".txt":
                raise ValueError("Wybierz istniejący plik .txt z danymi treningowymi.")
            if source.stat().st_size < 512:
                raise ValueError("Plik jest za mały. Dodaj co najmniej 512 bajtów tekstu.")
            project = APP_DIR / "ai" / name
            project.mkdir(parents=True, exist_ok=False)
            cfg = {"name": name, "training_steps": steps, "gpu_label": self.gpu.get().strip() or "Auto",
                   "device_preference": "auto", "machine_type": self.machine.get(), "status": "training"}
            (project / "config.json").write_text(json.dumps(cfg, ensure_ascii=False, indent=2), encoding="utf-8")
            shutil.copy2(source, project / "dataset.txt")
            trainer = Path(__file__).resolve().with_name("ai_trainer.py")
            cmd = [sys.executable, str(trainer), str(project)]
            if sys.platform == "win32":
                subprocess.Popen(["cmd", "/k", *cmd], cwd=str(project))
            else:
                subprocess.Popen(cmd, cwd=str(project))
            self.root.destroy()
        except FileExistsError:
            messagebox.showerror("321 AI", "Folder o takiej nazwie już istnieje.")
        except (ValueError, OSError) as exc:
            messagebox.showerror("321 AI", str(exc))


def main() -> int:
    root = tk.Tk()
    Creator(root)
    root.mainloop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
