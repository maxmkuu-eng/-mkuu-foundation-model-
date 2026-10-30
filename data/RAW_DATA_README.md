# Raw data intake

Place only approved, licensed source exports in this directory. Keep large corpora outside Git; this README is the only tracked intake guide.

Expected input: UTF-8 JSONL, one JSON object per line. Minimum fields:
```json
{"text":"Example text in the source language.","language":"sw","license":"CC-BY-4.0","source":"publisher-dataset-v1"}
```

Recommended provenance fields: `source_url`, `dataset_version`, `split`, `retrieved_at`, and `document_id`.

Before importing, obtain approval under [SOURCES.md](SOURCES.md). Do not use private messages, personal records, sensitive personal data, scraped social-media content, or material whose training rights are uncertain. Never commit the raw corpus to Git.
