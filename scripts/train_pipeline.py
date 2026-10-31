"""Run the complete licensed-data MKUU training pipeline.

This orchestrator deliberately refuses to train on unreviewed or synthetic data.
The input corpus is JSONL with text/language/license/source/document_id.
Conversation SFT is optional and uses a separate role-labelled JSONL corpus.
"""
import argparse
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def run(*args):
    print("+", " ".join(map(str, args)), flush=True)
    subprocess.run([sys.executable, *map(str, args)], cwd=ROOT, check=True)


def inspect_corpus(path, conversation=False):
    count = 0
    languages = set()
    with open(path, encoding="utf-8") as stream:
        for line_no, line in enumerate(stream, 1):
            if not line.strip():
                continue
            row = json.loads(line)
            if not row.get("license") or not row.get("source"):
                raise ValueError(f"{path}:{line_no}: missing license/source")
            if conversation:
                messages = row.get("messages")
                if not isinstance(messages, list) or not any(
                    isinstance(m, dict) and m.get("role") == "assistant"
                    and isinstance(m.get("content"), str) and m["content"].strip()
                    for m in messages
                ):
                    raise ValueError(f"{path}:{line_no}: no assistant conversation target")
            else:
                text = row.get("text")
                if not isinstance(text, str) or len(text.strip()) < 2:
                    raise ValueError(f"{path}:{line_no}: invalid text")
                if not row.get("language") or not row.get("document_id"):
                    raise ValueError(f"{path}:{line_no}: language and document_id are required")
                languages.add(row["language"])
            count += 1
    if count == 0:
        raise ValueError(f"{path}: corpus is empty")
    print(f"Validated {count} records from {len(languages)} languages: {sorted(languages)}")
    return count


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--corpus", required=True, help="Reviewed, licensed pretraining JSONL")
    parser.add_argument("--sft-corpus", help="Optional separately licensed conversation JSONL")
    parser.add_argument("--vocab-size", type=int, default=48000)
    parser.add_argument("--pretrain-steps", type=int, default=1000)
    parser.add_argument("--sft-steps", type=int, default=100)
    parser.add_argument("--output", default="artifacts/run")
    args = parser.parse_args()
    if args.vocab_size < 100 or args.pretrain_steps < 1 or args.sft_steps < 1:
        parser.error("vocab-size must be >=100 and training steps must be positive")

    corpus = Path(args.corpus).resolve()
    if not corpus.is_file():
        parser.error(f"corpus does not exist: {corpus}")
    inspect_corpus(corpus)
    output = Path(args.output)
    if not output.is_absolute():
        output = ROOT / output
    output.mkdir(parents=True, exist_ok=True)

    splits = output / "splits"
    run("data/split_dataset.py", "--input", corpus, "--output-dir", splits)
    train_jsonl = splits / "train.jsonl"
    tokenizer_text = output / "tokenizer_train.txt"
    run("data/build_tokenizer_corpus.py", "--input", train_jsonl,
        "--output", tokenizer_text)
    tokenizer_prefix = output / "mkuu_spm"
    run("tokenizer/train_tokenizer.py", "--input", tokenizer_text,
        "--model-prefix", tokenizer_prefix, "--vocab-size", args.vocab_size)

    model_config = ROOT / "configs/model_300m.yaml"
    raw_config = json.loads(json.dumps(__import__("yaml").safe_load(model_config.read_text())))
    raw_config["model"]["vocab_size"] = __import__("sentencepiece").SentencePieceProcessor(
        model_file=str(tokenizer_prefix) + ".model").get_piece_size()
    raw_config["training"] = __import__("yaml").safe_load(
        (ROOT / "configs/training_pilot.yaml").read_text())["training"]
    raw_config["training"]["max_steps"] = args.pretrain_steps
    import yaml
    effective_config = output / "pretrain.yaml"
    effective_config.write_text(yaml.safe_dump(raw_config, sort_keys=False), encoding="utf-8")
    pretrain_dir = output / "pretrain"
    run("training/pretrain.py", "--config", effective_config, "--data", train_jsonl,
        "--tokenizer", str(tokenizer_prefix) + ".model", "--output", pretrain_dir)

    validation = splits / "validation.jsonl"
    test = splits / "test.jsonl"
    run("scripts/evaluate.py", "--checkpoint", pretrain_dir / "last.pt",
        "--tokenizer", str(tokenizer_prefix) + ".model", "--data", validation,
        "--split", "validation")
    run("scripts/evaluate.py", "--checkpoint", pretrain_dir / "last.pt",
        "--tokenizer", str(tokenizer_prefix) + ".model", "--data", test, "--split", "test")

    if args.sft_corpus:
        sft_path = Path(args.sft_corpus).resolve()
        if not sft_path.is_file():
            parser.error(f"SFT corpus does not exist: {sft_path}")
        inspect_corpus(sft_path, conversation=True)
        sft_config = ROOT / "configs/sft_300m.yaml"
        sft_raw = __import__("yaml").safe_load(sft_config.read_text())
        sft_raw["model"]["vocab_size"] = raw_config["model"]["vocab_size"]
        sft_raw["training"]["max_steps"] = args.sft_steps
        sft_effective = output / "sft.yaml"
        sft_effective.write_text(yaml.safe_dump(sft_raw, sort_keys=False), encoding="utf-8")
        sft_dir = output / "sft"
        run("training/sft.py", "--config", sft_effective, "--data", sft_path,
            "--tokenizer", str(tokenizer_prefix) + ".model",
            "--init-checkpoint", pretrain_dir / "last.pt", "--output", sft_dir)
    print(f"Pipeline completed. Artifacts: {output}", flush=True)


if __name__ == "__main__":
    main()
