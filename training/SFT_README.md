# Supervised fine-tuning (SFT)

This is a separate conversational fine-tuning stage. It reuses the existing MKUU Transformer and SentencePiece tokenizer. It expects JSONL records with `messages` (ordered `system`, `user`, `assistant` roles), plus non-empty `license` and `source` provenance fields.

Only assistant response tokens are included in the loss; system/user prompt tokens are masked. Conversation text is serialized with role markers such as `<|user|>` and `<|assistant|>`. These markers are ordinary tokenizer text, not special tokens unless the tokenizer was explicitly trained/configured to recognize them.

## Before running
1. Obtain a tokenizer model and a base checkpoint compatible with the configured vocabulary and model dimensions. The repository currently has no trained tokenizer or pretrained checkpoint.
2. Review every training record's permission/license and provenance. Do not use private conversations without explicit permission.
3. Split train/validation/test by source or conversation before training; do not evaluate on training examples.
4. Start with a tiny model config and a tiny reviewed dataset for a smoke test. The 300M configuration is unlikely to train meaningfully on a phone or ordinary CPU.
5. Keep checkpoints out of Git; store only in permitted storage.

## Run
```bash
python training/sft.py --config configs/sft_300m.yaml --data data/processed/behaviour_train.jsonl --tokenizer artifacts/mkuu_spm.model --init-checkpoint checkpoints/pretrain/last.pt
```

For a pipeline smoke test before a base checkpoint exists, omit `--init-checkpoint`; this initializes random weights and is only useful to verify code execution, not to create a capable assistant.

## Limitations
This reference implementation is single-process and does not yet include validation metrics, packing, mixed precision, distributed training, LoRA/PEFT, or robust chat-template special-token registration. It saves resumable model/optimizer state, but a separate evaluation step is required before claiming improvements.
