#!/usr/bin/env python3
"""End-to-end, resumable MKUU 300M T4 pilot for Google Colab.

The script downloads and verifies the exact approved project snapshot, cleans and
splits it without retaining the entire split corpus in RAM, trains a 48k
SentencePiece tokenizer, tokenizes into compact uint16 files, and runs FP16
pretraining with resumable checkpoints. It never uploads raw data to GitHub.
"""
import argparse
import hashlib
import json
import math
import os
import random
import shutil
import subprocess
import sys
import time
from pathlib import Path

import numpy as np
import sentencepiece as spm
import torch
import yaml
from torch.utils.data import Dataset, DataLoader

ROOT = Path(__file__).resolve().parents[1]
SOURCE_REPO = "ngusadeep/Swahili-Corpus-Dataset"
SOURCE_REV = "edc06d0eac67b8dcbedc476f93875dd1fb6349b1"
SOURCE_FILE = "Swahili_Corpus_combined.txt"
SOURCE_SHA256 = "057bacef92295b5ece75347861e9a6feff658af0631bea948b2b448562d229cd"
SOURCE_URL = "https://huggingface.co/datasets/ngusadeep/Swahili-Corpus-Dataset"
LICENSE_ID = "CC-BY-4.0"


def run(*cmd):
    print("+", " ".join(map(str, cmd)), flush=True)
    subprocess.run([str(x) for x in cmd], cwd=ROOT, check=True)


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def download_source(path):
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists() and sha256(path) == SOURCE_SHA256:
        print(f"Verified existing source: {path}", flush=True)
        return
    import requests
    url = f"https://huggingface.co/datasets/{SOURCE_REPO}/resolve/{SOURCE_REV}/{SOURCE_FILE}"
    temp = path.with_suffix(path.suffix + ".download")
    digest = hashlib.sha256()
    with requests.get(url, stream=True, timeout=(30, 180)) as response:
        response.raise_for_status()
        with temp.open("wb") as dst:
            for chunk in response.iter_content(1024 * 1024):
                if chunk:
                    dst.write(chunk)
                    digest.update(chunk)
    actual = digest.hexdigest()
    if actual != SOURCE_SHA256:
        temp.unlink(missing_ok=True)
        raise RuntimeError(f"Source SHA256 mismatch: {actual}")
    temp.replace(path)
    print(f"Source verified: {path} ({path.stat().st_size:,} bytes)", flush=True)


def bucket(document_id):
    n = int(hashlib.sha256(document_id.encode("utf-8")).hexdigest()[:8], 16)
    fraction = n / 0xFFFFFFFF
    return "train" if fraction < .80 else ("validation" if fraction < .90 else "test")


def stream_split(candidate, out_dir):
    """Streaming split; cleaner already assigns one stable unique document_id per source line."""
    out_dir.mkdir(parents=True, exist_ok=True)
    paths = {name: out_dir / f"{name}.jsonl" for name in ("train", "validation", "test")}
    counts = {name: 0 for name in paths}
    seen_docs = set()
    with candidate.open(encoding="utf-8") as src, \
         paths["train"].open("w", encoding="utf-8") as train, \
         paths["validation"].open("w", encoding="utf-8") as val, \
         paths["test"].open("w", encoding="utf-8") as test:
        writers = {"train": train, "validation": val, "test": test}
        for line_no, line in enumerate(src, 1):
            if not line.strip():
                continue
            row = json.loads(line)
            if row.get("license_status") != "approved" or not row.get("license") or not row.get("source"):
                raise ValueError(f"Candidate line {line_no} lacks approved provenance")
            doc = row.get("document_id")
            if not doc:
                raise ValueError(f"Candidate line {line_no} has no document_id")
            if doc in seen_docs:
                raise ValueError(f"Repeated document_id at candidate line {line_no}: {doc}")
            seen_docs.add(doc)
            name = bucket(str(doc))
            row["split"] = name
            writers[name].write(json.dumps(row, ensure_ascii=False) + "\n")
            counts[name] += 1
    if any(counts[name] == 0 for name in counts):
        raise RuntimeError(f"One or more splits are empty: {counts}")
    print("Split counts:", json.dumps(counts), flush=True)
    return paths, counts


def build_tokenizer_text(train_jsonl, output):
    output.parent.mkdir(parents=True, exist_ok=True)
    count = 0
    with train_jsonl.open(encoding="utf-8") as src, output.open("w", encoding="utf-8") as dst:
        for line_no, line in enumerate(src, 1):
            if not line.strip():
                continue
            row = json.loads(line)
            if row.get("split") != "train" or row.get("license_status") != "approved":
                raise ValueError(f"Tokenizer input line {line_no} is not approved train data")
            text = " ".join(row["text"].split())
            if text:
                dst.write(text + "\n")
                count += 1
    if not count:
        raise RuntimeError("No text available for tokenizer training")
    print(f"Tokenizer training lines: {count:,}", flush=True)


class TokenMemmapDataset(Dataset):
    """Tokenize JSONL once into uint16 mmap; keep only chunk offsets in RAM."""
    def __init__(self, jsonl_path, tokenizer, seq_len, cache_prefix, required_split):
        self.bin_path = Path(str(cache_prefix) + ".u16")
        self.idx_path = Path(str(cache_prefix) + ".idx.json")
        self.seq_len = seq_len
        if self.bin_path.exists() and self.idx_path.exists():
            meta = json.loads(self.idx_path.read_text(encoding="utf-8"))
            if meta.get("source_size") == Path(jsonl_path).stat().st_size and meta.get("seq_len") == seq_len:
                self.offsets = meta["offsets"]
                self.tokens = np.memmap(self.bin_path, dtype=np.uint16, mode="r")
                print(f"Using token cache {self.bin_path}: {len(self.offsets):,} sequences", flush=True)
                return
        self.offsets = []
        self.bin_path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self.bin_path.with_suffix(".u16.tmp")
        with Path(jsonl_path).open(encoding="utf-8") as src, tmp.open("wb") as dst:
            for line_no, line in enumerate(src, 1):
                if not line.strip():
                    continue
                row = json.loads(line)
                if row.get("split") != required_split or row.get("license_status") != "approved":
                    raise ValueError(f"{jsonl_path}:{line_no}: unexpected split or unapproved row")
                if not row.get("license") or not row.get("source") or not row.get("document_id"):
                    raise ValueError(f"{jsonl_path}:{line_no}: missing provenance")
                ids = tokenizer.encode(row["text"], out_type=int)
                for start in range(0, max(0, len(ids) - 1), seq_len):
                    chunk = ids[start:start + seq_len + 1]
                    if len(chunk) > 1:
                        if max(chunk) > 65535:
                            raise ValueError("Tokenizer IDs exceed uint16 cache capacity")
                        byte_offset = dst.tell() // 2
                        np.asarray(chunk, dtype=np.uint16).tofile(dst)
                        self.offsets.append([byte_offset, len(chunk)])
        tmp.replace(self.bin_path)
        self.idx_path.write_text(json.dumps({
            "source_size": Path(jsonl_path).stat().st_size,
            "seq_len": seq_len, "offsets": self.offsets,
        }), encoding="utf-8")
        if not self.offsets:
            raise RuntimeError(f"No token sequences generated from {jsonl_path}")
        self.tokens = np.memmap(self.bin_path, dtype=np.uint16, mode="r")
        print(f"Created token cache {self.bin_path}: {len(self.offsets):,} sequences", flush=True)

    def __len__(self):
        return len(self.offsets)

    def __getitem__(self, index):
        offset, length = self.offsets[index]
        ids = self.tokens[offset:offset + length].astype(np.int64).tolist()
        x, y = ids[:-1], ids
        pad = self.seq_len - len(x)
        if pad > 0:
            x += [0] * pad
            y += [-100] * pad
        return torch.tensor(x[:self.seq_len], dtype=torch.long), torch.tensor(y[:self.seq_len], dtype=torch.long)


def save_checkpoint(path, model, optimizer, scaler, step, raw_cfg, best_loss=None):
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    torch.save({
        "model": model.state_dict(),
        "optimizer": optimizer.state_dict(),
        "scaler": scaler.state_dict(),
        "step": step,
        "config": raw_cfg,
        "python_rng": random.getstate(),
        "numpy_rng": np.random.get_state(),
        "torch_rng": torch.get_rng_state(),
        "cuda_rng": torch.cuda.get_rng_state_all(),
        "best_loss": best_loss,
    }, tmp)
    tmp.replace(path)
    print(f"Checkpoint saved: {path} (step {step})", flush=True)


def train(train_ds, raw_cfg, tokenizer_size, checkpoint_dir, steps, save_every, resume):
    if not torch.cuda.is_available():
        raise RuntimeError("CUDA GPU is required; refusing to fall back silently to CPU")
    device = torch.device("cuda")
    torch.backends.cuda.matmul.allow_tf32 = True
    tc = raw_cfg["training"]
    cfg = raw_cfg
    model_cfg = __import__("model").ModelConfig.from_dict(cfg)
    if tokenizer_size != model_cfg.vocab_size:
        raise ValueError(f"Tokenizer vocab {tokenizer_size} != model vocab {model_cfg.vocab_size}")
    model = __import__("model").MKUUTransformer(model_cfg).to(device)
    optimizer = torch.optim.AdamW(model.parameters(), lr=float(tc.get("learning_rate", 1e-4)),
                                  weight_decay=float(tc.get("weight_decay", .1)))
    scaler = torch.amp.GradScaler("cuda")
    step = 0
    best_loss = None
    if resume and (checkpoint_dir / "last.pt").exists():
        state = torch.load(checkpoint_dir / "last.pt", map_location=device, weights_only=False)
        model.load_state_dict(state["model"])
        optimizer.load_state_dict(state["optimizer"])
        scaler.load_state_dict(state.get("scaler", {}))
        step = int(state.get("step", 0))
        best_loss = state.get("best_loss")
        if state.get("python_rng") is not None:
            random.setstate(state["python_rng"])
        if state.get("numpy_rng") is not None:
            np.random.set_state(state["numpy_rng"])
        if state.get("torch_rng") is not None:
            torch.set_rng_state(state["torch_rng"])
        if state.get("cuda_rng") is not None:
            torch.cuda.set_rng_state_all(state["cuda_rng"])
        print(f"Resumed from step {step}", flush=True)

    batch_size = int(tc.get("batch_size", 1))
    accum = max(1, int(tc.get("gradient_accumulation_steps", 8)))
    loader = DataLoader(train_ds, batch_size=batch_size, shuffle=True, num_workers=0,
                        pin_memory=True, drop_last=False)
    base_lr = float(tc.get("learning_rate", 1e-4))
    min_lr = float(tc.get("min_learning_rate", 1e-5))
    warmup = max(1, int(tc.get("warmup_steps", 100)))
    max_steps = steps
    log_every = max(1, int(tc.get("log_every", 10)))
    optimizer.zero_grad(set_to_none=True)
    model.train()
    micro = 0
    loss_sum = 0.0
    while step < max_steps:
        made_progress = False
        for x, y in loader:
            made_progress = True
            progress = min(step / max(1, max_steps), 1.0)
            lr = base_lr * (step + 1) / warmup if step < warmup else (
                min_lr + .5 * (base_lr - min_lr) * (1 + math.cos(math.pi * progress)))
            for group in optimizer.param_groups:
                group["lr"] = lr
            x, y = x.to(device, non_blocking=True), y.to(device, non_blocking=True)
            with torch.autocast(device_type="cuda", dtype=torch.float16):
                loss = model(x, labels=y)["loss"]
            scaler.scale(loss / accum).backward()
            loss_sum += float(loss.detach())
            micro += 1
            if micro % accum == 0:
                scaler.unscale_(optimizer)
                torch.nn.utils.clip_grad_norm_(model.parameters(), float(tc.get("max_grad_norm", 1.0)))
                scaler.step(optimizer)
                scaler.update()
                optimizer.zero_grad(set_to_none=True)
                step += 1
                if step % log_every == 0 or step == 1:
                    print(f"step={step}/{max_steps} loss={loss_sum/accum:.4f} lr={lr:.3e} "
                          f"gpu_peak_gb={torch.cuda.max_memory_allocated()/1024**3:.2f}", flush=True)
                    loss_sum = 0.0
                if step % save_every == 0:
                    save_checkpoint(checkpoint_dir / f"step-{step}.pt", model, optimizer,
                                    scaler, step, cfg, best_loss)
                    save_checkpoint(checkpoint_dir / "last.pt", model, optimizer,
                                    scaler, step, cfg, best_loss)
                if step >= max_steps:
                    break
        if not made_progress:
            raise RuntimeError("Training DataLoader produced no batches")
    if micro % accum:
        scaler.unscale_(optimizer)
        correction = accum / (micro % accum)
        for param in model.parameters():
            if param.grad is not None:
                param.grad.mul_(correction)
        torch.nn.utils.clip_grad_norm_(model.parameters(), float(tc.get("max_grad_norm", 1.0)))
        scaler.step(optimizer)
        scaler.update()
        optimizer.zero_grad(set_to_none=True)
    save_checkpoint(checkpoint_dir / "last.pt", model, optimizer, scaler, step, cfg, best_loss)
    return model


def evaluate(model, dataset, split, max_sequences=256):
    device = next(model.parameters()).device
    model.eval()
    total_loss, total_tokens, total_sequences = 0.0, 0, 0
    limit = min(len(dataset), max_sequences)
    with torch.inference_mode():
        for start in range(0, limit, 1):
            x, y = dataset[start]
            x = x.unsqueeze(0).to(device)
            y = y.unsqueeze(0).to(device)
            with torch.autocast(device_type="cuda", dtype=torch.float16):
                logits = model(x)["logits"][:, :-1, :].float()
            labels = y[:, 1:]
            loss_sum = torch.nn.functional.cross_entropy(
                logits.reshape(-1, logits.size(-1)), labels.reshape(-1),
                ignore_index=-100, reduction="sum")
            count = int((labels != -100).sum())
            total_loss += float(loss_sum)
            total_tokens += count
            total_sequences += 1
    if not total_tokens:
        raise RuntimeError(f"{split} split has no evaluation tokens")
    mean_loss = total_loss / total_tokens
    result = {
        "split": split, "sequences_evaluated": total_sequences,
        "tokens_evaluated": total_tokens, "cross_entropy": mean_loss,
        "perplexity": math.exp(min(mean_loss, 80)),
        "evaluation_scope": f"first {limit} deterministic sequences",
    }
    print(json.dumps(result, indent=2), flush=True)
    return result


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--work-dir", default="/content/mkuu-work")
    p.add_argument("--drive-dir", default="/content/drive/MyDrive/MKUU-Foundation-Model")
    p.add_argument("--steps", type=int, default=1000)
    p.add_argument("--save-every", type=int, default=100)
    p.add_argument("--sequence-length", type=int, default=512)
    p.add_argument("--eval-sequences", type=int, default=256)
    p.add_argument("--no-resume", action="store_true")
    p.add_argument("--mount-drive", action="store_true")
    args = p.parse_args()
    if args.steps < 1 or args.save_every < 1 or args.sequence_length < 8:
        p.error("steps/save-every must be positive and sequence-length >= 8")
    if args.mount_drive:
        try:
            from google.colab import drive
            drive.mount("/content/drive")
        except ImportError as exc:
            raise RuntimeError("--mount-drive is only available inside Google Colab") from exc
    drive_dir = Path(args.drive_dir)
    drive_dir.mkdir(parents=True, exist_ok=True)
    work = Path(args.work_dir)
    work.mkdir(parents=True, exist_ok=True)
    raw_source = work / SOURCE_FILE
    download_source(raw_source)

    from data.clean_swahili_corpus import clean_corpus
    candidate = work / "swahili_candidate.jsonl"
    held = work / "held_for_review.jsonl"
    if not candidate.exists() or not held.exists():
        stats = clean_corpus(
            raw_source, candidate, held, source="ngusadeep-swahili-corpus",
            version=SOURCE_REV, source_url=SOURCE_URL, license_id=LICENSE_ID,
            max_chars=5000)
        print("Cleaning report:", json.dumps(stats, indent=2), flush=True)
    else:
        print("Using existing cleaned corpus candidates.", flush=True)

    split_dir = work / "splits"
    split_files = {name: split_dir / f"{name}.jsonl" for name in ("train", "validation", "test")}
    if not all(path.exists() for path in split_files.values()):
        split_files, counts = stream_split(candidate, split_dir)
    else:
        print("Using existing split files.", flush=True)

    tokenizer_text = work / "tokenizer_train.txt"
    tokenizer_prefix = work / "mkuu_swahili_spm"
    if not Path(str(tokenizer_prefix) + ".model").exists():
        build_tokenizer_text(split_files["train"], tokenizer_text)
        run(sys.executable, "tokenizer/train_tokenizer.py", "--input", tokenizer_text,
            "--model-prefix", tokenizer_prefix, "--vocab-size", "48000")
    tokenizer_path = Path(str(tokenizer_prefix) + ".model")
    tokenizer = spm.SentencePieceProcessor(model_file=str(tokenizer_path))
    vocab_size = tokenizer.get_piece_size()
    print(f"Tokenizer vocabulary: {vocab_size}", flush=True)

    model_raw = yaml.safe_load((ROOT / "configs/model_300m.yaml").read_text(encoding="utf-8"))
    model_raw["model"]["vocab_size"] = vocab_size
    train_raw = yaml.safe_load((ROOT / "configs/training_pilot.yaml").read_text(encoding="utf-8"))
    model_raw["training"] = train_raw["training"]
    model_raw["training"]["sequence_length"] = args.sequence_length
    model_raw["training"]["max_steps"] = args.steps
    model_raw["training"]["batch_size"] = 1
    model_raw["training"]["gradient_accumulation_steps"] = 8
    model_raw["training"]["num_workers"] = 0
    effective = work / "effective_t4_config.yaml"
    effective.write_text(yaml.safe_dump(model_raw, sort_keys=False), encoding="utf-8")

    cache = work / "token_cache"
    train_ds = TokenMemmapDataset(split_files["train"], tokenizer, args.sequence_length,
                                  cache / "train", "train")
    val_ds = TokenMemmapDataset(split_files["validation"], tokenizer, args.sequence_length,
                                cache / "validation", "validation")
    test_ds = TokenMemmapDataset(split_files["test"], tokenizer, args.sequence_length,
                                 cache / "test", "test")

    ckpt_dir = drive_dir / "checkpoints"
    model = train(train_ds, model_raw, vocab_size, ckpt_dir, args.steps,
                  args.save_every, resume=not args.no_resume)
    val_result = evaluate(model, val_ds, "validation", args.eval_sequences)
    test_result = evaluate(model, test_ds, "test", args.eval_sequences)
    report = {
        "source_repo": SOURCE_REPO, "source_revision": SOURCE_REV,
        "source_sha256": SOURCE_SHA256, "license": LICENSE_ID,
        "license_status": "approved_by_project_owner",
        "model_parameters": model.parameter_count(), "tokenizer_vocab_size": vocab_size,
        "gpu": torch.cuda.get_device_name(0), "gpu_vram_gb": round(
            torch.cuda.get_device_properties(0).total_memory / 1024**3, 2),
        "steps_target": args.steps, "sequence_length": args.sequence_length,
        "validation": val_result, "test": test_result,
        "checkpoint": str(ckpt_dir / "last.pt"),
        "finished_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }
    (drive_dir / "pilot_report.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    shutil.copy2(tokenizer_path, drive_dir / "mkuu_swahili_spm.model")
    print("\nPILOT COMPLETED. Report:", drive_dir / "pilot_report.json", flush=True)
    print(json.dumps(report, indent=2), flush=True)


if __name__ == "__main__":
    main()
