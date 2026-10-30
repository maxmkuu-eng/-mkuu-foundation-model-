# MKUU Foundation Model

A from-scratch, decoder-only Transformer research project targeting approximately 300M parameters. The long-term goal is worldwide multilingual support, with deliberate priority for African languages.

## Status
This repository contains the initial model implementation and training scaffolding. It is not a trained or production-ready language model. No pretrained weights are included.

## Zero-budget constraint
The project is designed to run with free, permitted compute only. Do not rent GPUs, subscribe to paid services, or add paid API dependencies. Meaningful 300M-parameter pretraining may not be feasible on free compute; begin with CPU smoke tests and small experiments, then use genuinely free and available GPU sessions with frequent checkpoints.

## Languages
There is no fixed 12-language limit. The list in `data/languages.yaml` is an initial planning list, not the boundary of the model's language coverage. Expand toward languages worldwide as suitable licensed data and competent evaluation become available. Give African languages deliberate priority. Do not claim support for a language before evaluating it with fluent speakers.

## Conversational behaviour
See `docs/BEHAVIOUR_SPEC.md` and `configs/behaviour.yaml`. The intended character is warm, playful and naturally humorous, with good tone control. Tanzanian Kiswahili must include both standard usage and authentic everyday mtaani language, idioms, shorthand and natural Swanglish. The model should support broad, open discussion without unnecessary refusals, while retaining proportionate safeguards against facilitating real-world harm. These are design targets, not capabilities of the current untrained model.

## Quick start
```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python scripts/print_model_size.py --config configs/model_300m.yaml
pytest -q
```

Train a SentencePiece tokenizer only on text you are permitted to use:
```bash
python tokenizer/train_tokenizer.py --input data/processed/train.txt --model-prefix artifacts/mkuu_spm --vocab-size 48000
```

Prepare licensed JSONL records:
```bash
python data/prepare_jsonl.py --input data/raw/input.jsonl --output data/processed/train.jsonl
```

Training requires a trained tokenizer and a prepared dataset:
```bash
python training/pretrain.py --config configs/model_300m.yaml --data data/processed/train.jsonl --tokenizer artifacts/mkuu_spm.model
```

## Tokenizer and conversational fine-tuning
Build tokenizer text from approved train-split JSONL records (text or role-labelled conversations):
```bash
python data/build_tokenizer_corpus.py --input data/approved/train.jsonl data/behaviour_seed.jsonl --output data/processed/tokenizer_train.txt
python tokenizer/train_tokenizer.py --input data/processed/tokenizer_train.txt --model-prefix artifacts/mkuu_spm --vocab-size 48000
```
Use the actual vocabulary size printed by SentencePiece in the model config. See `tokenizer/TOKENIZER_DATA_README.md`. A tiny smoke-test model config is provided at `configs/model_tiny_smoke.yaml`; it is for pipeline checks only, not quality training.

## Voice / speech
The intended speech architecture is documented in `speech/SPEECH_SPEC.md` and `configs/speech.yaml`. It requires a speech-to-text component for listening and text-to-speech for spoken replies. These are design targets only; no audio runtime or working voice capability is included yet.

## Data rules
Follow `data/SOURCES.md` and `data/RAW_DATA_README.md` for source admission and intake. Every source must have documented provenance and license/permission. Keep personal or sensitive information out. Deduplicate, filter low-quality text, retain language metadata, and reserve a held-out evaluation split. Never assume that publicly accessible means licensed for training.

## Repository policy
Do not commit large datasets, credentials, API keys, or model checkpoints. Store checkpoints only in a permitted storage location and document their provenance.

## Architecture
Decoder-only Transformer, RMSNorm, rotary position embeddings, causal scaled-dot-product attention, SwiGLU feed-forward layers, and autoregressive next-token prediction.
