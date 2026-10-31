"""End-to-end CPU smoke test for tokenizer, pretraining, SFT and local inference.

All text is tiny, project-authored synthetic fixture data. Behaviour seed
conversations are used ONLY for SFT, never as base-language pretraining text.
This test verifies pipeline execution, not model quality.
"""
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

import sentencepiece as spm
import yaml

ROOT = Path(__file__).resolve().parents[1]


def run(*args):
    env = os.environ.copy()
    existing = env.get("PYTHONPATH")
    env["PYTHONPATH"] = str(ROOT) if not existing else str(ROOT) + os.pathsep + existing
    subprocess.run([sys.executable, *map(str, args)], cwd=ROOT, env=env, check=True)


def write_jsonl(path, rows):
    with path.open("w", encoding="utf-8") as stream:
        for row in rows:
            stream.write(json.dumps(row, ensure_ascii=False) + chr(10))


def main():
    with tempfile.TemporaryDirectory(prefix="mkuu-smoke-") as tmp:
        work = Path(tmp)
        seed = ROOT / "data/behaviour_seed.jsonl"
        # Distinct, generic fixture text exercises next-token pretraining without
        # treating conversational behaviour examples as base-language corpus.
        base_data = work / "base_train.jsonl"
        provenance = {"license": "CC0-1.0-original-project-example",
                      "source": "original_project_authored_smoke_fixture"}
        base_rows = [
            {"text": text, **provenance} for text in [
                "Maji hutiririka kutoka sehemu za juu kwenda sehemu za chini.",
                "The sun rises in the east and sets in the west.",
                "Kila siku watu hujifunza mambo mapya kwa kusoma na kuuliza maswali.",
                "A small experiment checks whether a program can complete its steps.",
            ]
        ]
        write_jsonl(base_data, base_rows)
        corpus = work / "tokenizer.txt"
        run("data/build_tokenizer_corpus.py", "--input", base_data, seed, "--output", corpus)
        prefix = work / "mkuu-smoke"
        spm.SentencePieceTrainer.train(
            input=str(corpus), model_prefix=str(prefix), vocab_size=256,
            model_type="unigram", character_coverage=0.9995,
            pad_id=0, unk_id=1, bos_id=2, eos_id=3, hard_vocab_limit=False,
            user_defined_symbols=["<|system|>", "<|user|>", "<|assistant|>"],
        )
        tokenizer_path = Path(str(prefix) + ".model")
        tokenizer = spm.SentencePieceProcessor(model_file=str(tokenizer_path))
        vocab_size = tokenizer.get_piece_size()
        if vocab_size < 16:
            raise RuntimeError(f"Tokenizer vocabulary unexpectedly small: {vocab_size}")

        config = {
            "model": {"vocab_size": vocab_size, "d_model": 32, "n_layers": 1,
                      "n_heads": 4, "ffn_hidden_size": 64, "max_seq_len": 32,
                      "dropout": 0.0, "tie_embeddings": False, "rope_theta": 10000.0},
            "training": {"seed": 42, "sequence_length": 32, "batch_size": 1,
                         "gradient_accumulation_steps": 1, "learning_rate": 0.0002,
                         "min_learning_rate": 0.00002, "weight_decay": 0.01,
                         "warmup_steps": 1, "max_steps": 2, "log_every": 1,
                         "save_every": 2, "max_grad_norm": 1.0, "num_workers": 0},
        }
        config_path = work / "config.yaml"
        config_path.write_text(yaml.safe_dump(config), encoding="utf-8")
        pretrain_out = work / "pretrain"
        run("training/pretrain.py", "--config", config_path, "--data", base_data,
            "--tokenizer", tokenizer_path, "--output", pretrain_out)
        base_checkpoint = pretrain_out / "last.pt"
        if not base_checkpoint.is_file() or base_checkpoint.stat().st_size == 0:
            raise RuntimeError("Pretraining did not produce a non-empty checkpoint")

        sft_out = work / "sft"
        run("training/sft.py", "--config", config_path, "--data", seed,
            "--tokenizer", tokenizer_path, "--init-checkpoint", base_checkpoint,
            "--output", sft_out, "--max-steps", 2)
        sft_checkpoint = sft_out / "last.pt"
        if not sft_checkpoint.is_file() or sft_checkpoint.stat().st_size == 0:
            raise RuntimeError("SFT did not produce a non-empty checkpoint")

        # Exercise the real command-line generation path against the SFT result.
        run("scripts/generate.py", "--checkpoint", sft_checkpoint,
            "--tokenizer", tokenizer_path, "--prompt", "<|user|> Habari <|assistant|>",
            "--max-new-tokens", 4, "--temperature", 0)
        print(f"SMOKE TEST PASSED: vocab={vocab_size}; pretrain and SFT checkpoints created; inference executed.")
        print("Tiny synthetic fixtures only; this is not a quality or production test.")


if __name__ == "__main__":
    main()
