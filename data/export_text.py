import argparse
import json
from pathlib import Path

def export_text(input_path, output_path):
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    count = 0
    with open(input_path, encoding="utf-8") as src, open(output_path, "w", encoding="utf-8") as dst:
        for line_no, line in enumerate(src, 1):
            if not line.strip():
                continue
            row = json.loads(line)
            text = row.get("text", "").strip()
            if not text:
                continue
            dst.write(text.replace("\n", " ") + "\n")
            count += 1
    return count

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--input", required=True, help="Validated JSONL dataset")
    p.add_argument("--output", required=True, help="Plain UTF-8 text corpus")
    a = p.parse_args()
    print(f"Exported {export_text(a.input, a.output)} documents")

if __name__ == "__main__":
    main()
