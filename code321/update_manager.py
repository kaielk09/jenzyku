"""321code release checker and self-updater."""
from __future__ import annotations

import json
import subprocess
import sys
import urllib.request
from pathlib import Path

VERSION_URL = "https://raw.githubusercontent.com/kaielk09/jenzyku/main/version.json"
ROOT = Path(__file__).resolve().parent.parent


def read_latest():
    request = urllib.request.Request(VERSION_URL, headers={"User-Agent": "321code-version-check"})
    with urllib.request.urlopen(request, timeout=6) as response:
        data = json.loads(response.read().decode("utf-8"))
    return str(data.get("version", "")).strip(), str(data.get("notes", "Nowe funkcje i poprawki")).strip()


def version_tuple(value):
    try:
        return tuple(int(part) for part in value.split("."))
    except (TypeError, ValueError):
        return ()


def update_now():
    if not (ROOT / ".git").exists():
        raise RuntimeError("Instalacja nie zawiera repozytorium Git — aktualizacja automatyczna niedostępna.")
    git = subprocess.run(["git", "-C", str(ROOT), "pull", "--ff-only"], text=True, capture_output=True)
    if git.returncode:
        raise RuntimeError(git.stderr.strip() or git.stdout.strip() or "Git pull nie powiódł się.")
    pip = subprocess.run([sys.executable, "-m", "pip", "install", "-e", "."], cwd=str(ROOT), text=True, capture_output=True)
    if pip.returncode:
        raise RuntimeError(pip.stderr.strip() or "Reinstalacja pakietu 321code nie powiodła się.")
    return git.stdout.strip() or "Repozytorium zaktualizowane."


def show_update_dialog(current, latest, notes):
    import tkinter as tk
    from tkinter import messagebox

    root = tk.Tk()
    root.title("321code — dostępna aktualizacja")
    root.geometry("420x235")
    root.resizable(False, False)
    root.configure(bg="#15121f")
    tk.Label(root, text="321code UPDATE", font=("Segoe UI", 17, "bold"), fg="#bb86fc", bg="#15121f").pack(pady=(18, 5))
    tk.Label(root, text=f"Zainstalowana wersja: {current}", font=("Segoe UI", 10), fg="#ddd", bg="#15121f").pack()
    tk.Label(root, text=f"Nowa wersja: {latest}", font=("Segoe UI", 11, "bold"), fg="#a78bfa", bg="#15121f").pack(pady=2)
    tk.Label(root, text=notes[:110], wraplength=370, font=("Segoe UI", 9), fg="#bbb", bg="#15121f").pack(pady=(6, 12))
    status = tk.StringVar(value="Kliknij, aby pobrać i zastąpić pliki aktualną wersją.")
    tk.Label(root, textvariable=status, wraplength=370, font=("Segoe UI", 9), fg="#ddd", bg="#15121f").pack(pady=4)

    def do_update():
        button.config(state="disabled")
        status.set("Pobieranie i instalowanie aktualizacji…")
        root.update_idletasks()
        try:
            update_now()
            status.set("Aktualizacja zakończona. Uruchom CMD ponownie.")
            messagebox.showinfo("321code", "Zaktualizowano! Zamknij i otwórz ponownie CMD.", parent=root)
            root.destroy()
        except Exception as exc:
            status.set("Aktualizacja nie powiodła się.")
            messagebox.showerror("Błąd aktualizacji", str(exc), parent=root)
            button.config(state="normal")

    button = tk.Button(root, text="Pobierz nową wersję", command=do_update, bg="#7c3aed", fg="white", activebackground="#6d28d9", activeforeground="white", relief="flat", padx=18, pady=9, font=("Segoe UI", 10, "bold"))
    button.pack(pady=5)
    root.mainloop()


def version_command(current):
    print(f"321code {current}")
    try:
        latest, notes = read_latest()
    except Exception as exc:
        print(f"Nie udało się sprawdzić aktualizacji (offline?): {exc}")
        return 0
    if not latest:
        print("Serwer aktualizacji nie podał wersji.")
        return 0
    if version_tuple(latest) > version_tuple(current):
        print(f"Dostępna nowa wersja: {latest}")
        print("Otwieram okno aktualizacji z przyciskiem…")
        try:
            show_update_dialog(current, latest, notes)
        except Exception as exc:
            print(f"Nie udało się otworzyć okna aktualizacji: {exc}")
            print(f"Aby zaktualizować ręcznie: git -C \"{ROOT}\" pull --ff-only")
    else:
        print("Masz najnowszą wersję 321code.")
    return 0
