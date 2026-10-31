"""Evaluate a trained MKUU checkpoint on a held-out JSONL split.

Input records must have text, license, source and split=validation (or test).
Reports token-weighted loss and perplexity; never use training data as evaluation.
"""
import argparse
import json
import math
import sys
from pathlib import Path

# Make the repository root importable when this file is run by path in CI.
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import sentencepiece as spm
import torch
import yaml

from model import ModelConfig, MKUUTransformer


def load_records(path, tokenizer, seq_len, required_split):
    rows = []
    with open(path, encoding="utf-8") as stream:
        for line_no, line in enumerate(stream, 1):
            if not line.strip():
                continue
            row = json.loads(line)
            if row.get("split") != required_split:
                raise ValueError(f"Line {line_no}: expected split={required_split!r}")
            if not row.get("license") or not row.get("source"):
                raise ValueError(f"Line {line_no}: missing license/source provenance")
            text = row.get("text")
            if not isinstance(text, str) or not text.strip():
                raise ValueError(f"Line {line_no}: text must be non-empty")
            ids = tokenizer.encode(text, out_type=int)
            for start in range(0, max(0, len(ids) - 1), seq_len):
                chunk = ids[start:start + seq_len + 1]
                if len(chunk) > 1:
                    x, y = chunk[:-1], chunk
                    x += [0] * (seq_len - len(x))
                    y += [-100] * (seq_len - len(y))
                    rows.append((x[:seq_len], y[:seq_len]))
    if not rows:
        raise ValueError("No evaluable sequences in the requested held-out split")
    return rows


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--checkpoint", required=True)
    parser.add_argument("--tokenizer", required=True)
    parser.add_argument("--data", required=True)
    parser.add_argument("--config")
    parser.add_argument("--split", choices=("validation", "test"), default="test")
    parser.add_argument("--batch-size", type=int, default=2)
    args = parser.parse_args()
    if args.batch_size < 1:
        parser.error("--batch-size must be positive")

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    state = torch.load(args.checkpoint, map_location=device, weights_only=False)
    raw = state.get("config") or state.get("model_config")
    if args.config:
        with open(args.config, encoding="utf-8") as stream:
            raw = yaml.safe_load(stream)
    if not raw:
        parser.error("Checkpoint has no model config; pass --config")
    cfg = ModelConfig.from_dict(raw)
    tokenizer = spm.SentencePieceProcessor(model_file=args.tokenizer)
    if tokenizer.get_piece_size() != cfg.vocab_size:
        parser.error("Tokenizer vocabulary does not match checkpoint model config")
    rows = load_records(args.data, tokenizer, cfg.max_seq_len, args.split)
    model = MKUUTransformer(cfg).to(device)
    model.load_state_dict(state.get("model", state), strict=True)
    model.eval()

    total_nll, total_tokens = 0.0, 0
    with torch.inference_mode():
        for start in range(0, len(rows), args.batch_size):
            batch = rows[start:start + args.batch_size]
            x = torch.tensor([r[0] for r in batch], dtype=torch.long, device=device)
            y = torch.tensor([r[1] for r in batch], dtype=torch.long, device=device)
            logits = model(x)["logits"][:, :-1, :].contiguous()
            labels = y[:, 1:].contiguous()
            nll = torch.nn.functional.cross_entropy(
                logits.view(-1, cfg.vocab_size), labels.view(-1),
                ignore_index=-100, reduction="sum")
            count = int((labels != -100).sum().item())
            total_nll += float(nll.item())
            total_tokens += count
    if not total_tokens:
        raise RuntimeError("Evaluation split contains no target tokens")
    loss = total_nll / total_tokens
    print(f"split={args.split} sequences={len(rows)} tokens={total_tokens}")
    print(f"cross_entropy={loss:.6f} perplexity={math.exp(min(loss, 80)):.6f}")


if __name__ == "__main__":
    main()
