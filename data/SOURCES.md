# MKUU dataset sourcing register

This file defines the source-admission process. **No dataset is approved merely because it is publicly downloadable.** No source has been imported or approved yet.

## Required admission checks

For every candidate corpus, record:
1. Exact dataset title and version/release.
2. Canonical publisher URL and retrieval date.
3. License identifier and a link to the full license terms.
4. Explicit confirmation that the license permits ML/AI training and redistribution of derived artifacts, or written permission from the rights holder.
5. Language(s), approximate size, format, known quality issues and collection method.
6. Privacy review: exclude personal, confidential, sensitive and unlawfully collected data.
7. Attribution and share-alike obligations, including whether model weights or generated outputs trigger any obligations.
8. Reviewer and decision: pending, approved, rejected.

If training rights are unclear, mark the source **pending** and do not ingest it. Do not scrape websites, social media, books, news or other copyrighted material without permission. Do not put credentials, private user content, raw corpora or large files in Git.

## Candidate source register

| Dataset/source | Languages | Version | License / permission evidence | Training allowed? | Decision |
|---|---|---|---|---|---|
| Not yet reviewed | — | — | — | Unknown | Pending |

## Record format

Each JSONL record must include:
- `text`: UTF-8 text.
- `language`: ISO 639-1 code where available.
- `license`: exact license identifier or permission reference.
- `source`: stable dataset/source identifier.
- Recommended additional fields: `source_url`, `dataset_version`, `split`, `retrieved_at`, `document_id`.

## Language coverage targets

See [languages.yaml](languages.yaml). The list is a coverage plan, not evidence that corpora exist. Prioritize Kiswahili, English and Hausa for the first data audit, then expand while monitoring per-language balance.

## Splits and quality

Keep train, validation and test splits separate by document/source where possible to reduce leakage. Deduplicate exact and near-duplicate text, detect language, filter boilerplate and malformed text, and measure token counts per language. Preserve provenance through every transformation.
