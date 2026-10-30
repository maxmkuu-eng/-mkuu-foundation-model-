import argparse
import sentencepiece as spm

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--input", required=True)
    p.add_argument("--model-prefix", default="artifacts/mkuu_spm")
    p.add_argument("--vocab-size", type=int, default=48000)
    a = p.parse_args()
    spm.SentencePieceTrainer.train(
        input=a.input, model_prefix=a.model_prefix, vocab_size=a.vocab_size,
        model_type="unigram", character_coverage=0.9995,
        pad_id=0, unk_id=1, bos_id=2, eos_id=3, hard_vocab_limit=False
    )

if __name__ == "__main__":
    main()
