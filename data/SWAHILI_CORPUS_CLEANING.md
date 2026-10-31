# Swahili Corpus cleaning workflow

This workflow converts the combined plain-text export into a **review candidate**. It does not approve the source for training, certify factual accuracy, or replace human review. Raw data and generated JSONL files must remain outside Git.

## Source status

Candidate source: [ngusadeep/Swahili-Corpus-Dataset](https://huggingface.co/datasets/ngusadeep/Swahili-Corpus-Dataset).

The downloaded snapshot previously inspected contained 1,693,227 non-empty lines. Its SHA-256 was `057bacef92295b5ece75347861e9a6feff658af0631bea948b2b448562d229cd`. Hugging Face metadata reported Apache-2.0, while the dataset README identified an underlying Mendeley Data source (Noel Masasi and Bernard Masua, 2024) with CC BY 4.0. The relationship between the wrapper, underlying source materials and rights to train on every included text has not been independently established. This source therefore remains **PENDING** in `data/SOURCES.md`. Do not change the output license/status to approved until the rights review is completed and documented.

## Run

```bash
python data/clean_swahili_corpus.py \
  --input /path/to/Swahili_Corpus_combined.txt \
  --output /path/to/swahili_candidate.jsonl \
  --review /path/to/swahili_held_for_review.jsonl
```

The script streams the input and does not load the whole corpus into RAM. It writes provenance fields, source line numbers and stable document IDs. By default, every output record has `license_status=pending` and `license=PENDING-REVIEW`. The output is not a training approval.

## Cleaning policy

- Normalize whitespace and remove empty/one-character rows.
- Remove exact duplicates after whitespace normalization and case-folding.
- Hold lines longer than 5,000 characters and rows containing recognizable Word/XML artifacts for review.
- Hold rows containing possible email addresses, URLs, Tanzanian phone numbers or long numeric identifiers for privacy review.
- Preserve informal Tanzanian Swahili, code-switching, political/religious discussion, and expressive laughter. Repeated-token patterns are flagged but are not automatically deleted.
- Do not classify each row's language with a simplistic keyword heuristic. The source-level language label is `sw`; mixed-language and English rows still need a separate language audit.

The held file is for human inspection. Do not silently discard it. A held row may contain useful content that can be repaired or safely retained after review.

## After cleaning

1. Resolve source licensing and attribution; keep the source pending until then.
2. Review held rows and privacy flags.
3. Run a proper per-record language and quality audit; preserve valid mtaani and Swanglish content.
4. Create reviewed records with truthful provenance and approved license status.
5. Split by document ID into train/validation/test; check source and language balance and ensure no document or duplicate leaks across splits.
6. Train the tokenizer on approved training text only.
7. Run the tiny smoke pipeline before any long training run.

Never commit raw corpora, processed datasets, personal data, tokenizer models, or model checkpoints to this repository.
