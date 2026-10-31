"""Conservative, streaming cleaner for the Swahili Corpus text export.

This creates a REVIEW CANDIDATE, never an automatically approved training set.
It preserves colloquial Swahili, code-switching, political/religious discussion,
and repeated expressive language. Suspect long/XML/PII-like rows are written to
a separate review JSONL rather than silently discarded.
"""
import argparse
import hashlib
import json
import re
from pathlib import Path

XML_NOISE = re.compile(
    r"(?:<\?xml|<w:|</w:|\b(?:mso|latentstyles|lsdexception|deflockedstate)\b)",
    re.IGNORECASE,
)
REPEATED_TOKEN = re.compile(r"\b([\w'-]+)(?:\s+\1){4,}\b", re.IGNORECASE)
EMAIL = re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.IGNORECASE)
URL = re.compile(r"\b(?:https?://|www\.)\S+", re.IGNORECASE)
TZ_PHONE = re.compile(r"(?<!\d)(?:\+?255|0)(?:6|7|8|9)\d{8}(?!\d)")
LONG_NUMBER = re.compile(r"(?<!\d)\d{9,}(?!\d)")


def clean_corpus(input_path, output_path, review_path, *, source, version,
                 source_url, license_id="PENDING-REVIEW", max_chars=5000):
    """Stream a plain-text corpus into provenance-labelled candidate JSONL."""
    if not all((source, version, source_url, license_id)):
        raise ValueError("source, version, source_url and license_id are required")
    if max_chars < 100:
        raise ValueError("max_chars must be at least 100")

    output = Path(output_path)
    review = Path(review_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    review.parent.mkdir(parents=True, exist_ok=True)

    seen = set()
    stats = {
        "source_lines": 0, "candidate_rows": 0, "duplicates": 0,
        "empty_or_too_short": 0, "held_long": 0, "held_xml": 0,
        "pii_flagged": 0, "repeated_token_flagged": 0, "review_rows": 0,
    }

    with open(input_path, encoding="utf-8-sig") as src, \
         output.open("w", encoding="utf-8") as dst, \
         review.open("w", encoding="utf-8") as held:
        for line_no, raw in enumerate(src, 1):
            stats["source_lines"] += 1
            text = " ".join(raw.split())
            if len(text) < 2:
                stats["empty_or_too_short"] += 1
                continue

            reasons = []
            if len(text) > max_chars:
                reasons.append("TOO_LONG")
                stats["held_long"] += 1
            if XML_NOISE.search(text):
                reasons.append("XML_OR_WORD_ARTIFACT")
                stats["held_xml"] += 1
            if EMAIL.search(text) or URL.search(text) or TZ_PHONE.search(text) or LONG_NUMBER.search(text):
                reasons.append("POSSIBLE_PERSONAL_OR_LINK_DATA")
                stats["pii_flagged"] += 1

            repeated = bool(REPEATED_TOKEN.search(text))
            if repeated:
                stats["repeated_token_flagged"] += 1

            digest = hashlib.sha256(text.casefold().encode("utf-8")).hexdigest()
            if digest in seen:
                stats["duplicates"] += 1
                continue
            seen.add(digest)

            record = {
                "text": text,
                "language": "sw",
                "license": license_id,
                "license_status": "pending",
                "source": source,
                "source_url": source_url,
                "dataset_version": version,
                "document_id": f"{source}:{version}:line-{line_no}",
                "source_line": line_no,
                "quality_flags": (["REPEATED_TOKEN_PATTERN"] if repeated else []),
            }
            if reasons:
                stats["review_rows"] += 1
                record["review_reasons"] = reasons
                held.write(json.dumps(record, ensure_ascii=False) + "\n")
            else:
                dst.write(json.dumps(record, ensure_ascii=False) + "\n")
                stats["candidate_rows"] += 1

    stats["candidate_file"] = str(output)
    stats["review_file"] = str(review)
    return stats


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True, help="Original UTF-8 combined text file")
    parser.add_argument("--output", required=True, help="Review-candidate JSONL")
    parser.add_argument("--review", required=True, help="Held-for-review JSONL")
    parser.add_argument("--source", default="ngusadeep-swahili-corpus")
    parser.add_argument("--version", default="hf-snapshot-edc06d0")
    parser.add_argument("--source-url", default="https://huggingface.co/datasets/ngusadeep/Swahili-Corpus-Dataset")
    parser.add_argument("--license", default="PENDING-REVIEW")
    parser.add_argument("--max-chars", type=int, default=5000)
    args = parser.parse_args()
    result = clean_corpus(
        args.input, args.output, args.review, source=args.source,
        version=args.version, source_url=args.source_url,
        license_id=args.license, max_chars=args.max_chars,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
