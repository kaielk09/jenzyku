"""321 AI project creator desktop wizard."""
from __future__ import annotations
import json, re, subprocess, sys, tkinter as tk
from pathlib import Path
from tkinter import messagebox

APP_DIR = Path.cwd()

def safe_name(value):
    value = re.sub(r"[^A-Za-z0-9_-]+", "_", value.strip()).strip("_")
    if not value:
        raise ValueError("Wpisz nazwę z literami lub cyframi.")
    return value[:48]

class Creator:
    def __init__(self, root):
        self.root = root
        root.title("321 AI Creator")
        root.geometry("520x590")
        root.resizable(False, False)
        root.configure(bg="#101018")
        tk.Label(root, text="A", font=("Arial", 76, "bold"), fg="#a78bfa", bg="#101018").pack(pady=(14,0))
        tk.Label(root, text="321 AI CREATOR", font=("Arial",19,"bold"), fg="white", bg="#101018").pack(pady=(0,18))
        self.name = self.field("Nazwa Twojego AI","MojModel")
        self.steps = self.field("Ilość treningu (liczba kroków)","29000")
        self.gpu = self.field("Model karty graficznej (informacyjnie)","RTX 2060")
        tk.Label(root,text="Na czym pracujesz?",fg="#d8d4e8",bg="#101018",font=("Arial",11,"bold")).pack(anchor="w",padx=42,pady=(14,6))
        self.machine=tk.StringVar(value="Komputer")
        row=tk.Frame(root,bg="#101018"); row.pack(anchor="w",padx=42)
        for v in ("Komputer","Laptop"):
            tk.Radiobutton(row,text=v,value=v,variable=self.machine,fg="white",selectcolor="#29243a",bg="#101018",activebackground="#101018",activeforeground="white").pack(side="left",padx=(0,18))
        tk.Label(root,text="Projekt zostanie zapisany w folderze ai obok uruchomionego programu.",wraplength=420,fg="#aaa6bb",bg="#101018",font=("Arial",9)).pack(pady=22)
        tk.Button(root,text="CREATE",command=self.create,bg="#7c3aed",fg="white",activebackground="#6d28d9",activeforeground="white",relief="flat",font=("Arial",14,"bold"),width=24,height=2).pack(pady=8)

    def field(self,label,default):
        tk.Label(self.root,text=label,fg="#d8d4e8",bg="#101018",font=("Arial",11,"bold")).pack(anchor="w",padx=42,pady=(8,5))
        e=tk.Entry(self.root,bg="#242333",fg="white",insertbackground="white",relief="flat",font=("Arial",12))
        e.pack(fill="x",padx=42,ipady=9); e.insert(0,default); return e

    def create(self):
        try:
            name=safe_name(self.name.get())
            steps=int(self.steps.get().replace(" ","").replace("_",""))
            if not 1 <= steps <= 1000000: raise ValueError("Liczba kroków musi być od 1 do 1 000 000.")
            project=APP_DIR/"ai"/name
            project.mkdir(parents=True,exist_ok=False)
            cfg={"name":name,"training_steps":steps,"gpu_label":self.gpu.get().strip() or "Nie podano","device_preference":"auto","machine_type":self.machine.get(),"status":"waiting_for_dataset"}
            (project/"config.json").write_text(json.dumps(cfg,ensure_ascii=False,indent=2),encoding="utf-8")
            (project/"dataset.txt").write_text("# Wklej tu legalnie pozyskane przykłady treningowe.\n# Dodaj pytania i dobre odpowiedzi; usuń komentarze.\n",encoding="utf-8")
            trainer=Path(__file__).resolve().with_name("ai_trainer.py")
            cmd=[sys.executable,str(trainer),str(project)]
            if sys.platform=="win32": subprocess.Popen(["cmd","/k",*cmd],cwd=str(project))
            else: subprocess.Popen(cmd,cwd=str(project))
            self.root.destroy()
        except FileExistsError: messagebox.showerror("321 AI","Folder o takiej nazwie już istnieje.")
        except ValueError as exc: messagebox.showerror("321 AI",str(exc))
        except OSError as exc: messagebox.showerror("321 AI",f"Nie udało się utworzyć projektu: {exc}")

def main():
    root=tk.Tk(); Creator(root); root.mainloop(); return 0
if __name__=="__main__": raise SystemExit(main())
