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
        from pydantic import BaseModel, Field
    except ImportError as exc:
        raise RuntimeError("Zainstaluj dodatki API: pip install '321code-lang[api]'") from exc
    from .ai_runtime import ModelRuntime
    runtime = ModelRuntime(project, device=device)
    secret = api_key if api_key is not None else os.environ.get("321_AI_API_KEY", "")
    app = FastAPI(title="321 AI API", version="1.0.0", description="Lokalne API dla wytrenowanego modelu 321 AI.")
    class Message(BaseModel):
        role: str
        content: str
    class ChatRequest(BaseModel):
        model: str = "321-ai"
        messages: list[Message]
        max_tokens: int = Field(default=160, ge=1, le=1024)
        temperature: float = Field(default=0.8, ge=0.05, le=2.0)
        top_k: int = Field(default=40, ge=1, le=256)
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
    def chat(body: ChatRequest, authorization: str | None = Header(default=None)):
        authorize(authorization)
        if not body.messages:
            raise HTTPException(status_code=400, detail="messages nie może być puste.")
        messages=[m.model_dump() for m in body.messages]
        last_user=next((m["content"] for m in reversed(messages) if m["role"]=="user"),None)
        if not last_user:
            raise HTTPException(status_code=400, detail="Wymagana jest wiadomość role=user.")
        history=[{"role":m["role"],"content":m["content"]} for m in messages[:-1]]
        try:
            answer=runtime.generate(last_user,body.max_tokens,body.temperature,body.top_k,history)
        except ValueError as exc:
            raise HTTPException(status_code=400,detail=str(exc)) from exc
        return {"id":"321-chat-completion","object":"chat.completion","model":body.model,
                "choices":[{"index":0,"message":{"role":"assistant","content":answer},"finish_reason":"stop"}],
                "usage":{"prompt_tokens":0,"completion_tokens":0,"total_tokens":0}}
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
