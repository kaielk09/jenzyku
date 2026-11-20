"""UI for the local-only 321 AI image training mode."""
from __future__ import annotations
import subprocess,sys,threading
import tkinter as tk
from tkinter import filedialog,messagebox
from pathlib import Path
from code321.ai_app import BG,PANEL,PANEL_ALT,PURPLE,PURPLE_HOVER,TEXT,MUTED,BORDER,APP_DIR

def open_image_training(parent, model_name):
 win=tk.Toplevel(parent); win.title("321 AI • Trening obrazów"); win.geometry("610x420"); win.configure(bg=BG); win.transient(parent)
 tk.Label(win,text="321 AI • TRENING GENEROWANIA OBRAZÓW",bg=BG,fg=TEXT,font=("Segoe UI",16,"bold")).pack(anchor="w",padx=22,pady=(20,5))
 tk.Label(win,text="Wybierz folder z własnymi obrazami. Model trenuje lokalnie, od zera — bez API i gotowych wag.",bg=BG,fg=MUTED,wraplength=550,justify="left").pack(anchor="w",padx=22,pady=(0,12))
 card=tk.Frame(win,bg=PANEL,highlightthickness=1,highlightbackground=BORDER); card.pack(fill="both",expand=True,padx=22,pady=(0,14))
 folder=tk.StringVar(); steps=tk.StringVar(value="5000"); batch=tk.StringVar(value="16")
 tk.Label(card,text="FOLDER OBRAZÓW",bg=PANEL,fg=MUTED,font=("Segoe UI",9,"bold")).pack(anchor="w",padx=16,pady=(16,4))
 row=tk.Frame(card,bg=PANEL); row.pack(fill="x",padx=16)
 tk.Entry(row,textvariable=folder,bg=PANEL_ALT,fg=TEXT,insertbackground=TEXT,relief="flat").pack(side="left",fill="x",expand=True,ipady=9)
 def choose():
  p=filedialog.askdirectory(parent=win,title="Folder treningowy — obrazy")
  if p: folder.set(p)
 tk.Button(row,text="WYBIERZ",command=choose,bg=PANEL_ALT,fg=TEXT,relief="flat",padx=12,pady=8).pack(side="left",padx=(8,0))
 settings=tk.Frame(card,bg=PANEL); settings.pack(fill="x",padx=16,pady=16)
 for lab,var,vals in [("KROKI TRENINGU",steps,("500","1000","5000","10000","25000")),("BATCH",batch,("4","8","16","32"))]:
  col=tk.Frame(settings,bg=PANEL); col.pack(side="left",fill="x",expand=True,padx=(0,12))
  tk.Label(col,text=lab,bg=PANEL,fg=MUTED,font=("Segoe UI",8,"bold")).pack(anchor="w",pady=(0,5))
  from tkinter import ttk
  ttk.Combobox(col,textvariable=var,values=vals,state="readonly").pack(fill="x")
 status=tk.Label(win,text="Wymagane: PyTorch + Pillow • obrazy JPG/PNG/WEBP/BMP",bg=BG,fg=MUTED,font=("Segoe UI",9)); status.pack(anchor="w",padx=22,pady=(0,8))
 def start():
  if getattr(sys,"frozen",False):
   messagebox.showwarning("321 AI • Images","Tryb treningu obrazów wymaga obecnie uruchomienia wersji Python (nie samodzielnego 321.exe). W EXE nie jest jeszcze dołączony runtime PyTorch.",parent=win)
   return
  try:
   import torch
   from PIL import Image as _PILImage
  except ImportError as dependency_error:
   messagebox.showerror("321 AI • Images",f"Brak zależności treningu obrazów: {dependency_error}\\nInstaluj w Pythonie: pip install torch Pillow",parent=win)
   return
  src=Path(folder.get()).expanduser()
  try:
   count=sum(1 for p in src.rglob("*") if p.suffix.lower() in (".png",".jpg",".jpeg",".bmp",".webp"))
   if not src.is_dir() or count<4: raise ValueError("Wybierz folder zawierający minimum 4 obrazy.")
   n=int(steps.get()); b=int(batch.get())
   if not 1<=n<=500000 or b not in (4,8,16,32): raise ValueError("Nieprawidłowe parametry.")
  except Exception as e: messagebox.showerror("321 AI",str(e),parent=win); return
  out=APP_DIR/"ai_images"/model_name
  out.mkdir(parents=True,exist_ok=True)
  cmd=[sys.executable,"-m","ai.image_trainer","--images",str(src),"--out",str(out),"--steps",str(n),"--batch",str(b)]
  status.configure(text=f"Uruchamiam trening • {count} obrazów • {out}",fg="#c4b5fd")
  btn.configure(state="disabled")
  try:
   if sys.platform=="win32": subprocess.Popen(["cmd","/k",*cmd],cwd=str(APP_DIR))
   else: subprocess.Popen(cmd,cwd=str(APP_DIR))
   messagebox.showinfo("321 AI",f"Trening uruchomiony. Folder modelu:\n{out}",parent=win)
  except Exception as e: messagebox.showerror("Błąd uruchomienia",str(e),parent=win); btn.configure(state="normal")
 btn=tk.Button(win,text="ROZPOCZNIJ TRENING OBRAZÓW  →",command=start,bg=PURPLE,fg="white",activebackground=PURPLE_HOVER,relief="flat",font=("Segoe UI",10,"bold"),padx=18,pady=10); btn.pack(anchor="e",padx=22,pady=(0,18))
 return win
