"""Generate text from a trained MKUU checkpoint (no hosted model/API required)."""
import argparse
from pathlib import Path

import sentencepiece as spm
import torch
import yaml

from model import ModelConfig, MKUUTransformer


def load_model(checkpoint_path, config_path, device):
    state = torch.load(checkpoint_path, map_location=device, weights_only=False)
    raw = state.get("config") or state.get("model_config")
    if config_path:
        with open(config_path, encoding="utf-8") as stream:
            raw = yaml.safe_load(stream)
    if not raw:
        raise ValueError("Checkpoint has no model config; pass --config")
    config = ModelConfig.from_dict(raw)
    model = MKUUTransformer(config).to(device)
    model.load_state_dict(state.get("model", state), strict=True)
    model.eval()
    return model


@torch.inference_mode()
def generate(model, tokenizer, prompt, max_new_tokens=128, temperature=0.8,
             top_k=40, top_p=0.9, repetition_penalty=1.08, device="cpu"):
    if temperature < 0:
        raise ValueError("temperature must be >= 0")
    if not 0 < top_p <= 1:
        raise ValueError("top_p must be in (0, 1]")
    ids = tokenizer.encode(prompt, out_type=int)
    if not ids:
        ids = [tokenizer.bos_id() if tokenizer.bos_id() >= 0 else tokenizer.unk_id()]
    result = list(ids)
    eos = tokenizer.eos_id()
    for _ in range(max_new_tokens):
        context = result[-model.config.max_seq_len:]
        input_ids = torch.tensor([context], dtype=torch.long, device=device)
        logits = model(input_ids)["logits"][0, -1].float()
        if repetition_penalty != 1.0:
            for token_id in set(result):
                logits[token_id] = (logits[token_id] * repetition_penalty
                                    if logits[token_id] < 0 else logits[token_id] / repetition_penalty)
        if temperature == 0:
            next_id = int(torch.argmax(logits).item())
        else:
            logits /= temperature
            if top_k > 0 and top_k < logits.numel():
                threshold = torch.topk(logits, top_k).values[-1]
                logits[logits < threshold] = -torch.inf
            if top_p < 1.0:
                sorted_logits, sorted_indices = torch.sort(logits, descending=True)
                cumulative = torch.softmax(sorted_logits, dim=-1).cumsum(dim=-1)
                remove = cumulative - torch.softmax(sorted_logits, dim=-1) >= top_p
                sorted_logits[remove] = -torch.inf
                logits.fill_(-torch.inf)
                logits.scatter_(0, sorted_indices, sorted_logits)
            probs = torch.softmax(logits, dim=-1)
            next_id = int(torch.multinomial(probs, num_samples=1).item())
        result.append(next_id)
        if eos >= 0 and next_id == eos:
            break
    return tokenizer.decode(result[len(ids):])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--checkpoint", required=True)
    parser.add_argument("--tokenizer", required=True)
    parser.add_argument("--config", help="Optional YAML override; normally read from checkpoint")
    parser.add_argument("--prompt", required=True)
    parser.add_argument("--max-new-tokens", type=int, default=128)
    parser.add_argument("--temperature", type=float, default=0.8)
    parser.add_argument("--top-k", type=int, default=40)
    parser.add_argument("--top-p", type=float, default=0.9)
    parser.add_argument("--repetition-penalty", type=float, default=1.08)
    args = parser.parse_args()
    if args.max_new_tokens < 1:
        parser.error("--max-new-tokens must be positive")
    device = "cuda" if torch.cuda.is_available() else "cpu"
    tokenizer = spm.SentencePieceProcessor(model_file=args.tokenizer)
    model = load_model(args.checkpoint, args.config, device)
    print(generate(model, tokenizer, args.prompt, args.max_new_tokens,
                   args.temperature, args.top_k, args.top_p,
                   args.repetition_penalty, device))


if __name__ == "__main__":
    main()
