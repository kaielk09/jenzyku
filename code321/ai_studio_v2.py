"""321 AI Creator v2 — project wizard, task-mix configuration and GUI training."""
from __future__ import annotations

import json
import os
import queue
import re
import shutil
import subprocess
import sys
import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

from . import github_integration

BG="#0a0a11"; PANEL="#141421"; ALT="#1c1b2b"; PURPLE="#9565f5"
TEXT="#f4f1ff"; MUTED="#aaa4bd"; BORDER="#302b45"; GREEN="#62d6a0"


def safe_name(value: str) -> str:
    value=re.sub(r"[^A-Za-z0-9_-]+","-",value.strip()).strip("-")
    if not value: raise ValueError("Podaj poprawną nazwę projektu/modelu.")
    return value[:48]


class CreatorV2:
    def __init__(self, root: tk.Tk):
        self.root=root; root.title("321 AI • Model Creator"); root.geometry("1050x850")
        root.minsize(850,700); root.configure(bg=BG)
        self.name=tk.StringVar(value="PurpleModel")
        self.repo=tk.StringVar(value="PurpleModel")
        self.steps=tk.StringVar(value="10000")
        self.width=tk.StringVar(value="256"); self.layers=tk.StringVar(value="6")
        self.heads=tk.StringVar(value="8"); self.context=tk.StringVar(value="256")
        self.batch=tk.StringVar(value="8"); self.device=tk.StringVar(value="Auto")
        self.dataset=tk.StringVar(); self.private=tk.BooleanVar(value=True)
        self.github_state=tk.StringVar(value="GitHub niepołączony")
        self.status=tk.StringVar(value="Gotowy do konfiguracji")
        self.progress=tk.DoubleVar(value=0)
        self.tasks={
            "programowanie":tk.BooleanVar(value=True),
            "rozmowa":tk.BooleanVar(value=True),
            "rozumowanie":tk.BooleanVar(value=True),
        }
        self.counts={
            "programowanie":tk.StringVar(value="2000"),
            "rozmowa":tk.StringVar(value="2000"),
            "rozumowanie":tk.StringVar(value="1000"),
        }
        self.events=queue.Queue(); self.process=None; self.project=None; self.publisher_thread=None
        self._style(); self._build(); self.refresh_github()

    def _style(self):
        st=ttk.Style(); st.theme_use("clam")
        st.configure("TCombobox",fieldbackground=ALT,background=ALT,foreground=TEXT,
                     arrowcolor=TEXT,bordercolor=BORDER,padding=7)
        st.map("TCombobox",fieldbackground=[("readonly",ALT)],foreground=[("readonly",TEXT)])
        st.configure("Horizontal.TProgressbar",troughcolor=ALT,background=PURPLE)

    def label(self,parent,text,size=9,color=MUTED,bold=False,**kw):
        return tk.Label(parent,text=text,bg=parent.cget("bg"),fg=color,
                        font=("Segoe UI",size,"bold" if bold else "normal"),**kw)

    def button(self,parent,text,command,primary=False):
        return tk.Button(parent,text=text,command=command,bg=PURPLE if primary else ALT,
                         fg="white",activebackground="#7045cf",activeforeground="white",
                         relief="flat",bd=0,padx=14,pady=9,font=("Segoe UI",9,"bold"),
                         cursor="hand2")

    def card(self,parent,title,subtitle=""):
        f=tk.Frame(parent,bg=PANEL,highlightthickness=1,highlightbackground=BORDER)
        self.label(f,title,11,TEXT,True).pack(anchor="w",padx=16,pady=(13,3))
        if subtitle: self.label(f,subtitle,8,MUTED,wraplength=900,justify="left").pack(anchor="w",padx=16,pady=(0,10))
        return f

    def entry(self,parent,var,width=None):
        e=tk.Entry(parent,textvariable=var,bg=ALT,fg=TEXT,insertbackground=TEXT,
                   relief="flat",font=("Segoe UI",10),highlightthickness=1,
                   highlightbackground=BORDER)
        if width: e.configure(width=width)
        return e

    def _build(self):
        header=tk.Frame(self.root,bg=BG); header.pack(fill="x",padx=24,pady=(18,12))
        self.label(header,"321 AI",21,TEXT,True).pack(side="left")
        self.label(header,"MODEL CREATOR  /  FROM-SCRATCH LAB",8,"#c4b5fd",True).pack(side="left",padx=14,pady=(8,0))
        tk.Label(header,text="BETA",bg="#241b3b",fg="#c4b5fd",font=("Segoe UI",8,"bold"),padx=10,pady=6).pack(side="right",padx=8,pady=8)
        body=tk.Frame(self.root,bg=BG); body.pack(fill="both",expand=True,padx=24)
        # Scrollable settings area
        canvas=tk.Canvas(body,bg=BG,highlightthickness=0); scroll=ttk.Scrollbar(body,orient="vertical",command=canvas.yview)
        inner=tk.Frame(canvas,bg=BG); inner.bind("<Configure>",lambda _e:canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0,0),window=inner,anchor="nw",width=980); canvas.configure(yscrollcommand=scroll.set)
        canvas.pack(side="left",fill="both",expand=True); scroll.pack(side="right",fill="y")
        gh=self.card(inner,"01  •  Konto GitHub","Logowanie odbywa się przez oficjalne GitHub CLI. 321 AI nie prosi o hasło ani nie zapisuje tokenu.")
        gh.pack(fill="x",pady=(0,10))
        row=tk.Frame(gh,bg=PANEL); row.pack(fill="x",padx=16,pady=(0,12))
        self.label(row,"●",10,GREEN,True).pack(side="left")
        self.label(row,"  ",8).pack(side="left")
        self.label(row,"",9,MUTED).pack(side="left")
        tk.Label(row,textvariable=self.github_state,bg=PANEL,fg=MUTED,font=("Segoe UI",9)).pack(side="left")
        self.button(row,"ODŚWIEŻ",self.refresh_github).pack(side="right")
        self.button(row,"POŁĄCZ GITHUB",self.connect_github,True).pack(side="right",padx=8)
        project=self.card(inner,"02  •  Projekt i repozytorium","Nazwa projektu tworzy folder lokalny i nazwę repozytorium GitHub.")
        project.pack(fill="x",pady=(0,10))
        grid=tk.Frame(project,bg=PANEL); grid.pack(fill="x",padx=16,pady=(0,12))
        for col,(caption,var) in enumerate((("NAZWA MODELU / PROJEKTU",self.name),("REPOZYTORIUM (owner/nazwa lub sama nazwa)",self.repo))):
            cell=tk.Frame(grid,bg=PANEL); cell.grid(row=0,column=col,sticky="ew",padx=(0,12))
            self.label(cell,caption,8,MUTED,True).pack(anchor="w")
            self.entry(cell,var).pack(fill="x",ipady=8,pady=(5,0))
        grid.columnconfigure(0,weight=1); grid.columnconfigure(1,weight=1)
        vis=tk.Frame(project,bg=PANEL); vis.pack(fill="x",padx=16,pady=(0,12))
        tk.Checkbutton(vis,text="Prywatne repozytorium (zalecane)",variable=self.private,
                       bg=PANEL,fg=TEXT,selectcolor=ALT,activebackground=PANEL,
                       activeforeground=TEXT).pack(side="left")
        model=self.card(inner,"03  •  Cele treningu","Wybierz obszary, które chcesz rozwijać. Liczby są zapisywane jako cele/metadane projektu; obecny trener nadal uczy jeden model na wspólnym pliku, więc nie traktuj ich jako gwarantowanej liczby osobno oznaczonych przykładów.")
        model.pack(fill="x",pady=(0,10))
        for task,var in self.tasks.items():
            r=tk.Frame(model,bg=PANEL); r.pack(fill="x",padx=16,pady=4)
            tk.Checkbutton(r,text=task.capitalize(),variable=var,bg=PANEL,fg=TEXT,
                           selectcolor=ALT,activebackground=PANEL,activeforeground=TEXT).pack(side="left")
            self.label(r,"Liczba przykładów",8,MUTED).pack(side="left",padx=(18,6))
            self.entry(r,self.counts[task],10).pack(side="left",ipady=5)
        self.label(model,"Obrazy: osobny autorski model i pipeline będą osobnym etapem. Nie włączamy tu niedziałającego przełącznika.",8,"#e7bb75",wraplength=900,justify="left").pack(anchor="w",padx=16,pady=(7,12))
        data=self.card(inner,"04  •  Dane treningowe","Wybierz własny TXT / MD / JSONL / CSV. Gdy nic nie wybierzesz, kreator użyje dołączonego zestawu startowego, który służy do testów technicznych, nie do uzyskania jakości komercyjnej.")
        data.pack(fill="x",pady=(0,10))
        dr=tk.Frame(data,bg=PANEL); dr.pack(fill="x",padx=16,pady=(0,12))
        self.entry(dr,self.dataset).pack(side="left",fill="x",expand=True,ipady=8)
        self.button(dr,"WYBIERZ PLIK",self.browse).pack(side="left",padx=8)
        train=self.card(inner,"05  •  Trening i architektura","Trening uruchamia się z poziomu tego okna. Logi, postęp i status pozostają widoczne w GUI.")
        train.pack(fill="x",pady=(0,10))
        g=tk.Frame(train,bg=PANEL); g.pack(fill="x",padx=16,pady=(0,12))
        fields=[("KROKI",self.steps,("1000","2000","5000","10000","25000","50000","100000")),
                ("SZEROKOŚĆ",self.width,("128","256","384","512")),
                ("WARSTWY",self.layers,("4","6","8","12")),
                ("GŁOWICE",self.heads,("4","8","12","16")),
                ("KONTEKST",self.context,("128","256","512","1024")),
                ("BATCH",self.batch,("2","4","8","16")),
                ("URZĄDZENIE",self.device,("Auto","CPU","CUDA","MPS"))]
        for i,(caption,var,opts) in enumerate(fields):
            cell=tk.Frame(g,bg=PANEL); cell.grid(row=i//4,column=i%4,sticky="ew",padx=5,pady=6)
            self.label(cell,caption,8,MUTED,True).pack(anchor="w")
            if caption=="URZĄDZENIE": ttk.Combobox(cell,textvariable=var,values=opts,state="readonly").pack(fill="x",pady=(4,0))
            else: ttk.Combobox(cell,textvariable=var,values=opts).pack(fill="x",pady=(4,0))
            g.columnconfigure(i%4,weight=1)
        bottom=tk.Frame(self.root,bg=BG); bottom.pack(fill="x",padx=24,pady=(6,12))
        tk.Label(bottom,textvariable=self.status,bg=BG,fg=MUTED,font=("Segoe UI",8)).pack(side="left")
        self.button(bottom,"STWÓRZ PROJEKT I TRENUJ  →",self.create_and_train,True).pack(side="right")
        self.progressbar=ttk.Progressbar(self.root,variable=self.progress,maximum=100,mode="determinate")
        self.progressbar.pack(fill="x",padx=24,pady=(0,5))
        self.logs=tk.Text(self.root,height=7,bg="#101018",fg="#c5f5d8",insertbackground=TEXT,
                          relief="flat",font=("Consolas",8),wrap="word")
        self.logs.pack(fill="x",padx=24,pady=(0,14))

    def refresh_github(self):
        ok,detail=github_integration.auth_status()
        self.github_state.set("Połączono z GitHub" if ok else detail.splitlines()[0][:100])

    def connect_github(self):
        try:
            command=github_integration.login_command()
            if os.name=="nt":
                subprocess.Popen(["cmd","/c",*command],creationflags=getattr(subprocess,"CREATE_NEW_CONSOLE",0))
            elif sys.platform=="darwin":
                subprocess.Popen(command)
            else:
                terminal=shutil.which("x-terminal-emulator") or shutil.which("gnome-terminal") or shutil.which("xterm")
                if terminal:
                    subprocess.Popen([terminal,"-e"," ".join(command)])
                else:
                    messagebox.showinfo("GitHub","Uruchom w terminalu: gh auth login --web")
                    return
            self.status.set("Dokończ logowanie w przeglądarce, potem kliknij ODŚWIEŻ.")
        except (OSError,FileNotFoundError) as exc: messagebox.showerror("GitHub",str(exc))

    def browse(self):
        path=filedialog.askopenfilename(filetypes=[("Dane treningowe","*.txt *.md *.jsonl *.csv"),("Wszystkie","*.*")])
        if path: self.dataset.set(path)

    def append_log(self,line):
        self.logs.insert("end",line.rstrip()+"\n"); self.logs.see("end")
        match=re.search(r"Krok\s+(\d[\d,]*)/(\d[\d,]*)",line)
        if match:
            done=int(match.group(1).replace(",","")); total=max(1,int(match.group(2).replace(",","")))
            self.progress.set(done*100/total)

    def create_and_train(self):
        if self.process and self.process.poll() is None:
            messagebox.showwarning("321 AI","Trening już trwa."); return
        try:
            name=safe_name(self.name.get()); repo=self.repo.get().strip()
            if not repo: repo=name
            if "/" in repo:
                owner,repo_name=repo.split("/",1)
                if not owner or not repo_name: raise ValueError("Repozytorium musi mieć format owner/nazwa.")
                repo_name=safe_name(repo_name); full_repo=owner+"/"+repo_name
            else: full_repo=safe_name(repo); 
            active=[k for k,v in self.tasks.items() if v.get()]
            if not active: raise ValueError("Wybierz przynajmniej jeden typ zadania.")
            counts={k:int(self.counts[k].get().replace(",","").replace(" ","")) for k in active}
            if any(v<1 or v>1_000_000 for v in counts.values()): raise ValueError("Liczba przykładów musi być od 1 do 1 000 000.")
            steps=int(self.steps.get())
            if not 1<=steps<=1_000_000: raise ValueError("Kroki muszą być od 1 do 1 000 000.")
            source=Path(self.dataset.get()).expanduser() if self.dataset.get().strip() else None
            if source and (not source.is_file() or source.suffix.lower() not in {".txt",".md",".jsonl",".csv"}):
                raise ValueError("Nieprawidłowy plik danych.")
            if source and source.stat().st_size<2048: raise ValueError("Plik danych musi mieć co najmniej 2048 bajtów.")
            if not self.github_state.get().startswith("Połączono"):
                if not messagebox.askyesno("GitHub","Konto GitHub nie jest połączone. Utworzyć projekt lokalnie bez repozytorium?"): return
            root=Path.home()/"Desktop"/"321 AI Models"
            root.mkdir(parents=True,exist_ok=True)
            project=root/name; project.mkdir(parents=True,exist_ok=False)
            if source:
                dataset_name="dataset"+source.suffix.lower(); shutil.copy2(source,project/dataset_name)
            else:
                bundled=Path(__file__).resolve().parent/"data"/"starter_dataset.txt"
                if not bundled.is_file(): raise FileNotFoundError("Brak wbudowanego datasetu startowego.")
                dataset_name="dataset.txt"; shutil.copy2(bundled,project/dataset_name)
            cfg={"name":name,"repository":full_repo,"training_steps":steps,
                 "device_preference":self.device.get().lower(),"width":int(self.width.get()),
                 "layers":int(self.layers.get()),"heads":int(self.heads.get()),
                 "context":int(self.context.get()),"batch_size":int(self.batch.get()),
                 "dataset_file":dataset_name,"task_mix":counts,
                 "architecture":"321-TinyGPT-byte-v1","trained_from_scratch":True,
                 "resume":True,"eval_interval":max(10,min(500,steps//50)),
                 "save_interval":max(10,min(500,steps//50))}
            if int(cfg["width"])%int(cfg["heads"]): raise ValueError("Szerokość musi być podzielna przez liczbę głowic.")
            (project/"config.json").write_text(json.dumps(cfg,ensure_ascii=False,indent=2),encoding="utf-8")
            (project/"README.md").write_text(
                f"# {name}\n\nAutorski eksperymentalny model 321 AI trenowany od zera.\n\n"
                f"- Typy zadań: {', '.join(active)}\n- Proporcje: {json.dumps(counts,ensure_ascii=False)}\n"
                f"- Kroki: {steps}\n- Dane: {dataset_name}\n\n"
                "Model tekstowy byte-level. Generowanie obrazów nie jest częścią tego checkpointu. "
                "Wyniki zależą od jakości danych i sprzętu.\n",encoding="utf-8")
            self.project=project; self.status.set("Projekt zapisany. Uruchamiam trening…")
            self.append_log(f"Projekt: {project}")
            self.append_log(f"Zadania: {counts} | kroki: {steps}")
            self.root.update_idletasks()
            trainer=Path(__file__).resolve().with_name("ai_trainer.py")
            self.publish_repo=full_repo
            self.publish_private=self.private.get()
            self.publish_enabled=self.github_state.get().startswith("Połączono")
            self.process=subprocess.Popen([sys.executable,"-u",str(trainer),str(project)],
                cwd=project,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,
                text=True,encoding="utf-8",errors="replace",bufsize=1)
            threading.Thread(target=self._read_output,daemon=True).start()
            self.root.after(150,self._poll)
            if self.publish_enabled:
                self.publisher_thread=threading.Thread(target=self._publish_after_training,daemon=True)\n                self.publisher_thread.start()
        except FileExistsError: messagebox.showerror("321 AI","Folder tego modelu już istnieje.")
        except (ValueError,OSError) as exc: messagebox.showerror("321 AI",str(exc))

    def _read_output(self):
        if not self.process or not self.process.stdout: return
        for line in self.process.stdout: self.events.put(("log",line))
        self.events.put(("done",self.process.wait()))

    def _poll(self):
        try:
            while True:
                kind,value=self.events.get_nowait()
                if kind=="log": self.append_log(value)
                else:
                    if value==0:
                        self.progress.set(100); self.status.set("Trening zakończony")
                        self._export_model()
                        messagebox.showinfo("321 AI","Trening zakończony. Wagi i konfiguracja są w folderze model na pulpicie.")
                    else: self.status.set(f"Trening zakończył się błędem ({value}). Sprawdź logi.")
        except queue.Empty: pass
        if (self.process and self.process.poll() is None) or (self.publisher_thread and self.publisher_thread.is_alive()): self.root.after(150,self._poll)

    def _export_model(self):
        if not self.project: return
        target=self.project/"model"
        if target.exists():
            (self.project/"EXPORT_INFO.txt").write_text(
                "Eksport modelu 321 AI. Główne wagi: model/model.pt. "
                "Konfiguracja: config.json. Checkpointy treningowe: checkpoints/.\n"
                "To eksperymentalny model tekstowy byte-level, nie model klasy komercyjnych asystentów.\n",
                encoding="utf-8")

    def _publish_after_training(self):
        # Do not block training or the Tk event loop; GitHub CLI owns credentials.
        try:
            # Wait for process completion without touching Tk from this thread.
            self.process.wait()
            if self.process.returncode==0:
                result=github_integration.publish_repository(self.project,self.publish_repo,self.publish_private)
                self.events.put(("log","GitHub: "+result))
        except Exception as exc: self.events.put(("log","GitHub publikacja: "+str(exc)))


def main() -> int:
    root=tk.Tk(); CreatorV2(root); root.mainloop(); return 0


if __name__=="__main__": raise SystemExit(main())
