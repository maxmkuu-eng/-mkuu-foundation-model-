MKUU Foundation Model test inference server

This HTTP service loads this repository's own MKUUTransformer checkpoint and matching SentencePiece tokenizer. It does not call Gemini, OpenAI, Groq, or another hosted LLM.

Run: pip install -r server/requirements.txt
Then set MKUU_CHECKPOINT=/data/last.pt and MKUU_TOKENIZER=/data/mkuu_swahili_spm.model and run: uvicorn server.app:app --host 0.0.0.0 --port 7860

Endpoints: GET /, GET /health, POST /chat with JSON {"message":"Habari MKUU"}. Optional settings: MKUU_CHECKPOINT, MKUU_TOKENIZER, MKUU_DEVICE (cpu by default), MKUU_API_KEY, MKUU_MAX_INPUT_CHARS and MKUU_MAX_NEW_TOKENS. When MKUU_API_KEY is set, clients must send X-Mkuu-Key.

The Dockerfile is suitable for a Docker-based hosted container, subject to the provider's current free-tier quotas, sleeping and memory limits. Do not commit model checkpoints to this Git repository; attach them as model artifacts or mounted storage.

Important: the current pilot checkpoint is pretraining-only, not instruction/chat fine-tuned. This API makes the checkpoint testable but does not make its outputs conversational. Expect weak or continuation-like responses until supervised conversational fine-tuning and evaluation are completed. A free host is for testing, not guaranteed always-on production.