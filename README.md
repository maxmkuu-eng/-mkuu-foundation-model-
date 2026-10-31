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

Split a reviewed corpus by document (deterministic 80/10/10 target; all records
from one document stay together). Each row must include `document_id`:
```bash
python data/split_dataset.py --input data/processed/all.jsonl --output-dir data/approved
```
This writes `train.jsonl`, `validation.jsonl` and `test.jsonl`. The splitter
rejects missing provenance and exact duplicate text. Review split counts and
source balance before training; the ratios are targets, not a quality guarantee.

Prepare licensed JSONL records:
```bash
python data/prepare_jsonl.py --input data/raw/input.jsonl --output data/processed/train.jsonl
```

Generate locally from a trained checkpoint (no hosted model/API):
```bash
python scripts/generate.py --checkpoint checkpoints/sft/last.pt --tokenizer artifacts/mkuu_spm.model --prompt "Habari, unaweza kujitambulisha?"
```

Evaluate only on a separately held-out, provenance-labelled split:
```bash
python scripts/evaluate.py --checkpoint checkpoints/pretrain/last.pt --tokenizer artifacts/mkuu_spm.model --data data/approved/test.jsonl --split test
```
Each evaluation record must include `text`, `license`, `source`, and `split=test`. The script reports token-weighted cross-entropy and perplexity; these metrics do not replace human evaluation.

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

## Offline speech output (TTS)
MKUU now has a basic offline Swahili speech-output adapter based on the open-source eSpeak NG engine. It speaks text through the host audio output or creates a WAV file. Install the system engine first:

```bash
sudo apt install espeak-ng
python -m speech.tts_espeak "Habari, karibu MKUU AI."
python -m speech.tts_espeak "Habari, karibu MKUU AI." --output artifacts/mkuu_reply.wav
```

The default voice is eSpeak NG's `sw` Swahili voice. It is synthetic and can sound robotic; Tanzanian native-speaker evaluation and a more natural voice are future work. The Python adapter does not yet add microphone input or integrate playback controls into the separate Android app. See `speech/SPEECH_SPEC.md`.

## Data rules
Follow `data/SOURCES.md` and `data/RAW_DATA_README.md` for source admission and intake. For the inspected Swahili text source, see `data/SWAHILI_CORPUS_CLEANING.md` and run `data/clean_swahili_corpus.py`; its output is marked project-owner approved by the corpus workflow. Review-held rows remain excluded. The restore workflow creates deterministic document-level train/validation/test splits and a SentencePiece tokenizer artifact. Every source must have documented provenance and license/permission. Keep personal or sensitive information out. Deduplicate, filter low-quality text, retain language metadata, and reserve a held-out evaluation split. Never assume that publicly accessible means licensed for training.

## Repository policy
Do not commit large datasets, credentials, API keys, or model checkpoints. Store checkpoints only in a permitted storage location and document their provenance.

## Architecture
Decoder-only Transformer, RMSNorm, rotary position embeddings, causal scaled-dot-product attention, SwiGLU feed-forward layers, and autoregressive next-token prediction.


## Online speech output (TTS)

An online adapter for TTS.ai is available in `speech/tts_online.py`. It submits text, waits for the generated audio and saves an MP3. Run `python -m speech.tts_online --list-voices` to inspect the provider's current Swahili voice catalogue. The provider documents an anonymous free allowance of 5,000 characters/day, up to 500 characters per request. The configured Swahili Piper voice `Lanfrica` is marked **non-commercial only** by the provider; the adapter requires an explicit acknowledgement and it must not be enabled in a commercial MKUU release. This is a test integration, not unlimited hosting. See `speech/SPEECH_SPEC.md` and `configs/speech.yaml`. The separate Android app is not yet connected to this adapter; this repository has no deployed chat backend or Android playback UI.


## Common Voice intake

See [data/COMMON_VOICE_INTAKE.md](data/COMMON_VOICE_INTAKE.md) for the tested TSV importer, privacy filtering, provenance fields and safe local intake workflow. No raw dataset is committed.
