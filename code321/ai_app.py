"""Modern 321 AI Creator desktop interface (Tkinter, no extra GUI dependencies)."""
from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

APP_DIR = Path.cwd()
BG = "#0b0b12"
PANEL = "#141421"
PANEL_ALT = "#1b1b2b"
PURPLE = "#8b5cf6"
PURPLE_HOVER = "#7545df"
TEXT = "#f4f1ff"
MUTED = "#a6a1b8"
GREEN = "#4ade80"
BORDER = "#29263a"


def safe_name(value: str) -> str:
    value = re.sub(r"[^A-Za-z0-9_-]+", "_", value.strip()).strip("_")
    if not value:
        raise ValueError("Wpisz nazwę zawierającą litery lub cyfry.")
    return value[:48]


class Creator:
    def __init__(self, root: tk.Tk):
        self.root = root
        root.title("321 AI Creator")
        root.geometry("900x900")
        root.minsize(780, 820)
        root.configure(bg=BG)

        self.name = tk.StringVar(value="MojModel")
        self.steps = tk.StringVar(value="10000")
        self.width = tk.StringVar(value="256")
        self.layers = tk.StringVar(value="6")
        self.heads = tk.StringVar(value="8")
        self.context = tk.StringVar(value="256")
        self.batch = tk.StringVar(value="8")
        self.learning_rate = tk.StringVar(value="0.0003")
        self.gpu = tk.StringVar(value="Auto")
        self.machine = tk.StringVar(value="Automatycznie")
        self.dataset = tk.StringVar()
        self.dataset_info = tk.StringVar(value="Nie wybrano pliku TXT")
        self.status = tk.StringVar(value="Gotowy do konfiguracji")
        self._style()
        self._build()
        self.dataset.trace_add("write", lambda *_: self._update_dataset_info())

    def _style(self):
        style = ttk.Style()
        style.theme_use("clam")
        style.configure("TCombobox", fieldbackground=PANEL_ALT, background=PANEL_ALT,
                        foreground=TEXT, arrowcolor=TEXT, bordercolor=BORDER,
                        lightcolor=BORDER, darkcolor=BORDER, padding=8)
        style.map("TCombobox", fieldbackground=[("readonly", PANEL_ALT)],
                  foreground=[("readonly", TEXT)])
        style.configure("Horizontal.TProgressbar", troughcolor=PANEL_ALT,
                        background=PURPLE, bordercolor=PANEL_ALT, lightcolor=PURPLE,
                        darkcolor=PURPLE)

    def _label(self, parent, text, color=MUTED, size=10, weight="normal"):
        return tk.Label(parent, text=text, bg=parent.cget("bg"), fg=color,
                        font=("Segoe UI", size, weight))

    def _card(self, parent, title, subtitle=None):
        card = tk.Frame(parent, bg=PANEL, highlightthickness=1, highlightbackground=BORDER)
        tk.Label(card, text=title, bg=PANEL, fg=TEXT,
                 font=("Segoe UI", 12, "bold")).pack(anchor="w", padx=18, pady=(15, 2))
        if subtitle:
            tk.Label(card, text=subtitle, bg=PANEL, fg=MUTED,
                     font=("Segoe UI", 9), wraplength=700, justify="left").pack(
                         anchor="w", padx=18, pady=(0, 12))
        return card

    def _entry(self, parent, variable, width=None):
        entry = tk.Entry(parent, textvariable=variable, bg=PANEL_ALT, fg=TEXT,
                         insertbackground=TEXT, relief="flat", font=("Segoe UI", 11),
                         highlightthickness=1, highlightbackground=BORDER,
                         highlightcolor=PURPLE)
        if width:
            entry.configure(width=width)
        entry.pack(fill="x", ipady=10, padx=18, pady=(5, 14))
        return entry

    def _button(self, parent, text, command=None, primary=False, width=None):
        color = PURPLE if primary else PANEL_ALT
        button = tk.Button(parent, text=text, command=command, bg=color, fg="white",
                           activebackground=PURPLE_HOVER if primary else "#29263d",
                           activeforeground="white", relief="flat", bd=0,
                           font=("Segoe UI", 10, "bold"), cursor="hand2",
                           padx=16, pady=10, width=width)
        return button

    def _build(self):
        header = tk.Frame(self.root, bg=BG)
        header.pack(fill="x", padx=28, pady=(22, 16))
        mark = tk.Frame(header, bg=PURPLE, width=48, height=48)
        mark.pack(side="left")
        mark.pack_propagate(False)
        tk.Label(mark, text="321", bg=PURPLE, fg="white",
                 font=("Segoe UI", 15, "bold")).place(relx=.5, rely=.5, anchor="center")
        titles = tk.Frame(header, bg=BG)
        titles.pack(side="left", padx=14)
        tk.Label(titles, text="321 AI CREATOR", bg=BG, fg=TEXT,
                 font=("Segoe UI", 19, "bold")).pack(anchor="w")
        tk.Label(titles, text="Studio tworzenia własnych modeli językowych",
                 bg=BG, fg=MUTED, font=("Segoe UI", 9)).pack(anchor="w")
        tk.Label(header, text="BETA", bg="#241b3b", fg="#c4b5fd",
                 font=("Segoe UI", 9, "bold"), padx=12, pady=6).pack(side="right", pady=8)

        content = tk.Frame(self.root, bg=BG)
        content.pack(fill="both", expand=True, padx=28)
        intro = tk.Frame(content, bg=BG)
        intro.pack(fill="x", pady=(0, 14))
        tk.Label(intro, text="Nowy projekt AI", bg=BG, fg=TEXT,
                 font=("Segoe UI", 16, "bold")).pack(anchor="w")
        tk.Label(intro, text="Ustaw parametry, dodaj zbiór danych i rozpocznij trening od zera.",
                 bg=BG, fg=MUTED, font=("Segoe UI", 10)).pack(anchor="w", pady=(3, 0))

        model = self._card(content, "01  •  Model", "Podstawowe informacje o projekcie.")
        model.pack(fill="x", pady=(0, 12))
        grid = tk.Frame(model, bg=PANEL)
        grid.pack(fill="x", padx=18, pady=(0, 4))
        left = tk.Frame(grid, bg=PANEL)
        right = tk.Frame(grid, bg=PANEL)
        left.pack(side="left", fill="x", expand=True, padx=(0, 10))
        right.pack(side="left", fill="x", expand=True, padx=(10, 0))
        self._label(left, "NAZWA MODELU", size=9, weight="bold").pack(anchor="w")
        name_row = tk.Frame(left, bg=PANEL)
        name_row.pack(fill="x", pady=(5, 14))
        tk.Entry(name_row, textvariable=self.name, bg=PANEL_ALT, fg=TEXT,
                 insertbackground=TEXT, relief="flat", font=("Segoe UI", 11),
                 highlightthickness=1, highlightbackground=BORDER,
                 highlightcolor=PURPLE).pack(side="left", fill="x", expand=True, ipady=10)
        self._label(right, "LICZBA KROKÓW TRENINGU", size=9, weight="bold").pack(anchor="w")
        steps_row = tk.Frame(right, bg=PANEL)
        steps_row.pack(fill="x", pady=(5, 14))
        ttk.Combobox(steps_row, textvariable=self.steps,
                     values=("1000", "5000", "10000", "25000", "50000", "100000"),
                     state="normal", font=("Segoe UI", 10)).pack(side="left", fill="x", expand=True, ipady=5)
        tk.Label(steps_row, text="kroków", bg=PANEL, fg=MUTED,
                 font=("Segoe UI", 9)).pack(side="left", padx=(8, 0))

        advanced = self._card(content, "02  •  Architektura AI", "Konfiguruj wielkość sieci. Większe modele wymagają więcej pamięci i mocniejszego sprzętu.")
        advanced.pack(fill="x", pady=(0, 12))
        settings = tk.Frame(advanced, bg=PANEL)
        settings.pack(fill="x", padx=18, pady=(0, 14))
        options = [
            ("SZEROKOŚĆ", self.width, ("128", "256", "384", "512", "768")),
            ("WARSTWY", self.layers, ("4", "6", "8", "12", "16")),
            ("GŁOWICE", self.heads, ("4", "8", "12", "16")),
            ("KONTEKST", self.context, ("128", "256", "512", "1024")),
            ("BATCH", self.batch, ("4", "8", "16", "32")),
            ("LEARNING RATE", self.learning_rate, ("0.001", "0.0005", "0.0003", "0.0001")),
        ]
        for i, (label, variable, values) in enumerate(options):
            col = tk.Frame(settings, bg=PANEL)
            col.grid(row=i // 3, column=i % 3, sticky="ew", padx=5, pady=5)
            settings.grid_columnconfigure(i % 3, weight=1)
            self._label(col, label, size=8, weight="bold").pack(anchor="w", pady=(0, 4))
            ttk.Combobox(col, textvariable=variable, values=values, state="readonly").pack(fill="x", ipady=3)

        hardware = self._card(content, "03  •  Sprzęt", "Wybór jest informacyjny. Dostępne urządzenie obliczeniowe wykrywa PyTorch.")
        hardware.pack(fill="x", pady=(0, 12))
        hwrow = tk.Frame(hardware, bg=PANEL)
        hwrow.pack(fill="x", padx=18, pady=(0, 16))
        for label, variable, values in (
            ("URZĄDZENIE", self.machine, ("Automatycznie", "Komputer", "Laptop")),
            ("GPU (OPCJONALNIE)", self.gpu, ("Auto", "NVIDIA", "AMD", "Intel", "CPU")),
        ):
            col = tk.Frame(hwrow, bg=PANEL)
            col.pack(side="left", fill="x", expand=True, padx=(0, 12))
            self._label(col, label, size=9, weight="bold").pack(anchor="w", pady=(0, 6))
            ttk.Combobox(col, textvariable=variable, values=values,
                         state="readonly").pack(fill="x", ipady=4)

        data = self._card(content, "04  •  Dane treningowe",
                          "Wybierz plik TXT. Możesz też użyć przycisku AI — jego funkcja zostanie dodana w przyszłości.")
        data.pack(fill="x", pady=(0, 12))
        file_row = tk.Frame(data, bg=PANEL)
        file_row.pack(fill="x", padx=18, pady=(0, 8))
        tk.Entry(file_row, textvariable=self.dataset, bg=PANEL_ALT, fg=TEXT,
                 insertbackground=TEXT, relief="flat", font=("Segoe UI", 10),
                 highlightthickness=1, highlightbackground=BORDER).pack(
                     side="left", fill="x", expand=True, ipady=11)
        self._button(file_row, "AI", self.open_text_dialog).pack(side="left", padx=(8, 6))
        self._button(file_row, "WYBIERZ TXT", self.browse).pack(side="left")
        tk.Label(data, textvariable=self.dataset_info, bg=PANEL, fg=MUTED,
                 font=("Segoe UI", 9)).pack(anchor="w", padx=18, pady=(0, 14))

        note = tk.Frame(content, bg="#171426", highlightthickness=1, highlightbackground="#3b2d59")
        note.pack(fill="x", pady=(0, 12))
        tk.Label(note, text="ⓘ  Warto wiedzieć", bg="#171426", fg="#c4b5fd",
                 font=("Segoe UI", 10, "bold")).pack(anchor="w", padx=14, pady=(10, 2))
        tk.Label(note, text="To mały model eksperymentalny trenowany od zera. Nie będzie działał jak duży chatbot bez dużego i dobrego zbioru danych. Trening może długo obciążać komputer.",
                 bg="#171426", fg="#c4bfd0", font=("Segoe UI", 9),
                 wraplength=790, justify="left").pack(anchor="w", padx=14, pady=(0, 10))

        footer = tk.Frame(self.root, bg=BG)
        footer.pack(fill="x", padx=28, pady=(2, 20))
        tk.Label(footer, textvariable=self.status, bg=BG, fg=MUTED,
                 font=("Segoe UI", 9)).pack(side="left")
        self._button(footer, "UTWÓRZ MODEL  →", self.create, primary=True).pack(side="right")

    def open_text_dialog(self):
        win = tk.Toplevel(self.root)
        win.title("321 AI • Wklej tekst")
        win.geometry("680x520")
        win.minsize(560, 420)
        win.configure(bg=BG)
        win.transient(self.root)
        tk.Label(win, text="Dodaj własne dane treningowe", bg=BG, fg=TEXT,
                 font=("Segoe UI", 16, "bold")).pack(anchor="w", padx=22, pady=(20, 4))
        tk.Label(win, text="Wklej lub wpisz tekst. Zostanie zapisany jako plik TXT na tym komputerze.",
                 bg=BG, fg=MUTED, font=("Segoe UI", 9)).pack(anchor="w", padx=22, pady=(0, 12))
        editor_frame = tk.Frame(win, bg=PANEL, highlightthickness=1, highlightbackground=BORDER)
        editor_frame.pack(fill="both", expand=True, padx=22, pady=(0, 12))
        editor = tk.Text(editor_frame, bg=PANEL_ALT, fg=TEXT, insertbackground=TEXT,
                         wrap="word", relief="flat", font=("Segoe UI", 10),
                         padx=12, pady=12, undo=True)
        scroll = ttk.Scrollbar(editor_frame, command=editor.yview)
        editor.configure(yscrollcommand=scroll.set)
        editor.pack(side="left", fill="both", expand=True)
        scroll.pack(side="right", fill="y")
        bottom = tk.Frame(win, bg=BG)
        bottom.pack(fill="x", padx=22, pady=(0, 20))
        tk.Label(bottom, text="Zapis nastąpi po kliknięciu DALEJ.", bg=BG,
                 fg=MUTED, font=("Segoe UI", 9)).pack(side="left")
        def save_text():
            value = editor.get("1.0", "end-1c").strip()
            if len(value.encode("utf-8")) < 512:
                messagebox.showwarning("Za mało danych", "Wklej co najmniej 512 bajtów tekstu.", parent=win)
                return
            try:
                folder = APP_DIR / "ai_datasets"
                folder.mkdir(parents=True, exist_ok=True)
                filename = safe_name(self.name.get() or "dataset") + "_dataset.txt"
                path = folder / filename
                path.write_text(value + "\n", encoding="utf-8")
                self.dataset.set(str(path))
                self.status.set("Zapisano dane: " + path.name)
                win.destroy()
            except (OSError, ValueError) as exc:
                messagebox.showerror("Nie udało się zapisać TXT", str(exc), parent=win)
        self._button(bottom, "DALEJ  →", save_text, primary=True).pack(side="right")

    def browse(self):
        path = filedialog.askopenfilename(
            title="Wybierz dane treningowe",
            filetypes=[("Pliki tekstowe", "*.txt"), ("Wszystkie pliki", "*.*")]
        )
        if path:
            self.dataset.set(path)

    def _update_dataset_info(self):
        raw = self.dataset.get().strip()
        if not raw:
            self.dataset_info.set("Nie wybrano pliku TXT")
            return
        path = Path(raw).expanduser()
        if not path.is_file():
            self.dataset_info.set("Wybrany plik nie istnieje.")
            return
        size = path.stat().st_size
        self.dataset_info.set(f"✓  {path.name}   •   {size:,} bajtów   •   {'Dane gotowe' if size >= 512 and path.suffix.lower() == '.txt' else 'Sprawdź format lub rozmiar pliku'}")

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
            if int(self.width.get()) % int(self.heads.get()) != 0:
                raise ValueError("Szerokość modelu musi być podzielna przez liczbę głowic.")
            project = APP_DIR / "ai" / name
            project.mkdir(parents=True, exist_ok=False)
            cfg = {
                "name": name,
                "training_steps": steps,
                "gpu_label": self.gpu.get().strip() or "Auto",
                "device_preference": "auto",
                "machine_type": self.machine.get(),
                "width": int(self.width.get()),
                "layers": int(self.layers.get()),
                "heads": int(self.heads.get()),
                "context": int(self.context.get()),
                "batch_size": int(self.batch.get()),
                "learning_rate": float(self.learning_rate.get()),
                "status": "training",
            }
            (project / "config.json").write_text(
                json.dumps(cfg, ensure_ascii=False, indent=2), encoding="utf-8"
            )
            shutil.copy2(source, project / "dataset.txt")
            trainer = Path(__file__).resolve().with_name("ai_trainer.py")
            cmd = [sys.executable, str(trainer), str(project)]
            if sys.platform == "win32":
                subprocess.Popen(["cmd", "/k", *cmd], cwd=str(project))
            else:
                subprocess.Popen(cmd, cwd=str(project))
            self.status.set(f"Projekt utworzony: {name}")
            messagebox.showinfo(
                "321 AI Creator",
                f"Projekt „{name}” został utworzony.\n\nTrening uruchomił się w osobnym oknie terminala.\nFolder: {project}"
            )
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
