"""Import Common Voice TSV sentence text into provenance-labelled JSONL.

Only sentence text and non-identifying sentence metadata are retained. Speaker
IDs, demographics, audio paths and other speaker-level fields are discarded.
Raw Common Voice archives must remain outside this repository.
"""
import argparse
import csv
import hashlib
import json
from pathlib import Path

DEFAULT_SOURCE_URL = "https://commonvoice.mozilla.org/dav/datasets"
DEFAULT_LICENSE = "CC0-1.0"


def import_tsv(input_path, output_path, *, language, source, source_url,
               dataset_version, license_id=DEFAULT_LICENSE, retrieved_at=None,
               minimum_votes=0):
    if not all((language, source, source_url, dataset_version, license_id)):
        raise ValueError("language, source, source_url, dataset_version and license_id are required")
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    seen = set()
    written = rejected = 0
    with open(input_path, encoding="utf-8-sig", newline="") as source_file, \
         output.open("w", encoding="utf-8") as target:
        reader = csv.DictReader(source_file, delimiter="\t")
        if not reader.fieldnames or "sentence" not in reader.fieldnames:
            raise ValueError("Input TSV must contain a 'sentence' column")
        for line_no, row in enumerate(reader, 2):
            text = " ".join((row.get("sentence") or "").split())
            if len(text) < 2:
                rejected += 1
                continue
            try:
                up = int(row.get("up_votes") or 0)
                down = int(row.get("down_votes") or 0)
            except ValueError as exc:
                raise ValueError(f"Line {line_no}: invalid vote count") from exc
            if up < minimum_votes or down > up:
                rejected += 1
                continue
            sentence_id = (row.get("sentence_id") or "").strip()
            if not sentence_id:
                sentence_id = hashlib.sha256(text.casefold().encode("utf-8")).hexdigest()
            digest = hashlib.sha256(text.casefold().encode("utf-8")).hexdigest()
            if digest in seen:
                rejected += 1
                continue
            seen.add(digest)
            record = {
                "text": text, "language": language, "license": license_id,
                "source": source, "source_url": source_url,
                "dataset_version": dataset_version,
                "document_id": f"{source}:{dataset_version}:{sentence_id}",
                "sentence_domain": (row.get("sentence_domain") or "").strip(),
                "variant": (row.get("variant") or "").strip(),
            }
            if retrieved_at:
                record["retrieved_at"] = retrieved_at
            target.write(json.dumps(record, ensure_ascii=False) + "\n")
            written += 1
    if written == 0:
        output.unlink(missing_ok=True)
        raise ValueError("No eligible sentence rows were imported")
    return {"written": written, "rejected": rejected}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True, help="Common Voice TSV, e.g. validated_sentences.tsv")
    parser.add_argument("--output", required=True)
    parser.add_argument("--language", required=True, help="Locale code, e.g. sw")
    parser.add_argument("--source", required=True, help="Stable source identifier")
    parser.add_argument("--source-url", default=DEFAULT_SOURCE_URL)
    parser.add_argument("--dataset-version", required=True)
    parser.add_argument("--license", default=DEFAULT_LICENSE)
    parser.add_argument("--retrieved-at", help="Retrieval date YYYY-MM-DD")
    parser.add_argument("--minimum-votes", type=int, default=0)
    args = parser.parse_args()
    if args.minimum_votes < 0:
        parser.error("--minimum-votes cannot be negative")
    result = import_tsv(
        args.input, args.output, language=args.language, source=args.source,
        source_url=args.source_url, dataset_version=args.dataset_version,
        license_id=args.license, retrieved_at=args.retrieved_at,
        minimum_votes=args.minimum_votes,
    )
    print(f"Imported {result['written']} rows; skipped {result['rejected']} rows")


if __name__ == "__main__":
    main()
