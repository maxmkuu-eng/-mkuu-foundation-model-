# Tokenizer corpus preparation

Use approved JSONL files with non-empty `license` and `source` fields. The builder accepts either `text` records or conversational `messages` records and exports only the train split.

```bash
python data/build_tokenizer_corpus.py --input data/approved/text.jsonl data/behaviour_seed.jsonl --output data/processed/tokenizer_train.txt
python tokenizer/train_tokenizer.py --input data/processed/tokenizer_train.txt --model-prefix artifacts/mkuu_spm --vocab-size 48000
```

The eight synthetic dialogue examples are only a tiny smoke-test seed. They are not enough to train a useful multilingual tokenizer or language model. Add a substantial, balanced, reviewed corpus before serious training. Check the actual vocabulary size printed by SentencePiece and use that exact value in the model config; `hard_vocab_limit=False` may produce fewer pieces than requested.

Keep validation and test records out of tokenizer training where possible. Do not commit corpora or tokenizer artifacts to Git.
