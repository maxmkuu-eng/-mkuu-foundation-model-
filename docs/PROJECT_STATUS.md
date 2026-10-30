# MKUU Foundation Model — project status

## What exists in this repository
- A decoder-only Transformer implementation: RMSNorm, rotary position embeddings, causal attention and SwiGLU.
- A configurable 16-layer, 1024-hidden-size architecture targeting roughly 300M parameters.
- SentencePiece tokenizer training script.
- JSONL data validation, normalization and exact-text deduplication.
- A basic autoregressive training loop with gradient accumulation and checkpoint saving/resume.
- Small unit tests and a GitHub Actions CPU test workflow.

## Dataset preparation progress
- Added an initial 12-language coverage plan in `data/languages.yaml`.
- Added source licensing/provenance admission rules in `data/SOURCES.md` and raw intake instructions in `data/RAW_DATA_README.md`.
- Fixed newline output in the JSONL-to-text export script.
- No corpus has yet been collected, license-reviewed or approved; no source should be treated as admitted.

## What does not exist yet
- No trained tokenizer model.
- No curated or licensed training corpus.
- No pretrained weights or checkpoint.
- No completed pretraining run.
- No Android APK or on-device inference runtime.
- No measured test report yet. CI must run on GitHub before tests can be called passing.

## Parameter target
The configured dimensions imply approximately 304M parameters with untied token embeddings and output projection. Run the parameter-count script and record its actual output before treating the count as verified.

## Zero-budget reality
A 300M model can be prototyped on CPU with tiny synthetic data, but meaningful pretraining needs a large corpus and substantial compute. Free hosted GPU sessions are limited, interruptible and not guaranteed. This repository does not rent compute or depend on paid APIs.

## Safe data requirements
Only use datasets whose licenses explicitly permit the intended training use. Keep source, license, language and provenance metadata. Do not place secrets, private user data, or large datasets/checkpoints in Git.

## Android testing path
An APK can be built as a test client once a stable inference artifact and tokenizer format are selected. A random-initialized model is not a useful conversational assistant. Do not label a UI demo as a working AI model. The Android packaging stage is blocked on trained/exported model weights and a tested mobile inference path.
