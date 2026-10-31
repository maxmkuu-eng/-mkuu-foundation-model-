"FastAPI HTTP inference API for the MKUU Foundation Model prototype."
import os, threading
from pathlib import Path
from typing import Optional
import sentencepiece as spm
import torch
from fastapi import FastAPI, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from model import ModelConfig, MKUUTransformer

CHECKPOINT = Path(os.getenv("MKUU_CHECKPOINT", "/data/last.pt"))
TOKENIZER = Path(os.getenv("MKUU_TOKENIZER", "/data/mkuu_swahili_spm.model"))
DEVICE = torch.device(os.getenv("MKUU_DEVICE", "cpu"))
API_KEY = os.getenv("MKUU_API_KEY", "")
MAX_INPUT_CHARS = int(os.getenv("MKUU_MAX_INPUT_CHARS", "2000"))
MAX_NEW_TOKENS = int(os.getenv("MKUU_MAX_NEW_TOKENS", "128"))
app = FastAPI(title="MKUU Foundation Model API", version="0.1.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["GET","POST"], allow_headers=["*"])
_model = None
_tokenizer = None
_load_error: Optional[str] = None
_lock = threading.Lock()

class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=MAX_INPUT_CHARS)
    max_new_tokens: int = Field(default=96, ge=1, le=MAX_NEW_TOKENS)
    temperature: float = Field(default=0.8, ge=0.0, le=1.5)

def load_model():
    global _model, _tokenizer, _load_error
    with _lock:
        if _model is not None: return
        try:
            if not CHECKPOINT.is_file(): raise FileNotFoundError(f'Checkpoint not found: {CHECKPOINT}')
            if not TOKENIZER.is_file(): raise FileNotFoundError(f'Tokenizer not found: {TOKENIZER}')
            state = torch.load(CHECKPOINT, map_location='cpu', weights_only=False)
            raw = state.get('config') or state.get('model_config')
            if not raw: raise ValueError('Checkpoint is missing model config')
            config = ModelConfig.from_dict(raw)
            tokenizer = spm.SentencePieceProcessor(model_file=str(TOKENIZER))
            if tokenizer.get_piece_size() != config.vocab_size: raise ValueError('Tokenizer vocabulary does not match checkpoint')
            model = MKUUTransformer(config)
            model.load_state_dict(state.get('model', state), strict=True)
            model.to(DEVICE).eval()
            del state
            _tokenizer, _model, _load_error = tokenizer, model, None
        except Exception as exc:
            _load_error = f'{type(exc).__name__}: {exc}'
            raise

@app.get('/')
def root(): return {'name':'MKUU Foundation Model','status':'ready' if _model is not None else 'model_not_loaded','provider':'local_mkuu_checkpoint'}

@app.get('/health')
def health(): return {'status':'ready' if _model is not None else 'not_ready','checkpoint_exists':CHECKPOINT.is_file(),'tokenizer_exists':TOKENIZER.is_file(),'device':str(DEVICE),'error':_load_error}

@app.post('/chat')
def chat(request: ChatRequest, x_mkuu_key: Optional[str] = Header(default=None)):
    if API_KEY and x_mkuu_key != API_KEY: raise HTTPException(status_code=401, detail='Invalid MKUU API key')
    try: load_model()
    except Exception as exc: raise HTTPException(status_code=503, detail=f'MKUU model is not ready: {exc}')
    prompt = f'<|user|>\n{request.message.strip()}\n<|assistant|>\n'
    ids = _tokenizer.encode(prompt, out_type=int)
    if not ids: raise HTTPException(status_code=400, detail='Prompt could not be tokenized')
    generated, eos = list(ids), _tokenizer.eos_id()
    with torch.inference_mode():
        for _ in range(request.max_new_tokens):
            x = torch.tensor([generated[-_model.config.max_seq_len:]], dtype=torch.long, device=DEVICE)
            logits = _model(x)['logits'][0,-1].float()
            if request.temperature == 0: next_id = int(torch.argmax(logits).item())
            else:
                logits /= request.temperature
                k = min(40, logits.numel())
                threshold = torch.topk(logits, k).values[-1]
                logits[logits < threshold] = -torch.inf
                next_id = int(torch.multinomial(torch.softmax(logits, dim=-1), 1).item())
            generated.append(next_id)
            if eos >= 0 and next_id == eos: break
    answer = _tokenizer.decode(generated[len(ids):]).strip()
    for marker in ('<|user|>','<|assistant|>','<|system|>'): answer = answer.split(marker,1)[0].strip()
    return {'answer':answer,'model':'MKUU Foundation Model','source':'project_checkpoint','warning':'Pretraining-only prototype; conversational fine-tuning and evaluation are still required.'}
