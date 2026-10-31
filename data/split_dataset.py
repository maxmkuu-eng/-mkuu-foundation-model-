"""Create deterministic train/validation/test splits without document leakage.

Input JSONL records require text, language, license, source and document_id.
All records from the same document_id are assigned to the same split. Exact
duplicate text is rejected rather than silently leaking between splits.
"""
import argparse
import hashlib
import json
from collections import Counter, defaultdict
from pathlib import Path

REQUIRED = ("text", "language", "license", "source", "document_id")
SPLITS = ("train", "validation", "test")


def _bucket(document_id):
    value = int(hashlib.sha256(document_id.encode("utf-8")).hexdigest()[:8], 16)
    fraction = value / 0xFFFFFFFF
    if fraction < 0.80:
        return "train"
    if fraction < 0.90:
        return "validation"
    return "test"


def split_records(input_path, output_dir):
    groups = defaultdict(list)
    seen_text = set()
    with open(input_path, encoding="utf-8") as stream:
        for line_no, line in enumerate(stream, 1):
            if not line.strip():
                continue
            row = json.loads(line)
            missing = [key for key in REQUIRED if not row.get(key)]
            if missing:
                raise ValueError(f"Line {line_no}: missing required fields {missing}")
            if not isinstance(row["text"], str) or len(row["text"].strip()) < 2:
                raise ValueError(f"Line {line_no}: text must contain at least 2 characters")
            normalized = " ".join(row["text"].split())
            digest = hashlib.sha256(normalized.casefold().encode("utf-8")).hexdigest()
            if digest in seen_text:
                raise ValueError(f"Line {line_no}: duplicate text detected; deduplicate before splitting")
            seen_text.add(digest)
            groups[str(row["document_id"])].append({**row, "text": normalized})
    if len(groups) < 3:
        raise ValueError("At least 3 distinct document_id groups are required for leakage-safe splits")

    assigned = {key: _bucket(key) for key in groups}
    # Avoid silently producing an empty held-out split for small corpora.
    missing_splits = [name for name in SPLITS if name not in assigned.values()]
    if missing_splits:
        # Move one group at a time from the currently largest split, never
        # emptying an existing split while reserving a held-out partition.
        for name in missing_splits:
            counts = Counter(assigned.values())
            donors = [split for split, count in counts.items() if count > 1]
            if not donors:
                raise ValueError("Cannot create non-empty train/validation/test splits from these groups")
            donor = max(donors, key=lambda split: counts[split])
            candidates = [key for key, split in assigned.items() if split == donor]
            chosen = min(candidates, key=lambda key: hashlib.sha256(key.encode("utf-8")).hexdigest())
            assigned[chosen] = name

    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    counts = Counter()
    handles = {name: (output / f"{name}.jsonl").open("w", encoding="utf-8") for name in SPLITS}
    try:
        for document_id, rows in groups.items():
            split = assigned[document_id]
            for row in rows:
                row["split"] = split
                handles[split].write(json.dumps(row, ensure_ascii=False) + "\n")
                counts[split] += 1
    finally:
        for handle in handles.values():
            handle.close()
    return dict(counts)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True)
    parser.add_argument("--output-dir", required=True)
    args = parser.parse_args()
    counts = split_records(args.input, args.output_dir)
    print("Split records: " + ", ".join(f"{key}={counts.get(key, 0)}" for key in SPLITS))


if __name__ == "__main__":
    main()
