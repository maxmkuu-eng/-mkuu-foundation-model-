# MKUU dataset sourcing register

This file defines the source-admission process. **No dataset is approved merely because it is publicly downloadable.** No raw dataset has been imported or approved yet.

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

| Dataset/source | Languages | Version | License / permission evidence | Intended use | Decision |
|---|---|---|---|---|---|
| Mozilla Common Voice Scripted Speech | Swahili, including Tanzania mainland variety where present | 27.0 (current release announced 2026-09-18) | Mozilla states Common Voice datasets are CC0; [legal terms](https://commonvoice.mozilla.org/dav/terms) and [Data Collective catalogue](https://commonvoice.mozilla.org/dav/datasets) | Speech recognition/transcription; extracted sentence text may be assessed for language-model pretraining, not conversational SFT | Pending: verify Swahili 27.0 package, exact metadata, text availability, privacy and quality |
| Mozilla Common Voice Spontaneous Speech | Swahili is newly listed among supported languages | 5.0 (released 2026-09-18) | Mozilla states Common Voice datasets are CC0; [legal terms](https://commonvoice.mozilla.org/dav/terms) and [Data Collective catalogue](https://commonvoice.mozilla.org/dav/datasets) | Potential conversational-style language exposure only after transcript and prompt/response structure are inspected; not automatically suitable for SFT | Pending: verify Swahili package availability, transcript license/terms, consent/privacy and dataset structure |
| Mozilla Common Voice Scripted Speech 25.0 — Swahili (\`sw\`, including `sw-baratz`) | Kiswahili; Tanzania variety identified in release metadata | 25.0 (2026-03-09) | CC0-1.0 reported in [release datasheet](https://test-proxy.konza.go.ke/items/28fba537-6452-4676-a1cc-7430cfb82964); [Mozilla Data Collective](https://datacollective.mozillafoundation.org/datasets/cmn3ailbd008nmb07mjyu3xro) | Speech/transcription; candidate sentence text for language exposure only | Pending: superseded by newer release candidate; retain as historical metadata until 27.0 is verified |

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

## Intake decision

No corpus has been downloaded, imported into training data, or approved for training by this change. Mozilla's current terms say Common Voice datasets are offered under CC0 through Mozilla Data Collective and ask users not to post, distribute or mirror the datasets elsewhere; access should remain through MDC. Respect that restriction and keep raw files out of this Git repository. See [Common Voice Legal Terms](https://commonvoice.mozilla.org/dav/terms).

## References

- [Mozilla Common Voice 27.0 / Spontaneous Speech 5.0 release announcement (2026-09-18)](https://discourse.mozilla.org/t/common-voice-scripted-speech-v27-0-and-spontaneous-speech-v5-0-released/149490)
- [Mozilla Common Voice Legal Terms](https://commonvoice.mozilla.org/dav/terms)
- [Mozilla Data Collective dataset catalogue](https://commonvoice.mozilla.org/dav/datasets)
- [Common Voice Swahili 25.0 release datasheet](https://test-proxy.konza.go.ke/items/28fba537-6452-4676-a1cc-7430cfb82964)
