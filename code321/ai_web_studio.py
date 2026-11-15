"""Responsive browser-based 321 AI Creator. Start with: 321 ai web."""
from __future__ import annotations

import argparse
import hmac
import json
import os
import re
import secrets
import shutil
import subprocess
import sys
import threading
from pathlib import Path

try:
    from fastapi import FastAPI, File, Form, HTTPException, Request, Response, UploadFile
    from fastapi.responses import HTMLResponse
except ImportError as exc:
    raise RuntimeError("Zainstaluj dodatki WWW: pip install '321code-lang[api]'") from exc

APP_DIR = Path(__file__).resolve().parent
REPO_ROOT = APP_DIR.parent
STATE = {"process": None, "logs": [], "status": "Gotowy", "project": None, "progress": 0}
LOCK = threading.Lock()
PANEL_KEY = os.environ.get("321_AI_WEB_KEY") or secrets.token_urlsafe(24)

HTML = r"""<!doctype html>
<html lang="pl"><head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="theme-color" content="#09090f"><title>321 AI Creator</title>
<style>
:root{color-scheme:dark;--bg:#09090f;--panel:#12121d;--panel2:#191827;--line:#2c2840;--text:#f4f0ff;--muted:#9690a9;--purple:#9565f5;--green:#6fe0ae}
*{box-sizing:border-box}body{margin:0;background:radial-gradient(ellipse at 80% -20%,#26183f 0,transparent 42%),var(--bg);color:var(--text);font:15px Inter,ui-sans-serif,system-ui,Arial}
main{width:min(1050px,100%);margin:auto;padding:28px 22px 50px}.header{display:flex;justify-content:space-between;align-items:center;gap:12px;margin-bottom:24px}
.brand{display:flex;align-items:center;gap:12px}.mark{width:43px;height:43px;border-radius:13px;background:linear-gradient(145deg,#a78bfa,#6335ca);display:grid;place-items:center;font-weight:900;font-size:20px;box-shadow:0 8px 28px #7546dc44}
h1{font-size:22px;margin:0;letter-spacing:-.5px}.subtitle{font-size:12px;color:var(--muted);margin-top:4px}
.pill{border:1px solid #28533f;background:#12251e;color:var(--green);border-radius:30px;padding:8px 12px;font-size:12px;white-space:nowrap}
.intro{padding:24px;border:1px solid var(--line);border-radius:18px;background:linear-gradient(120deg,#1b1730,#11111b 70%);margin-bottom:17px}
.intro h2{font-size:20px;margin:0 0 7px}.intro p{margin:0;color:var(--muted);font-size:13px;line-height:1.6}
.grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:16px}.card{background:var(--panel);border:1px solid var(--line);border-radius:16px;padding:19px;min-width:0}
.card h3{margin:0 0 5px;font-size:15px}.hint{margin:0 0 15px;color:var(--muted);font-size:12px;line-height:1.5}
label{display:block;color:#b9b2ca;font-size:11px;font-weight:650;letter-spacing:.4px;margin:13px 0 6px}
input,select{width:100%;min-width:0;border:1px solid #363149;border-radius:9px;padding:11px 12px;background:var(--panel2);color:var(--text);font:inherit;font-size:13px;outline:none}
input:focus,select:focus{border-color:var(--purple);box-shadow:0 0 0 3px #9565f522}
.two{display:grid;grid-template-columns:1fr 1fr;gap:11px}.task{display:flex;align-items:center;gap:9px;margin:12px 0}.task input{width:17px;height:17px;accent-color:var(--purple)}.task label{margin:0;font-size:13px;letter-spacing:0;font-weight:500}
.actions{display:flex;gap:10px;align-items:center;flex-wrap:wrap;margin-top:17px}
button{border:0;border-radius:10px;background:linear-gradient(120deg,#9868f7,#7044d2);color:white;padding:12px 17px;font-size:12px;font-weight:800;letter-spacing:.3px;cursor:pointer}
button:disabled{opacity:.45;cursor:wait}.secondary{background:#28243a;border:1px solid #3a3450}
.wide{grid-column:1/-1}.progress{height:8px;background:#28243a;border-radius:20px;overflow:hidden;margin-top:17px}.bar{height:100%;width:0;background:linear-gradient(90deg,#7546dc,#b99cff);transition:width .3s}
.log{height:220px;overflow:auto;white-space:pre-wrap;overflow-wrap:anywhere;background:#08080d;border:1px solid #292538;border-radius:10px;padding:13px;color:#a8e8c5;font:12px/1.6 ui-monospace,Consolas,monospace}
.foot{font-size:11px;color:var(--muted);margin-top:18px;text-align:center}
@media(max-width:680px){main{padding:17px 13px 35px}.grid{grid-template-columns:1fr}.wide{grid-column:auto}.intro{padding:18px}.header{align-items:flex-start}.pill{font-size:10px;padding:7px 9px}.two{gap:8px}}
</style></head><body><main>
<header class="header"><div class="brand"><div class="mark">321</div><div><h1>AI Creator</h1><div class="subtitle">MODEL LAB · TRAIN FROM SCRATCH</div></div></div><div class="pill" id="status">● Gotowy</div></header>
<section class="card" id="loginBox"><h3>Logowanie do panelu</h3><p class="hint">Wpisz klucz pokazany w terminalu po uruchomieniu serwera.</p><div class="actions"><input id="loginKey" type="password" placeholder="Klucz dostępu" autocomplete="current-password"><button onclick="login()">ZALOGUJ</button></div></section>\n<section class="intro"><h2>Stwórz własny model AI</h2><p>Skonfiguruj architekturę, dodaj dane i uruchom trening. Panel steruje oryginalnym silnikiem 321 TinyGPT z repozytorium.</p></section>
<div class="grid">
<section class="card"><h3>01 · Projekt</h3><p class="hint">Nazwa i podstawowe ustawienia modelu.</p>
<label for="name">NAZWA MODELU</label><input id="name" value="PurpleModel" maxlength="48">
<label for="steps">KROKI TRENINGOWE</label><select id="steps"><option>1000</option><option>2000</option><option>5000</option><option selected>10000</option><option>25000</option><option>50000</option></select>
<label for="device">URZĄDZENIE</label><select id="device"><option value="auto">Automatyczne</option><option value="cpu">CPU</option><option value="cuda">CUDA</option><option value="mps">MPS</option></select>
</section>
<section class="card"><h3>02 · Architektura</h3><p class="hint">Wymiary modelu Transformer.</p>
<div class="two"><div><label for="width">SZEROKOŚĆ</label><select id="width"><option>128</option><option selected>256</option><option>384</option><option>512</option></select></div><div><label for="layers">WARSTWY</label><select id="layers"><option>4</option><option selected>6</option><option>8</option><option>12</option></select></div>
<div><label for="heads">GŁOWICE</label><select id="heads"><option>4</option><option selected>8</option><option>12</option><option>16</option></select></div><div><label for="context">KONTEKST</label><select id="context"><option>128</option><option selected>256</option><option>512</option><option>1024</option></select></div></div>
<label for="batch">BATCH SIZE</label><select id="batch"><option>2</option><option>4</option><option selected>8</option><option>16</option></select>
</section>
<section class="card"><h3>03 · Dane treningowe</h3><p class="hint">Własny plik TXT, MD, JSONL lub CSV. Bez pliku użyty zostanie zestaw startowy.</p>
<label for="dataset">WYBIERZ DATASET</label><input id="dataset" type="file" accept=".txt,.md,.jsonl,.csv">
<div class="task"><input type="checkbox" id="programming" checked><label for="programming">Programowanie</label></div>
<div class="task"><input type="checkbox" id="conversation" checked><label for="conversation">Rozmowa</label></div>
<div class="task"><input type="checkbox" id="reasoning" checked><label for="reasoning">Rozumowanie</label></div>
</section>
<section class="card"><h3>04 · Proporcje danych</h3><p class="hint">Docelowa liczba przykładów dla każdej kategorii.</p>
<label for="nprog">PROGRAMOWANIE</label><input id="nprog" type="number" min="1" max="1000000" value="2000">
<label for="nchat">ROZMOWA</label><input id="nchat" type="number" min="1" max="1000000" value="2000">
<label for="nreason">ROZUMOWANIE</label><input id="nreason" type="number" min="1" max="1000000" value="1000">
</section>
<section class="card wide"><h3>05 · Trening modelu</h3><p class="hint">Trening działa na serwerze, a postęp i logi są odświeżane automatycznie.</p>
<div class="actions"><button id="start" onclick="startTraining()">▶ STWÓRZ MODEL I TRENUJ</button><button class="secondary" onclick="refreshStatus()">ODŚWIEŻ</button></div>
<div class="progress"><div class="bar" id="bar"></div></div>
</section>
<section class="card wide"><h3>06 · Konsola</h3><p class="hint">Komunikaty i postęp treningu.</p><div class="log" id="logs">321 AI Creator gotowy. Oczekiwanie na konfigurację…</div></section>
</div><div class="foot">321code · Experimental model training studio</div>
</main>
<script>
const panelKey = "__PANEL_KEY__";
const byId = id => document.getElementById(id);
async function startTraining(){
 const button=byId("start");button.disabled=true;
 const data=new FormData();
 ["name","steps","device","width","layers","heads","context","batch","nprog","nchat","nreason"].forEach(id=>data.append(id,byId(id).value));
 ["programming","conversation","reasoning"].forEach(id=>data.append(id,byId(id).checked?"true":"false"));
 const file=byId("dataset").files[0];if(file)data.append("dataset",file);
 try{const response=await fetch("/start",{method:"POST",body:data});const result=await response.json();if(!response.ok)throw new Error(result.detail||"Nie udało się uruchomić treningu.");byId("status").textContent="● Trening uruchomiony";await refreshStatus();}
 catch(error){alert(error.message);button.disabled=false;}
}
async function refreshStatus(){
 try{const response=await fetch("/status",{credentials:"same-origin"});const data=await response.json();if(!response.ok)throw new Error(data.detail||"Błąd statusu");byId("status").textContent="● "+data.status;byId("logs").textContent=data.logs.join("");byId("logs").scrollTop=byId("logs").scrollHeight;byId("bar").style.width=data.progress+"%";if(data.status==="Gotowy"||data.status==="Zakończono"||data.status.startsWith("Błąd"))byId("start").disabled=false;}
 catch(error){byId("status").textContent="● Brak połączenia";}
}
setInterval(refreshStatus,2000);refreshStatus();
</script></body></html>"""

app = FastAPI(title="321 AI Creator Web", docs_url=None, redoc_url=None)


def require_key(value: str | None) -> None:
    if not value or not hmac.compare_digest(value, PANEL_KEY):
        raise HTTPException(status_code=401, detail="Brak lub nieprawidłowy klucz panelu.")


def clean_name(value: str) -> str:
    name = re.sub(r"[^A-Za-z0-9_-]+", "-", value.strip()).strip("-")[:48]
    if not name:
        raise HTTPException(status_code=400, detail="Podaj poprawną nazwę modelu.")
    return name


@app.get("/", response_class=HTMLResponse)
def index():
    return HTMLResponse(HTML)


@app.post("/start")
async def start_training(
    name: str = Form(...), steps: int = Form(...), device: str = Form("auto"),
    width: int = Form(...), layers: int = Form(...), heads: int = Form(...),
    context: int = Form(...), batch: int = Form(...),
    nprog: int = Form(2000), nchat: int = Form(2000), nreason: int = Form(1000),
    programming: bool = Form(False), conversation: bool = Form(False),
    reasoning: bool = Form(False), dataset: UploadFile | None = File(None),
    x_panel_key: str | None = Header(None),
):
    require_key(x_panel_key)
    with LOCK:
        current = STATE["process"]
        if current is not None and current.poll() is None:
            raise HTTPException(status_code=409, detail="Trening już trwa.")

    name = clean_name(name)
    if not (1 <= steps <= 1_000_000 and 64 <= width <= 1024 and
            1 <= layers <= 24 and 1 <= heads <= 16 and width % heads == 0 and
            32 <= context <= 1024 and 1 <= batch <= 32):
        raise HTTPException(status_code=400, detail="Parametry architektury lub treningu są poza dozwolonym zakresem.")

    task_mix = {}
    if programming:
        task_mix["programowanie"] = nprog
    if conversation:
        task_mix["rozmowa"] = nchat
    if reasoning:
        task_mix["rozumowanie"] = nreason
    if not task_mix or any(not 1 <= count <= 1_000_000 for count in task_mix.values()):
        raise HTTPException(status_code=400, detail="Wybierz co najmniej jedno zadanie i poprawne liczby przykładów.")

    root = Path(os.environ.get("321_AI_PROJECTS_DIR", str(Path.home() / "321 AI Models"))).expanduser().resolve()
    root.mkdir(parents=True, exist_ok=True)
    project = root / name
    if project.exists():
        raise HTTPException(status_code=409, detail="Folder projektu już istnieje. Wybierz inną nazwę.")

    project.mkdir()
    try:
        if dataset is not None and dataset.filename:
            suffix = Path(dataset.filename).suffix.lower()
            if suffix not in {".txt", ".md", ".jsonl", ".csv"}:
                raise HTTPException(status_code=400, detail="Obsługiwane formaty: TXT, MD, JSONL, CSV.")
            content = await dataset.read()
            if len(content) < 2048:
                raise HTTPException(status_code=400, detail="Dataset musi mieć co najmniej 2048 bajtów.")
            if len(content) > 100 * 1024 * 1024:
                raise HTTPException(status_code=413, detail="Dataset przekracza limit 100 MB.")
            dataset_name = "dataset" + suffix
            (project / dataset_name).write_bytes(content)
        else:
            bundled = APP_DIR / "data" / "starter_dataset.txt"
            if not bundled.is_file():
                raise HTTPException(status_code=500, detail="Nie znaleziono wbudowanego datasetu startowego.")
            shutil.copy2(bundled, project / "dataset.txt")
            dataset_name = "dataset.txt"

        config = {
            "name": name, "training_steps": steps, "device_preference": device.lower(),
            "width": width, "layers": layers, "heads": heads, "context": context,
            "batch_size": batch, "dataset_file": dataset_name, "task_mix": task_mix,
            "architecture": "321-TinyGPT-byte-v1", "trained_from_scratch": True,
            "resume": True, "eval_interval": max(10, min(500, steps // 50)),
            "save_interval": max(10, min(500, steps // 50)),
        }
        (project / "config.json").write_text(json.dumps(config, ensure_ascii=False, indent=2), encoding="utf-8")
        (project / "README.md").write_text(
            f"# {name}\n\nEksperymentalny model 321 AI trenowany od zera.\n",
            encoding="utf-8",
        )
        trainer = APP_DIR / "ai_trainer.py"
        process = subprocess.Popen(
            [sys.executable, "-u", str(trainer), str(project)],
            cwd=str(project), stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            text=True, encoding="utf-8", errors="replace", bufsize=1,
        )
        with LOCK:
            STATE.update(process=process, logs=[f"Projekt: {project}\n"], status="Trening", project=str(project), progress=0)

        def collect_output():
            assert process.stdout is not None
            for line in process.stdout:
                with LOCK:
                    STATE["logs"].append(line)
                    STATE["logs"] = STATE["logs"][-500:]
                    match = re.search(r"Krok\s+([\d,]+)/([\d,]+)", line)
                    if match:
                        done = int(match.group(1).replace(",", ""))
                        total = max(1, int(match.group(2).replace(",", "")))
                        STATE["progress"] = min(100, round(done * 100 / total, 1))
            code = process.wait()
            with LOCK:
                STATE["status"] = "Zakończono" if code == 0 else f"Błąd ({code})"
                if code == 0:
                    STATE["progress"] = 100

        threading.Thread(target=collect_output, daemon=True).start()
        return {"ok": True, "project": str(project), "message": "Trening uruchomiony."}
    except Exception:
        shutil.rmtree(project, ignore_errors=True)
        raise


@app.get("/status")
def get_status(x_panel_key: str | None = Header(None)):
    require_key(x_panel_key)
    with LOCK:
        return {
            "status": STATE["status"], "logs": list(STATE["logs"][-300:]),
            "progress": STATE["progress"], "project": STATE["project"],
        }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="321 ai web", description="Uruchom przeglądarkowy 321 AI Creator.")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8001)
    args = parser.parse_args(argv)
    try:
        import uvicorn
    except ImportError:
        print("Brak dodatków WWW. Zainstaluj: pip install '321code-lang[api]'")
        return 2
    if not 1 <= args.port <= 65535:
        print("Port musi należeć do zakresu 1–65535.")
        return 2
    print(f"321 AI Creator: http://{args.host}:{args.port}")
    print("Klucz panelu (zachowaj prywatnie): " + PANEL_KEY)
    if args.host not in {"127.0.0.1", "localhost", "::1"}:
        print("UWAGA: panel będzie dostępny z sieci. Udostępniaj adres i klucz wyłącznie zaufanym osobom.")
    uvicorn.run(app, host=args.host, port=args.port, log_level="info")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
