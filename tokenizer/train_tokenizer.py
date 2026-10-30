import argparse
from pathlib import Path
import sentencepiece as spm

CHAT_MARKERS = ["<|system|>", "<|user|>", "<|assistant|>"]

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--input", required=True)
    p.add_argument("--model-prefix", default="artifacts/mkuu_spm")
    p.add_argument("--vocab-size", type=int, default=48000)
    p.add_argument("--character-coverage", type=float, default=0.9995)
    a = p.parse_args()
    Path(a.model_prefix).parent.mkdir(parents=True, exist_ok=True)
    spm.SentencePieceTrainer.train(
        input=a.input, model_prefix=a.model_prefix, vocab_size=a.vocab_size,
        model_type="unigram", character_coverage=a.character_coverage,
        pad_id=0, unk_id=1, bos_id=2, eos_id=3, hard_vocab_limit=False,
        user_defined_symbols=CHAT_MARKERS
    )
    processor = spm.SentencePieceProcessor(model_file=a.model_prefix + ".model")
    print(f"Tokenizer trained: {a.model_prefix}.model")
    print(f"Actual vocabulary size: {processor.get_piece_size()}")

if __name__ == "__main__":
    main()
