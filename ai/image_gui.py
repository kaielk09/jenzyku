"""GUI for automatic 321 AI image dataset creation and local training."""
from __future__ import annotations
import subprocess,sys
import tkinter as tk
from tkinter import messagebox,ttk
from pathlib import Path
from code321.ai_app import BG,PANEL,PANEL_ALT,PURPLE,PURPLE_HOVER,TEXT,MUTED,BORDER,APP_DIR

def open_image_training(parent,model_name):
 w=tk.Toplevel(parent); w.title("321 AI • Image training"); w.geometry("620x510"); w.configure(bg=BG); w.transient(parent)
 tk.Label(w,text="321 AI  /  IMAGE LAB",bg=BG,fg=TEXT,font=("Segoe UI",19,"bold")).pack(anchor="w",padx=24,pady=(22,5))
 tk.Label(w,text="Dataset jest pobierany automatycznie z Wikimedia Commons (tylko oznaczone wolne licencje / public domain), potem model DDPM trenuje od zera.",bg=BG,fg=MUTED,wraplength=560,justify="left").pack(anchor="w",padx=24,pady=(0,15))
 card=tk.Frame(w,bg=PANEL,highlightthickness=1,highlightbackground=BORDER); card.pack(fill="both",expand=True,padx=24,pady=(0,18))
 category=tk.StringVar(value="random"); count=tk.StringVar(value="120"); steps=tk.StringVar(value="8000"); batch=tk.StringVar(value="8")
 def field(label,var,values):
  f=tk.Frame(card,bg=PANEL); f.pack(fill="x",padx=18,pady=8)
  tk.Label(f,text=label,bg=PANEL,fg=MUTED,font=("Segoe UI",9,"bold")).pack(anchor="w",pady=(0,4))
  cb=ttk.Combobox(f,textvariable=var,values=values,state="readonly"); cb.pack(fill="x"); return cb
 field("AUTOMATYCZNY TEMAT DATASETU",category,("random","nature","landscapes","animals","architecture","objects","space","plants"))
 field("LICZBA OBRAZÓW",count,("40","80","120","200","300","500"))
 field("KROKI TRENINGU DDPM",steps,("1000","2500","5000","8000","15000","30000"))
 field("BATCH GPU/CPU",batch,("2","4","8","16","32"))
 status=tk.Label(w,text="Wymagane biblioteki: PyTorch + Pillow + NumPy",bg=BG,fg=MUTED,font=("Segoe UI",9)); status.pack(anchor="w",padx=24,pady=(0,10))
 def start():
  if getattr(sys,"frozen",False):
   messagebox.showwarning("321 AI","Trening wymaga wersji Python. PyTorch nie jest dołączony do instalatora EXE.",parent=w); return
  try:
   import torch, numpy
   from PIL import Image
  except ImportError as e:
   messagebox.showerror("Brak pakietów",f"Zainstaluj: pip install torch numpy Pillow\n\n{e}",parent=w); return
  target=APP_DIR/"ai_images"/model_name; target.mkdir(parents=True,exist_ok=True)
  cmd=[sys.executable,"-m","ai.image_pipeline","--category",category.get(),"--count",count.get(),"--steps",steps.get(),"--batch",batch.get(),"--out",str(target)]
  status.configure(text=f"Uruchomiono pipeline • zapis: {target}",fg="#c4b5fd"); btn.configure(state="disabled")
  try:
   subprocess.Popen(["cmd","/k",*cmd] if sys.platform=="win32" else cmd,cwd=str(APP_DIR))
   messagebox.showinfo("321 AI","Otwarto terminal: najpierw automatyczny dataset, następnie trening DDPM. Okno terminala pozostaw otwarte.",parent=w)
  except Exception as e: messagebox.showerror("Błąd",str(e),parent=w); btn.configure(state="normal")
 btn=tk.Button(w,text="START AUTOMATYCZNEGO DATASETU + TRENING  →",command=start,bg=PURPLE,fg="white",activebackground=PURPLE_HOVER,relief="flat",font=("Segoe UI",10,"bold"),padx=15,pady=11); btn.pack(fill="x",padx=24,pady=(0,22))
 def generate_samples():
  model=APP_DIR/"ai_images"/model_name/"training"/"image_model.pt"
  if not model.is_file():
   messagebox.showinfo("321 AI","Najpierw ukończ trening obrazów, żeby utworzyć checkpoint generatora.",parent=w); return
  if getattr(sys,"frozen",False):
   messagebox.showwarning("321 AI","Generator wymaga obecnie wersji Python; PyTorch nie jest jeszcze dołączony do EXE.",parent=w); return
  try: import torch
  except ImportError: messagebox.showerror("321 AI","Brak PyTorch. Zainstaluj: pip install torch",parent=w); return
  dest=__import__("tkinter.filedialog",fromlist=["askdirectory"]).askdirectory(parent=w,title="Folder wynikowych obrazów")
  if not dest:return
  cmd=[sys.executable,"-m","ai.image_generate","--model",str(model),"--out",dest,"--count","4"]
  try:
   subprocess.Popen(["cmd","/k",*cmd] if sys.platform=="win32" else cmd,cwd=str(APP_DIR))
   messagebox.showinfo("321 AI","Generator uruchomiony — zapisze 4 obrazy w wybranym folderze.",parent=w)
  except Exception as e:messagebox.showerror("321 AI",str(e),parent=w)
 genbtn=tk.Button(w,text="GENERUJ 4 OBRAZY Z WYTRAINOWANEGO MODELU",command=generate_samples,bg=PANEL_ALT,fg=TEXT,activebackground=PURPLE_HOVER,relief="flat",font=("Segoe UI",9,"bold"),padx=12,pady=8)
 genbtn.pack(fill="x",padx=24,pady=(0,10))
 return w
