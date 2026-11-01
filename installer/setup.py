"""Small Windows GUI installer bundled into a self-contained EXE."""
from __future__ import annotations

import ctypes
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tkinter as tk
from tkinter import messagebox, ttk
import winreg

APP_NAME = "321code"
INSTALL_DIR = Path(os.environ.get("LOCALAPPDATA", str(Path.home()))) / "Programs" / APP_NAME
BIN_DIR = INSTALL_DIR / "bin"
EXE_NAME = "321.exe"


def bundled_cli() -> Path:
    base = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent))
    candidate = base / EXE_NAME
    if not candidate.is_file():
        raise FileNotFoundError("Nie znaleziono dołączonego pliku 321.exe.")
    return candidate


def add_user_path(directory: Path) -> None:
    with winreg.OpenKey(
        winreg.HKEY_CURRENT_USER, r"Environment", 0,
        winreg.KEY_READ | winreg.KEY_SET_VALUE
    ) as key:
        try:
            current, value_type = winreg.QueryValueEx(key, "Path")
        except FileNotFoundError:
            current, value_type = "", winreg.REG_EXPAND_SZ
        entries = [part.strip().strip('"') for part in current.split(";") if part.strip()]
        if str(directory).lower() not in [part.lower() for part in entries]:
            entries.append(str(directory))
            winreg.SetValueEx(key, "Path", 0, value_type, ";".join(entries))

    ctypes.windll.user32.SendMessageTimeoutW(
        0xFFFF, 0x001A, 0, "Environment", 0x0002, 5000, None
    )


def schedule_installer_cleanup() -> None:
    if not getattr(sys, "frozen", False):
        return
    installer = Path(sys.executable).resolve()
    script = Path(os.environ.get("TEMP", str(Path.home()))) / "321code-remove-setup.cmd"
    script.write_text(
        "@echo off\r\n"
        "timeout /t 3 /nobreak >nul\r\n"
        f'del /f /q "{installer}" >nul 2>&1\r\n'
        'del /f /q "%~f0" >nul 2>&1\r\n',
        encoding="utf-8",
    )
    subprocess.Popen(
        f'start "" /min cmd.exe /c "{script}"',
        shell=True,
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
    )


def install(status: tk.StringVar, button: ttk.Button, root: tk.Tk) -> None:
    button.configure(state="disabled")
    try:
        status.set("Instalowanie 321code...")
        root.update_idletasks()
        BIN_DIR.mkdir(parents=True, exist_ok=True)
        shutil.copy2(bundled_cli(), BIN_DIR / EXE_NAME)
        add_user_path(BIN_DIR)
        messagebox.showinfo(
            "321code — instalacja zakończona",
            "321code został zainstalowany.\n\n"
            f"Lokalizacja: {BIN_DIR}\n\n"
            "Otwórz nowe okno CMD i wpisz: 321 help\n"
            "Instalator EXE zostanie teraz usunięty.",
        )
        schedule_installer_cleanup()
        root.destroy()
    except Exception as exc:
        button.configure(state="normal")
        status.set("Instalacja nie powiodła się.")
        messagebox.showerror("Błąd instalacji", str(exc))


def main() -> None:
    if os.name != "nt":
        raise SystemExit("Ten instalator jest przeznaczony dla Windows.")
    root = tk.Tk()
    root.title("321code — Instalator")
    root.geometry("430x260")
    root.resizable(False, False)
    root.configure(bg="#171321")
    tk.Label(
        root, text="321code", font=("Segoe UI", 25, "bold"),
        fg="#b78cff", bg="#171321"
    ).pack(pady=(24, 4))
    tk.Label(
        root, text="Instalacja języka programowania 321code",
        font=("Segoe UI", 10), fg="#eeeeF5", bg="#171321"
    ).pack(pady=(0, 18))
    tk.Label(
        root, text=f"Folder: {INSTALL_DIR}",
        font=("Segoe UI", 8), fg="#b9b3c7", bg="#171321", wraplength=390
    ).pack(pady=(0, 15))
    status = tk.StringVar(value="Gotowy do instalacji.")
    tk.Label(
        root, textvariable=status, font=("Segoe UI", 9),
        fg="#d8c8ff", bg="#171321"
    ).pack(pady=(0, 12))
    button = ttk.Button(
        root, text="Zainstaluj", command=lambda: install(status, button, root)
    )
    button.pack(ipadx=28, ipady=8)
    tk.Label(
        root, text="Python nie musi być zainstalowany.",
        font=("Segoe UI", 8), fg="#aaa2b7", bg="#171321"
    ).pack(side="bottom", pady=14)
    root.mainloop()


if __name__ == "__main__":
    main()
