"""321 AI generator window: search the web and build a training TXT."""
from __future__ import annotations
import threading
import tkinter as tk
from tkinter import messagebox
from pathlib import Path
from .generator import build_training_txt
from code321.ai_app import BG, PANEL, PANEL_ALT, PURPLE, PURPLE_HOVER, TEXT, MUTED, BORDER

def open_generator(parent, model_name, on_ready):
    win=tk.Toplevel(parent)
    win.title("321 AI • Generator danych")
    win.geometry("650x470")
    win.minsize(560,400)
    win.configure(bg=BG)
    win.transient(parent)
    tk.Label(win,text="AI • INTERNETOWY GENERATOR TXT",bg=BG,fg=TEXT,font=("Segoe UI",16,"bold")).pack(anchor="w",padx=22,pady=(20,4))
    tk.Label(win,text="Opisz temat. Generator wyszuka strony w internecie i zbierze ich tekst do pliku treningowego TXT.",bg=BG,fg=MUTED,wraplength=590,justify="left",font=("Segoe UI",9)).pack(anchor="w",padx=22,pady=(0,12))
    box=tk.Frame(win,bg=PANEL,highlightthickness=1,highlightbackground=BORDER)
    box.pack(fill="both",expand=True,padx=22,pady=(0,12))
    entry=tk.Text(box,bg=PANEL_ALT,fg=TEXT,insertbackground=TEXT,wrap="word",relief="flat",font=("Segoe UI",10),padx=12,pady=12)
    entry.pack(fill="both",expand=True,padx=1,pady=1)
    status=tk.Label(win,text="Gotowy • wyszukiwanie wymaga internetu",bg=BG,fg=MUTED,font=("Segoe UI",9))
    status.pack(anchor="w",padx=22,pady=(0,10))
    btn=tk.Button(win,text="GENERUJ TXT  →",bg=PURPLE,fg="white",activebackground=PURPLE_HOVER,activeforeground="white",relief="flat",font=("Segoe UI",10,"bold"),padx=18,pady=10)
    btn.pack(anchor="e",padx=22,pady=(0,20))
    def run():
        prompt=entry.get("1.0","end-1c").strip()
        if len(prompt)<3:
            messagebox.showwarning("321 AI","Opisz temat.",parent=win)
            return
        btn.configure(state="disabled")
        status.configure(text="Wyszukuję w internecie i pobieram treść stron…",fg="#c4b5fd")
        def worker():
            try:
                target=Path.home()/"321code"/"ai_datasets"/(model_name+"_internet_dataset.txt")
                size,urls=build_training_txt(prompt,target)
                def done():
                    on_ready(str(target))
                    status.configure(text=f"Gotowe • {len(urls)} źródła • {size:,} bajtów",fg="#4ade80")
                    btn.configure(state="normal")
                    messagebox.showinfo("321 AI",f"Zapisano TXT i podłączono do treningu:\n{target}",parent=win)
                    win.destroy()
                win.after(0,done)
            except Exception as exc:
                def fail():
                    status.configure(text="Nie udało się wygenerować pliku.",fg="#fca5a5")
                    btn.configure(state="normal")
                    messagebox.showerror("321 AI • Generator",str(exc),parent=win)
                win.after(0,fail)
        threading.Thread(target=worker,daemon=True).start()
    btn.configure(command=run)
    return win
