import argparse
import hashlib
import json
from pathlib import Path

REQUIRED = ("text", "language", "license", "source")

def prepare(input_path, output_path):
    seen, written = set(), 0
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    with open(input_path, encoding="utf-8") as src, open(output_path, "w", encoding="utf-8") as dst:
        for line_no, line in enumerate(src, 1):
            if not line.strip():
                continue
            row = json.loads(line)
            missing = [k for k in REQUIRED if not row.get(k)]
            if missing:
                raise ValueError(f"Line {line_no} missing fields: {missing}")
            text = " ".join(row["text"].split())
            if len(text) < 20:
                continue
            digest = hashlib.sha256(text.encode("utf-8")).hexdigest()
            if digest in seen:
                continue
            seen.add(digest)
            dst.write(json.dumps({**row, "text": text}, ensure_ascii=False) + "\n")
            written += 1
    return written

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--input", required=True)
    p.add_argument("--output", required=True)
    a = p.parse_args()
    print(f"Prepared {prepare(a.input, a.output)} unique records")

if __name__ == "__main__":
    main()
