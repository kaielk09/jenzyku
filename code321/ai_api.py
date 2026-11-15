"""Optional OpenAI-compatible HTTP API for a local 321 AI model.

Install: pip install '321code-lang[api]'
Run: 321 ai serve <project-folder>
"""
from __future__ import annotations
import hmac, os
from pathlib import Path
from typing import Any

def create_app(project: str | Path, api_key: str | None = None, device: str = "auto"):
    try:
        from fastapi import FastAPI, Header, HTTPException
    except ImportError as exc:
        raise RuntimeError("Zainstaluj dodatki API: pip install '321code-lang[api]'") from exc
    from .ai_runtime import ModelRuntime
    runtime = ModelRuntime(project, device=device)
    secret = api_key if api_key is not None else os.environ.get("321_AI_API_KEY", "")
    app = FastAPI(title="321 AI API", version="1.0.0", description="Lokalne API dla wytrenowanego modelu 321 AI.")
    def authorize(authorization: str | None):
        if not secret:
            return
        supplied = (authorization or "").removeprefix("Bearer ").strip()
        if not hmac.compare_digest(supplied, secret):
            raise HTTPException(status_code=401, detail="Nieprawidłowy klucz API.")
    @app.get("/health")
    def health():
        return {"status":"ok","model_loaded":True,"model":runtime.info.get("name",Path(project).name),
                "parameters":runtime.parameter_count,"device":runtime.device}
    @app.get("/v1/models")
    def models(authorization: str | None = Header(default=None)):
        authorize(authorization)
        return {"object":"list","data":[{"id":runtime.info.get("name",Path(project).name),"object":"model","owned_by":"321code"}]}
    @app.post("/v1/chat/completions")
    def chat(body: dict, authorization: str | None = Header(default=None)):
        authorize(authorization)
        messages=body.get("messages") if isinstance(body,dict) else None
        if not isinstance(messages,list) or not messages:
            raise HTTPException(status_code=400, detail="messages musi być niepustą listą.")
        if any(not isinstance(m,dict) or m.get("role") not in {"system","user","assistant"} or not isinstance(m.get("content"),str) for m in messages):
            raise HTTPException(status_code=400, detail="Każda wiadomość musi zawierać role i tekst content.")
        last_user=next((m["content"] for m in reversed(messages) if m["role"]=="user"),None)
        if not last_user:
            raise HTTPException(status_code=400, detail="Wymagana jest wiadomość role=user.")
        try:
            max_tokens=int(body.get("max_tokens",160)); temperature=float(body.get("temperature",0.8)); top_k=int(body.get("top_k",40))
            history=[{"role":m["role"],"content":m["content"]} for m in messages[:-1]]
            answer=runtime.generate(last_user,max_tokens,temperature,top_k,history)
        except (ValueError,TypeError) as exc:
            raise HTTPException(status_code=400,detail=str(exc)) from exc
        return {"id":"321-chat-completion","object":"chat.completion","model":str(body.get("model","321-ai")),
                "choices":[{"index":0,"message":{"role":"assistant","content":answer},"finish_reason":"stop"}],
                "usage":{"prompt_tokens":0,"completion_tokens":0,"total_tokens":0}}
    @app.post("/v1/images/sample")
    def sample_image(body: dict, authorization: str | None = Header(default=None)):
        authorize(authorization)
        import base64
        import io
        image_checkpoint = Path(os.environ.get("321_AI_IMAGE_MODEL", str(Path(project) / "image_model")))
        if image_checkpoint.is_dir():
            image_checkpoint = image_checkpoint / "image_model.pt"
        if not image_checkpoint.is_file():
            raise HTTPException(status_code=503, detail="Brak wytrenowanego modelu obrazowego. Ustaw 321_AI_IMAGE_MODEL na folder lub plik image_model.pt.")
        try:
            count = int(body.get("n", 1))
            if not 1 <= count <= 4: raise ValueError("n musi należeć do zakresu 1–4.")
            from .ai_image_generate import sample_images
            images = sample_images(image_checkpoint, count=count, device=runtime.device, seed=body.get("seed"))
            encoded=[]
            for image in images:
                buffer=io.BytesIO(); image.save(buffer,format="PNG")
                encoded.append(base64.b64encode(buffer.getvalue()).decode("ascii"))
            return {"object":"list","data":[{"b64_json":item,"size":"64x64"} for item in encoded],
                    "model":"321-ImageDDPM-unconditional","prompt_conditioning":False}
        except (ValueError,TypeError,FileNotFoundError) as exc:
            raise HTTPException(status_code=400,detail=str(exc)) from exc
        except Exception as exc:
            raise HTTPException(status_code=500,detail=f"Błąd modelu obrazowego: {exc}") from exc
    return app

def main(argv=None):
    import argparse
    parser=argparse.ArgumentParser(prog="321 ai serve")
    parser.add_argument("project")
    parser.add_argument("--host",default="127.0.0.1")
    parser.add_argument("--port",type=int,default=8000)
    parser.add_argument("--device",choices=("auto","cpu","cuda","mps"),default="auto")
    args=parser.parse_args(argv)
    if args.host not in {"127.0.0.1", "localhost", "::1"} and not os.environ.get("321_AI_API_KEY"):
        print("Dla nasłuchiwania poza localhost ustaw 321_AI_API_KEY. Nie uruchamiam niezabezpieczonego API.")
        return 2
    try:
        import uvicorn
        app=create_app(args.project,device=args.device)
    except (ImportError,RuntimeError,FileNotFoundError,ValueError) as exc:
        print(f"Nie można uruchomić API: {exc}")
        return 2
    print(f"321 AI API: http://{args.host}:{args.port}  |  /health  |  /v1/chat/completions")
    uvicorn.run(app,host=args.host,port=args.port)
    return 0

if __name__=="__main__":
    raise SystemExit(main())
