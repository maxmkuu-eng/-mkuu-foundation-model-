"""Build a tokenizer text corpus from approved JSONL sources.

Accepts plain-text records (text) and conversation records (messages). Every record
must carry license and source provenance. Only records explicitly marked split=train
are admitted when a split field is present; records without split are treated as
training input and should be pre-reviewed by the dataset owner.
"""
import argparse
import json
from pathlib import Path


def extract_text(row, line_no):
    if not row.get("license") or not row.get("source"):
        raise ValueError(f"Line {line_no}: license and source provenance are required")
    if row.get("split", "train") != "train":
        return []
    chunks = []
    if isinstance(row.get("text"), str):
        chunks.append(row["text"])
    for message in row.get("messages", []):
        if message.get("role") in {"user", "assistant", "system"}:
            value = message.get("content")
            if isinstance(value, str) and value.strip():
                chunks.append(value.strip())
    return chunks


def build(inputs, output):
    Path(output).parent.mkdir(parents=True, exist_ok=True)
    count = 0
    with open(output, "w", encoding="utf-8") as dst:
        for path in inputs:
            with open(path, encoding="utf-8") as src:
                for line_no, line in enumerate(src, 1):
                    if not line.strip():
                        continue
                    row = json.loads(line)
                    for value in extract_text(row, line_no):
                        normalized = " ".join(value.split())
                        if normalized:
                            dst.write(normalized + "\n")
                            count += 1
    if not count:
        raise ValueError("No training text found. Add reviewed, licensed train-split JSONL.")
    return count


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", nargs="+", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    print(f"Wrote {build(args.input, args.output)} text lines to {args.output}")


if __name__ == "__main__":
    main()
