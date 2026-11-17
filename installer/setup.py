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


def schedule_installer_self_delete() -> None:
    """Delete the downloaded setup EXE after this process exits (frozen build only)."""
    if not getattr(sys, "frozen", False):
        return
    installer_path = Path(sys.executable).resolve()
    if installer_path.name.lower() != "321code-setup.exe":
        return
    script_path = Path(os.environ.get("TEMP", str(Path.home()))) / f"321code-cleanup-{os.getpid()}.cmd"
    quoted_exe = str(installer_path).replace('"', '""')
    script = (
        "@echo off\r\n"
        ":retry\r\n"
        "timeout /t 2 /nobreak >nul\r\n"
        f'del /f /q "{quoted_exe}" >nul 2>&1\r\n'
        f'if exist "{quoted_exe}" goto retry\r\n'
        'del /f /q "%~f0" >nul 2>&1\r\n'
    )
    script_path.write_text(script, encoding="utf-8")
    flags = getattr(subprocess, "DETACHED_PROCESS", 0x00000008) | getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0x00000200)
    subprocess.Popen(
        ["cmd.exe", "/c", str(script_path)],
        creationflags=flags,
        close_fds=True,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
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
            "321code został poprawnie zainstalowany.\n\n"
            f"Lokalizacja: {BIN_DIR}\n\n"
            "Otwórz nowe okno CMD i wpisz: 321 help",
            parent=root,
        )
        schedule_installer_self_delete()
        root.destroy()
    except Exception as exc:
        button.configure(state="normal")
        status.set("Instalacja nie powiodła się.")
        messagebox.showerror("Błąd instalacji", str(exc))


def main() -> None:
    if os.name != "nt":
        raise SystemExit("Ten instalator jest przeznaczony dla Windows.")

    root = tk.Tk()
    root.title("321code Setup")
    root.geometry("580x430")
    root.minsize(540, 400)
    root.configure(bg="#0b0b12")
    root.resizable(True, True)

    style = ttk.Style(root)
    style.theme_use("clam")
    style.configure("Install.TButton", font=("Segoe UI", 10, "bold"),
                    padding=(18, 11), background="#8b5cf6",
                    foreground="white", borderwidth=0)
    style.map("Install.TButton",
              background=[("active", "#7545df"), ("disabled", "#393247")],
              foreground=[("disabled", "#aaa2b7")])

    shell = tk.Frame(root, bg="#0b0b12")
    shell.pack(fill="both", expand=True, padx=34, pady=28)
    brand = tk.Frame(shell, bg="#0b0b12")
    brand.pack(fill="x")
    mark = tk.Frame(brand, bg="#8b5cf6", width=54, height=54)
    mark.pack(side="left")
    mark.pack_propagate(False)
    tk.Label(mark, text="321", bg="#8b5cf6", fg="white",
             font=("Segoe UI", 17, "bold")).place(relx=.5, rely=.5, anchor="center")
    titles = tk.Frame(brand, bg="#0b0b12")
    titles.pack(side="left", padx=15)
    tk.Label(titles, text="321code", bg="#0b0b12", fg="#f4f1ff",
             font=("Segoe UI", 23, "bold")).pack(anchor="w")
    tk.Label(titles, text="INSTALATOR WINDOWS", bg="#0b0b12", fg="#a6a1b8",
             font=("Segoe UI", 9, "bold")).pack(anchor="w")

    tk.Frame(shell, bg="#29263a", height=1).pack(fill="x", pady=22)
    tk.Label(shell, text="Zainstaluj 321code na swoim komputerze",
             bg="#0b0b12", fg="#f4f1ff",
             font=("Segoe UI", 16, "bold")).pack(anchor="w")
    tk.Label(shell, text="Interpreter zostanie dodany do PATH Twojego konta Windows. "
                         "Nie musisz instalować Pythona.",
             bg="#0b0b12", fg="#a6a1b8", wraplength=480, justify="left",
             font=("Segoe UI", 10)).pack(anchor="w", pady=(7, 18))

    location = tk.Frame(shell, bg="#141421", highlightthickness=1,
                        highlightbackground="#29263a")
    location.pack(fill="x")
    tk.Label(location, text="LOKALIZACJA INSTALACJI", bg="#141421",
             fg="#a6a1b8", font=("Segoe UI", 8, "bold")).pack(anchor="w", padx=14, pady=(11, 3))
    tk.Label(location, text=str(BIN_DIR), bg="#141421", fg="#f4f1ff",
             font=("Segoe UI", 9), wraplength=470, justify="left").pack(
                 anchor="w", padx=14, pady=(0, 12))

    status = tk.StringVar(value="Gotowy do instalacji.")
    tk.Label(shell, textvariable=status, bg="#0b0b12", fg="#c4b5fd",
             font=("Segoe UI", 9)).pack(anchor="w", pady=(18, 10))
    footer = tk.Frame(shell, bg="#0b0b12")
    footer.pack(fill="x", side="bottom")
    tk.Label(footer, text="321code • Instalator", bg="#0b0b12", fg="#777187",
             font=("Segoe UI", 8)).pack(side="left")
    button = ttk.Button(footer, text="ZAINSTALUJ  →",
                        command=lambda: install(status, button, root),
                        style="Install.TButton")
    button.pack(side="right")

    root.update_idletasks()
    x = max(0, (root.winfo_screenwidth() - root.winfo_width()) // 2)
    y = max(0, (root.winfo_screenheight() - root.winfo_height()) // 2)
    root.geometry(f"+{x}+{y}")
    root.mainloop()

if __name__ == "__main__":
    main()
