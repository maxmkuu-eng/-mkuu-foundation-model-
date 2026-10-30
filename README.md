# MKUU Foundation Model

A from-scratch, decoder-only Transformer research project targeting approximately 300M parameters and African-language coverage.

## Status
This repository contains the initial model implementation and training scaffolding. It is not a trained or production-ready language model. No pretrained weights are included.

## Zero-budget constraint
The project is designed to run with free, permitted compute only. Do not rent GPUs, subscribe to paid services, or add paid API dependencies. Meaningful 300M-parameter pretraining may not be feasible on free compute; begin with CPU smoke tests and small experiments, then use genuinely free and available GPU sessions with frequent checkpoints.

## Languages
The tokenizer and data pipeline are language-agnostic. Initial evaluation should cover Kiswahili, English, Hausa, Yoruba, Amharic, and additional African languages as licensed data becomes available.

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

## Data rules
Every source must have documented provenance and license/permission. Keep personal or sensitive information out. Deduplicate, filter low-quality text, retain language metadata, and reserve a held-out evaluation split. Never assume that publicly accessible means licensed for training.

## Repository policy
Do not commit large datasets, credentials, API keys, or model checkpoints. Store checkpoints only in a permitted storage location and document their provenance.

## Architecture
Decoder-only Transformer, RMSNorm, rotary position embeddings, causal scaled-dot-product attention, SwiGLU feed-forward layers, and autoregressive next-token prediction.
