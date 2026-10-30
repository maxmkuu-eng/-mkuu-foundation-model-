"""Supervised fine-tuning for role-labelled conversation JSONL.

Expected record:
{"id":"...","language":"sw-TZ","license":"...","source":"...","messages":[{"role":"user","content":"..."},{"role":"assistant","content":"..."}]}

Only assistant message tokens contribute to the loss. This is a small, transparent
reference pipeline; it is not a claim that a useful model can be trained on CPU.
"""
import argparse
import json
import random
from pathlib import Path

import sentencepiece as spm
import torch
import yaml
from torch.utils.data import Dataset, DataLoader

from model import ModelConfig, MKUUTransformer


def encode_conversation(messages, tokenizer, max_length):
    ids, labels = [], []
    for message in messages:
        role = message["role"]
        content = message["content"].strip()
        if role not in {"system", "user", "assistant"} or not content:
            continue
        prefix = f"<|{role}|>\n"
        prefix_ids = tokenizer.encode(prefix, out_type=int)
        content_ids = tokenizer.encode(content + "\n", out_type=int)
        ids.extend(prefix_ids)
        labels.extend([-100] * len(prefix_ids))
        ids.extend(content_ids)
        labels.extend(content_ids if role == "assistant" else [-100] * len(content_ids))
    eos = tokenizer.eos_id()
    if eos >= 0:
        ids.append(eos)
        labels.append(eos if messages and messages[-1]["role"] == "assistant" else -100)
    return ids[:max_length], labels[:max_length]


class ConversationDataset(Dataset):
    def __init__(self, path, tokenizer, max_length):
        self.rows = []
        with open(path, encoding="utf-8") as stream:
            for line_no, line in enumerate(stream, 1):
                if not line.strip():
                    continue
                row = json.loads(line)
                messages = row.get("messages")
                if not isinstance(messages, list) or not messages:
                    raise ValueError(f"Line {line_no}: messages must be a non-empty list")
                if not row.get("license") or not row.get("source"):
                    raise ValueError(f"Line {line_no}: license and source provenance are required")
                if not any(m.get("role") == "assistant" for m in messages):
                    continue
                ids, labels = encode_conversation(messages, tokenizer, max_length)
                if len(ids) >= 2 and any(x != -100 for x in labels[1:]):
                    self.rows.append((ids, labels))
        if not self.rows:
            raise ValueError("No usable assistant-target conversation examples found")

    def __len__(self):
        return len(self.rows)

    def __getitem__(self, index):
        ids, labels = self.rows[index]
        pad = self.max_length - len(ids)
        return (torch.tensor(ids + [0] * pad, dtype=torch.long),
                torch.tensor(labels + [-100] * pad, dtype=torch.long))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", required=True)
    parser.add_argument("--data", required=True)
    parser.add_argument("--tokenizer", required=True)
    parser.add_argument("--output", default="checkpoints/sft")
    parser.add_argument("--init-checkpoint", help="Optional pretrained/base checkpoint")
    parser.add_argument("--max-steps", type=int)
    args = parser.parse_args()

    with open(args.config, encoding="utf-8") as stream:
        raw = yaml.safe_load(stream)
    model_raw = raw["model"]
    train = raw.get("training", {})
    config = ModelConfig.from_dict({"model": model_raw})
    seed = int(train.get("seed", 42))
    random.seed(seed)
    torch.manual_seed(seed)

    tokenizer = spm.SentencePieceProcessor(model_file=args.tokenizer)
    max_length = min(int(train.get("sequence_length", 512)), config.max_seq_len)
    dataset = ConversationDataset(args.data, tokenizer, max_length)
    loader = DataLoader(dataset, batch_size=int(train.get("batch_size", 1)),
                        shuffle=True, num_workers=0)
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model = MKUUTransformer(config).to(device)

    if args.init_checkpoint:
        state = torch.load(args.init_checkpoint, map_location=device)
        model.load_state_dict(state.get("model", state), strict=True)

    optimizer = torch.optim.AdamW(
        model.parameters(), lr=float(train.get("learning_rate", 2e-5)),
        weight_decay=float(train.get("weight_decay", 0.01)))
    output = Path(args.output)
    output.mkdir(parents=True, exist_ok=True)
    steps = args.max_steps or int(train.get("max_steps", 100))
    save_every = max(1, int(train.get("save_every", 50)))
    model.train()
    step = 0
    while step < steps:
        for input_ids, labels in loader:
            input_ids, labels = input_ids.to(device), labels.to(device)
            optimizer.zero_grad(set_to_none=True)
            loss = model(input_ids, labels=labels)["loss"]
            if not torch.isfinite(loss):
                raise RuntimeError("Non-finite SFT loss; stopping without saving a misleading checkpoint")
            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
            optimizer.step()
            step += 1
            if step == 1 or step % 10 == 0:
                print(f"step={step} loss={loss.item():.4f} device={device}")
            if step % save_every == 0:
                torch.save({"model": model.state_dict(), "optimizer": optimizer.state_dict(),
                            "step": step, "model_config": model_raw, "stage": "sft"},
                           output / f"step-{step}.pt")
            if step >= steps:
                break
    torch.save({"model": model.state_dict(), "optimizer": optimizer.state_dict(),
                "step": step, "model_config": model_raw, "stage": "sft"},
               output / "last.pt")


if __name__ == "__main__":
    main()
