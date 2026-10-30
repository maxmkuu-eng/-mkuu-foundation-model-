# MKUU Foundation Model — project status

## What exists in this repository
- A decoder-only Transformer implementation: RMSNorm, rotary position embeddings, causal attention and SwiGLU.
- A configurable 16-layer, 1024-hidden-size architecture targeting roughly 300M parameters.
- SentencePiece tokenizer training script.
- JSONL data validation, normalization and exact-text deduplication.
- A basic autoregressive training loop with gradient accumulation and checkpoint saving/resume.
- Conversational behaviour specification in `docs/BEHAVIOUR_SPEC.md` and intended behaviour settings in `configs/behaviour.yaml`.
- Eight original synthetic Tanzanian Kiswahili dialogue examples in `data/behaviour_seed.jsonl`, with usage and licensing notes in `data/BEHAVIOUR_DATA_README.md`.
- Initial supervised conversation fine-tuning script in `training/sft.py`, with `configs/sft_300m.yaml` and usage/limitations in `training/SFT_README.md`.
- Tokenizer corpus builder in `data/build_tokenizer_corpus.py`; SentencePiece training now registers chat role markers and reports the actual vocabulary size.
- Tiny 128-hidden, 2-layer smoke-test config in `configs/model_tiny_smoke.yaml`.
- Offline Swahili TTS adapter in `speech/tts_espeak.py`, using the system eSpeak NG executable to play speech or write WAV files.
- Speech input/output design and integration targets in `speech/SPEECH_SPEC.md` and `configs/speech.yaml`.
- SFT masks system/user prompt tokens and computes loss on assistant response tokens only; seed examples include explicit synthetic provenance.
- Small unit tests and a GitHub Actions CPU test workflow.

## Dataset preparation progress
- An initial 12-language planning list exists in `data/languages.yaml`; this is not a fixed limit. The long-term target is worldwide multilingual support, with deliberate priority for African languages.
- Added source licensing/provenance admission rules in `data/SOURCES.md` and raw intake instructions in `data/RAW_DATA_README.md`.
- Fixed newline output in the JSONL-to-text export script.
- No corpus has yet been collected, license-reviewed or approved; no source should be treated as admitted.

## Conversational behaviour targets
- Broad, open-topic discussion without unnecessary refusals or moralising; proportionate safeguards remain for requests that would facilitate real-world harm.
- Natural Tanzanian Kiswahili, including standard usage, mtaani slang, idioms, shorthand and Swanglish.
- Warm, playful, witty conversation and friendly humour, without forcing jokes into every answer.
- Tone adaptation: serious and careful when the situation calls for it.
- Multilingual conversational registers, humour and cultural context should be learned and evaluated separately for each language.
- These are specifications for future training and evaluation, not capabilities already demonstrated by the untrained model.

## Speech status
- Implemented: offline eSpeak NG Swahili TTS adapter; can synthesize text to WAV or invoke local playback when the eSpeak NG executable is installed.
- Not implemented: speech recognition/listening (ASR), microphone capture, Android app integration, barge-in controls, or a trained natural Tanzanian voice.
- eSpeak NG's Swahili voice is a basic synthetic baseline and must not be described as a natural Tanzanian voice without native-speaker evaluation.

## What does not exist yet
- No trained tokenizer model.
- No curated or licensed training corpus.
- No pretrained weights or checkpoint.
- No completed pretraining run.
- No Android APK or on-device inference runtime.
- No ASR model or speech checkpoints; microphone capture and Android app integration remain unimplemented.
- The SFT pipeline has been added but has not yet been executed end-to-end; it still needs a compatible tokenizer and base checkpoint. No measured SFT quality report exists.

## Parameter target
The configured dimensions imply approximately 304M parameters with untied token embeddings and output projection. Run the parameter-count script and record its actual output before treating the count as verified.

## Zero-budget reality
A 300M model can be prototyped on CPU with tiny synthetic data, but meaningful pretraining needs a large corpus and substantial compute. Free hosted GPU sessions are limited, interruptible and not guaranteed. This repository does not rent compute or depend on paid APIs.

## Safe data requirements
Only use datasets whose licenses explicitly permit the intended training use. Keep source, license, language and provenance metadata. Do not place secrets, private user data, or large datasets/checkpoints in Git.

## Android testing path
An APK can be built as a test client once a stable inference artifact and tokenizer format are selected. A random-initialized model is not a useful conversational assistant. Do not label a UI demo as a working AI model. The Android packaging stage is blocked on trained/exported model weights and a tested mobile inference path.
