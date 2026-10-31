"""MKUU Foundation Model HTTP chat API with lightweight live web retrieval."""
import hmac
import os
from contextlib import asynccontextmanager
from typing import Literal

import requests
import torch
from bs4 import BeautifulSoup
from fastapi import FastAPI, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
import sentencepiece as spm

from scripts.generate import generate, load_model

CHECKPOINT = os.getenv("MKUU_CHECKPOINT", "/content/drive/MyDrive/MKUU-Foundation-Model/checkpoints/last.pt")
TOKENIZER = os.getenv("MKUU_TOKENIZER", "/content/drive/MyDrive/MKUU-Foundation-Model/mkuu_swahili_spm.model")
API_TOKEN = os.getenv("MKUU_API_TOKEN", "")
MAX_HISTORY_MESSAGES = 4
runtime = {"model": None, "tokenizer": None, "device": None, "load_error": None}


class HistoryMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str = Field(min_length=1, max_length=1200)


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=2000)
    history: list[HistoryMessage] = Field(default_factory=list, max_length=MAX_HISTORY_MESSAGES)
    max_new_tokens: int = Field(default=128, ge=16, le=256)


def search_web(query: str, limit: int = 5) -> list[dict]:
    """Fetch public web snippets using DuckDuckGo HTML; no search API key required."""
    try:
        response = requests.get(
            "https://html.duckduckgo.com/html/",
            params={"q": query[:300]},
            headers={"User-Agent": "Mozilla/5.0 (compatible; MKUUFoundationChat/0.1)"},
            timeout=12,
        )
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")
        results = []
        for item in soup.select(".result"):
            link = item.select_one("a.result__a")
            snippet = item.select_one(".result__snippet")
            if not link or not link.get("href"):
                continue
            results.append({
                "title": link.get_text(" ", strip=True)[:240],
                "url": link["href"],
                "snippet": snippet.get_text(" ", strip=True)[:450] if snippet else "",
            })
            if len(results) >= limit:
                break
        return results
    except requests.RequestException:
        return []


def build_prompt(message: str, history: list[HistoryMessage], sources: list[dict]) -> str:
    context = "\n".join(
        f"[{i + 1}] {item['title']}\nURL: {item['url']}\n{item['snippet']}"
        for i, item in enumerate(sources)
    ) or "Hakuna matokeo ya mtandao yaliyopatikana kwa swali hili."
    parts = [
        "<|system|>\n"
        "Wewe ni MKUU AI, msaidizi wa mazungumzo. Jibu kwa Kiswahili cha kawaida cha Tanzania "
        "isipokuwa mtumiaji atumie lugha nyingine. Tumia taarifa za mtandao zilizo chini pale "
        "zinapohusika. Usibuni ukweli, tarehe, au vyanzo. Ikiwa ushahidi hautoshi, sema hivyo. "
        "Taja namba za vyanzo [1], [2] ndani ya jibu inapofaa. Majibu yawe mafupi na yenye msaada.\n"
        f"TAARIFA ZA MTANDAO:\n{context}\n"
    ]
    for item in history[-MAX_HISTORY_MESSAGES:]:
        parts.append(f"<|{item.role}|>\n{item.content}\n")
    parts.append(f"<|user|>\n{message.strip()}\n<|assistant|>\n")
    return "".join(parts)


@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        if not os.path.isfile(CHECKPOINT):
            raise FileNotFoundError(f"Checkpoint not found: {CHECKPOINT}")
        if not os.path.isfile(TOKENIZER):
            raise FileNotFoundError(f"Tokenizer not found: {TOKENIZER}")
        device = "cuda" if torch.cuda.is_available() else "cpu"
        tokenizer = spm.SentencePieceProcessor(model_file=TOKENIZER)
        model = load_model(CHECKPOINT, None, device)
        if tokenizer.get_piece_size() != model.config.vocab_size:
            raise ValueError(
                f"Tokenizer vocabulary {tokenizer.get_piece_size()} does not match "
                f"checkpoint vocabulary {model.config.vocab_size}"
            )
        runtime.update(model=model, tokenizer=tokenizer, device=device, load_error=None)
        print(f"MKUU model loaded on {device}; vocab={tokenizer.get_piece_size()}", flush=True)
    except Exception as exc:
        runtime["load_error"] = str(exc)
        print(f"MKUU model failed to load: {exc}", flush=True)
    yield
    runtime.update(model=None, tokenizer=None, device=None)


app = FastAPI(title="MKUU Foundation Model API", version="0.1.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["Authorization", "Content-Type"],
)


@app.get("/health")
def health():
    return {
        "status": "ok" if runtime["model"] is not None else "model_unavailable",
        "model_loaded": runtime["model"] is not None,
        "device": runtime["device"],
        "load_error": runtime["load_error"],
    }


@app.post("/chat")
def chat(payload: ChatRequest, authorization: str | None = Header(default=None)):
    if API_TOKEN and not hmac.compare_digest(authorization or "", f"Bearer {API_TOKEN}"):
        raise HTTPException(status_code=401, detail="Invalid or missing access token")
    if runtime["model"] is None:
        raise HTTPException(status_code=503, detail=f"MKUU model is not loaded: {runtime['load_error']}")
    sources = search_web(payload.message)
    prompt = build_prompt(payload.message, payload.history, sources)
    reply = generate(
        runtime["model"], runtime["tokenizer"], prompt,
        max_new_tokens=payload.max_new_tokens, temperature=0.7,
        top_k=40, top_p=0.9, repetition_penalty=1.08, device=runtime["device"],
    ).strip()
    if not reply:
        reply = "Samahani, sijapata jibu linaloeleweka. Jaribu kuuliza tena kwa namna nyingine."
    return {
        "reply": reply, "sources": sources, "model": "MKUU Foundation Model",
        "model_loaded": True, "retrieval": "DuckDuckGo HTML",
    }
