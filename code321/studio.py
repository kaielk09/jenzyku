"""321code Studio: a polished desktop hub for projects, AI and security."""
from __future__ import annotations

import os
import subprocess
import sys
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

BG = "#0b0b12"
SIDEBAR = "#10101a"
PANEL = "#151522"
PANEL_2 = "#1c1b2b"
PURPLE = "#9565f5"
PURPLE_DARK = "#6f45cf"
TEXT = "#f4f1ff"
MUTED = "#aaa4bd"
BORDER = "#2b2940"
GREEN = "#58d69a"
YELLOW = "#f0bd69"


class Studio:
    def __init__(self, root: tk.Tk):
        self.root = root
        root.title("321code Studio")
        root.geometry("1120x760")
        root.minsize(900, 620)
        root.configure(bg=BG)
        self.status = tk.StringVar(value="Wszystkie systemy gotowe")
        self.active = tk.StringVar(value="dashboard")
        self._style()
        self._layout()
        self.show("dashboard")

    def _style(self):
        style = ttk.Style()
        style.theme_use("clam")
        style.configure("Treeview", background=PANEL_2, fieldbackground=PANEL_2,
                        foreground=TEXT, rowheight=30, borderwidth=0)
        style.configure("Treeview.Heading", background=SIDEBAR, foreground=MUTED,
                        relief="flat", font=("Segoe UI", 9, "bold"))
        style.map("Treeview", background=[("selected", PURPLE_DARK)])
        style.configure("TProgressbar", troughcolor=PANEL_2, background=PURPLE)

    def _label(self, parent, value, size=10, color=TEXT, bold=False, **kwargs):
        return tk.Label(parent, text=value, bg=parent.cget("bg"), fg=color,
                        font=("Segoe UI", size, "bold" if bold else "normal"), **kwargs)

    def _button(self, parent, value, command, primary=False, width=None):
        return tk.Button(parent, text=value, command=command,
                         bg=PURPLE if primary else PANEL_2, fg="white",
                         activebackground=PURPLE_DARK, activeforeground="white",
                         relief="flat", bd=0, cursor="hand2",
                         font=("Segoe UI", 9, "bold"), padx=15, pady=10, width=width)

    def _card(self, parent, title, subtitle=""):
        card = tk.Frame(parent, bg=PANEL, highlightthickness=1, highlightbackground=BORDER)
        self._label(card, title, 12, TEXT, True).pack(anchor="w", padx=18, pady=(16, 4))
        if subtitle:
            self._label(card, subtitle, 9, MUTED, wraplength=680, justify="left").pack(
                anchor="w", padx=18, pady=(0, 14))
        return card

    def _layout(self):
        shell = tk.Frame(self.root, bg=BG)
        shell.pack(fill="both", expand=True)
        self.sidebar = tk.Frame(shell, bg=SIDEBAR, width=220)
        self.sidebar.pack(side="left", fill="y")
        self.sidebar.pack_propagate(False)
        brand = tk.Frame(self.sidebar, bg=SIDEBAR)
        brand.pack(fill="x", padx=20, pady=(24, 28))
        mark = tk.Frame(brand, bg=PURPLE, width=42, height=42)
        mark.pack(side="left")
        mark.pack_propagate(False)
        self._label(mark, "321", 13, "white", True).place(relx=.5, rely=.5, anchor="center")
        names = tk.Frame(brand, bg=SIDEBAR)
        names.pack(side="left", padx=11)
        self._label(names, "321CODE", 13, TEXT, True).pack(anchor="w")
        self._label(names, "STUDIO", 8, MUTED, True).pack(anchor="w")
        self._label(self.sidebar, "WORKSPACE", 8, "#716b85", True).pack(anchor="w", padx=20, pady=(0, 8))
        nav = [
            ("dashboard", "⌂   Pulpit"),
            ("projects", "▦   Projekty"),
            ("ai", "✦   321 AI Studio"),
            ("security", "◇   Security Scanner"),
            ("language", "⌘   Język 321code"),
            ("settings", "⚙   Ustawienia"),
        ]
        self.nav_buttons = {}
        for key, label in nav:
            btn = tk.Button(self.sidebar, text=label, anchor="w", command=lambda k=key: self.show(k),
                            bg=SIDEBAR, fg=TEXT if key == "dashboard" else MUTED,
                            activebackground=PANEL_2, activeforeground=TEXT,
                            relief="flat", bd=0, padx=20, pady=12,
                            font=("Segoe UI", 10, "bold" if key == "dashboard" else "normal"),
                            cursor="hand2")
            btn.pack(fill="x", padx=10, pady=2)
            self.nav_buttons[key] = btn
        bottom = tk.Frame(self.sidebar, bg=SIDEBAR)
        bottom.pack(side="bottom", fill="x", padx=20, pady=20)
        self._label(bottom, "321code  •  Desktop Edition", 8, MUTED).pack(anchor="w")
        self._label(bottom, "Local-first workspace", 8, "#716b85").pack(anchor="w", pady=(3, 0))

        main = tk.Frame(shell, bg=BG)
        main.pack(side="left", fill="both", expand=True)
        top = tk.Frame(main, bg=BG, height=68)
        top.pack(fill="x", padx=28, pady=(18, 4))
        top.pack_propagate(False)
        self.page_title = self._label(top, "Pulpit", 18, TEXT, True)
        self.page_title.pack(side="left", anchor="center")
        self._label(top, "●  LOCAL WORKSPACE", 8, GREEN, True).pack(side="right", anchor="center")
        self.body = tk.Frame(main, bg=BG)
        self.body.pack(fill="both", expand=True, padx=28, pady=(10, 8))
        footer = tk.Frame(main, bg=SIDEBAR, height=30)
        footer.pack(fill="x", side="bottom")
        footer.pack_propagate(False)
        self._label(footer, "321code Studio", 8, MUTED).pack(side="left", padx=14, pady=6)
        tk.Label(footer, textvariable=self.status, bg=SIDEBAR, fg=MUTED,
                 font=("Segoe UI", 8)).pack(side="right", padx=14)

    def show(self, page: str):
        self.active.set(page)
        for key, btn in self.nav_buttons.items():
            btn.configure(bg="#242039" if key == page else SIDEBAR,
                          fg=TEXT if key == page else MUTED)
        for child in self.body.winfo_children():
            child.destroy()
        titles = {"dashboard":"Pulpit", "projects":"Projekty", "ai":"321 AI Studio",
                  "security":"Security Scanner", "language":"Język 321code", "settings":"Ustawienia"}
        self.page_title.configure(text=titles.get(page, "321code Studio"))
        getattr(self, "_page_" + page)()

    def _page_dashboard(self):
        self._label(self.body, "Witaj w 321code Studio", 22, TEXT, True).pack(anchor="w", pady=(10, 4))
        self._label(self.body, "Jedno miejsce do tworzenia programów, modeli AI i analizowania plików.", 10, MUTED).pack(anchor="w", pady=(0, 20))
        cards = tk.Frame(self.body, bg=BG)
        cards.pack(fill="x")
        for title, value, detail, color in [
            ("JĘZYK", "321code", "Interpreter i projekty .321", PURPLE),
            ("AI STUDIO", "Model Lab", "Tworzenie i trening modeli", GREEN),
            ("SECURITY", "Scanner", "Analiza statyczna plików i WWW", YELLOW),
        ]:
            card = tk.Frame(cards, bg=PANEL, highlightthickness=1, highlightbackground=BORDER)
            card.pack(side="left", fill="both", expand=True, padx=(0, 10), ipady=12)
            self._label(card, title, 8, color, True).pack(anchor="w", padx=16, pady=(10, 8))
            self._label(card, value, 17, TEXT, True).pack(anchor="w", padx=16)
            self._label(card, detail, 8, MUTED).pack(anchor="w", padx=16, pady=(4, 10))
        quick = self._card(self.body, "Szybki start", "Najczęściej używane działania")
        quick.pack(fill="x", pady=18)
        row = tk.Frame(quick, bg=PANEL)
        row.pack(fill="x", padx=18, pady=(0, 18))
        self._button(row, "＋  Nowy projekt", self.new_project, True).pack(side="left", padx=(0, 8))
        self._button(row, "✦  Otwórz 321 AI", self.open_ai).pack(side="left", padx=8)
        self._button(row, "◇  Skanuj stronę", lambda: self.show("security")).pack(side="left", padx=8)
        info = self._card(self.body, "Wskazówka", "321 AI trenuje mały model od zera. Jakość zależy od danych, architektury i czasu treningu — sam kreator nie zamieni małego modelu w duży model klasy komercyjnej.")
        info.pack(fill="x")

    def _page_projects(self):
        header = tk.Frame(self.body, bg=BG)
        header.pack(fill="x", pady=(6, 14))
        self._label(header, "Twoje lokalne projekty 321code", 16, TEXT, True).pack(side="left")
        self._button(header, "＋  Nowy projekt", self.new_project, True).pack(side="right")
        card = self._card(self.body, "Foldery projektów", "Wybierz katalog, aby otworzyć go w Eksploratorze plików.")
        card.pack(fill="both", expand=True)
        self.project_tree = ttk.Treeview(card, columns=("path",), show="headings")
        self.project_tree.heading("path", text="ŚCIEŻKA")
        self.project_tree.pack(fill="both", expand=True, padx=16, pady=(0, 12))
        roots = [Path.cwd() / "projects", Path.cwd() / "ai"]
        for root in roots:
            if root.is_dir():
                for child in sorted(root.iterdir()):
                    if child.is_dir():
                        self.project_tree.insert("", "end", values=(str(child),))
        self._button(card, "Otwórz zaznaczony folder", self.open_selected_project).pack(anchor="e", padx=16, pady=(0, 16))

    def _page_ai(self):
        self._label(self.body, "AI Model Lab", 22, TEXT, True).pack(anchor="w", pady=(8, 4))
        self._label(self.body, "Konfiguruj dane, architekturę, trening i testuj zapisane modele.", 10, MUTED).pack(anchor="w", pady=(0, 18))
        for title, desc, command in [
            ("Kreator modelu", "Utwórz projekt AI, dobierz parametry i zbiór danych.", self.open_ai),
            ("Otwórz istniejący model", "Wybierz folder projektu, aby uruchomić czat z modelem.", self.open_model),
            ("Trening z terminala", "Uruchom trening dla istniejącego folderu projektu.", self.train_model),
        ]:
            card = self._card(self.body, title, desc)
            card.pack(fill="x", pady=6)
            self._button(card, "Otwórz  →", command, True).pack(anchor="e", padx=18, pady=(0, 16))
        note = self._card(self.body, "Uczciwa informacja o możliwościach", "Aktualny silnik to eksperymentalny byte-level Transformer. Jest dobry do nauki i eksperymentów, ale nie jest gotowym modelem klasy GPT-4/Qwen. Aby uzyskać lepsze odpowiedzi, potrzebne są wysokiej jakości dane, większy tokenizer/model i odpowiedni sprzęt.")
        note.pack(fill="x", pady=8)

    def _page_security(self):
        self._label(self.body, "321 Security Scanner", 22, TEXT, True).pack(anchor="w", pady=(8, 4))
        self._label(self.body, "Analiza statyczna. Badane pliki nie są uruchamiane.", 10, MUTED).pack(anchor="w", pady=(0, 16))
        card = self._card(self.body, "Skanowanie folderu", "Folder jest zapamiętywany między uruchomieniami CMD.")
        card.pack(fill="x", pady=6)
        folder = tk.StringVar()
        line = tk.Frame(card, bg=PANEL)
        line.pack(fill="x", padx=18, pady=(0, 10))
        tk.Entry(line, textvariable=folder, bg=PANEL_2, fg=TEXT, insertbackground=TEXT,
                 relief="flat").pack(side="left", fill="x", expand=True, ipady=9)
        self._button(line, "Wybierz", lambda: folder.set(filedialog.askdirectory() or folder.get())).pack(side="left", padx=6)
        def save_and_scan():
            from .security_scanner import print_report, save_scan_folder, scan_folder
            try:
                target = save_scan_folder(folder.get())
                self.status.set("Skanowanie folderu...")
                self.root.update_idletasks()
                report = scan_folder(target)
                print_report(report)
                messagebox.showinfo("321 Scanner", f"Przeanalizowano {report['files_analysed']} plików. Wynik: {report['severity']}\nSzczegóły raportu w konsoli.")
                self.status.set("Skanowanie zakończone")
            except Exception as exc:
                messagebox.showerror("321 Scanner", str(exc))
        self._button(card, "Zapisz folder i skanuj", save_and_scan, True).pack(anchor="e", padx=18, pady=(0, 16))
        web = self._card(self.body, "Skanowanie publicznej strony WWW", "Podstawowe informacje HTTP(S), nagłówki, domeny i identyfikatory usług. To nie jest test penetracyjny.")
        web.pack(fill="x", pady=6)
        url = tk.StringVar(value="https://replit.com")
        tk.Entry(web, textvariable=url, bg=PANEL_2, fg=TEXT, insertbackground=TEXT,
                 relief="flat").pack(fill="x", padx=18, pady=(0, 10), ipady=9)
        def scan_url():
            from .security_scanner import print_report, scan_website
            try:
                report = scan_website(url.get())
                print_report(report, website=True)
                messagebox.showinfo("321 Scanner", f"HTTP {report['status']} • API: {len(report['apis'])}\nRaport szczegółowy wyświetlono w konsoli.")
            except Exception as exc:
                messagebox.showerror("321 Scanner", str(exc))
        self._button(web, "Analizuj stronę", scan_url, True).pack(anchor="e", padx=18, pady=(0, 16))

    def _page_language(self):
        self._label(self.body, "Język 321code", 22, TEXT, True).pack(anchor="w", pady=(8, 4))
        self._label(self.body, "Twórz i uruchamiaj programy .321.", 10, MUTED).pack(anchor="w", pady=(0, 18))
        card = self._card(self.body, "Otwórz plik .321", "Uruchom interpreter dla wybranego programu.")
        card.pack(fill="x")
        def run_file():
            path = filedialog.askopenfilename(filetypes=[("321code", "*.321"), ("Wszystkie pliki", "*.*")])
            if not path:
                return
            from .runtime import run_file as execute
            code = execute(Path(path))
            self.status.set("Program zakończył działanie" if code == 0 else "Program zakończył się błędem")
        self._button(card, "Wybierz plik i uruchom", run_file, True).pack(anchor="e", padx=18, pady=(0, 16))
        docs = self._card(self.body, "Dokumentacja", "Dokumentacja składni znajduje się w docs/SYNTAX.md w repozytorium.")
        docs.pack(fill="x", pady=12)
        self._button(docs, "Otwórz repozytorium", lambda: self.open_url("https://github.com/kaielk09/jenzyku")).pack(anchor="e", padx=18, pady=(0, 16))

    def _page_settings(self):
        self._label(self.body, "Ustawienia", 22, TEXT, True).pack(anchor="w", pady=(8, 4))
        card = self._card(self.body, "Informacje o środowisku", "321code Studio działa lokalnie i korzysta z systemowego Pythona.")
        card.pack(fill="x", pady=8)
        self._label(card, f"Python: {sys.version.split()[0]}", 10, MUTED).pack(anchor="w", padx=18, pady=4)
        self._label(card, f"System: {sys.platform}", 10, MUTED).pack(anchor="w", padx=18, pady=4)
        self._label(card, f"Katalog: {Path.cwd()}", 9, MUTED, wraplength=700, justify="left").pack(anchor="w", padx=18, pady=(4, 16))

    def new_project(self):
        name = tk.simpledialog.askstring("Nowy projekt", "Nazwa projektu:")
        if not name:
            return
        safe = "".join(c if c.isalnum() or c in "_-" else "_" for c in name).strip("_")
        if not safe:
            messagebox.showerror("Projekt", "Nieprawidłowa nazwa projektu.")
            return
        folder = Path.cwd() / "projects" / safe
        try:
            folder.mkdir(parents=True, exist_ok=False)
            (folder / "main.321").write_text('print "Witaj w 321code!"\n', encoding="utf-8")
            (folder / "321code.json").write_text('{"name": "' + safe + '", "scripts": {}}\n', encoding="utf-8")
            self.status.set("Utworzono projekt " + safe)
            messagebox.showinfo("Projekt utworzony", str(folder))
            self.show("projects")
        except FileExistsError:
            messagebox.showerror("Projekt", "Projekt o tej nazwie już istnieje.")

    def open_selected_project(self):
        selected = self.project_tree.selection()
        if not selected:
            return
        self.open_folder(self.project_tree.item(selected[0], "values")[0])

    def open_folder(self, folder):
        path = Path(folder)
        if os.name == "nt":
            os.startfile(str(path))
        elif sys.platform == "darwin":
            subprocess.Popen(["open", str(path)])
        else:
            subprocess.Popen(["xdg-open", str(path)])

    def open_url(self, url):
        import webbrowser
        webbrowser.open(url)

    def open_ai(self):
        from .ai_app import main
        main()

    def open_model(self):
        path = filedialog.askdirectory(title="Wybierz folder projektu modelu AI")
        if path:
            from .ai_chat import main
            main([path])

    def train_model(self):
        path = filedialog.askdirectory(title="Wybierz folder projektu modelu AI")
        if not path:
            return
        from .ai_trainer import main
        main([path])


def main() -> int:
    try:
        import tkinter.simpledialog
        root = tk.Tk()
    except tk.TclError as exc:
        print(f"Nie można uruchomić GUI: {exc}", file=sys.stderr)
        return 1
    Studio(root)
    root.mainloop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
