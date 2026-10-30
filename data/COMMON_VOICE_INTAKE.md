# Common Voice intake

Common Voice Scripted Speech 27.0 includes Swahili (`sw`) and is listed as
CC0-1.0 in the Mozilla Data Collective catalogue. The release announcement
also lists Swahili in Spontaneous Speech 5.0. These are source facts, not
evidence that an archive has been downloaded or that its contents passed
MKUU's quality review.

## Import sentence text

1. Obtain the Swahili dataset through the official
   [Mozilla Data Collective catalogue](https://commonvoice.mozilla.org/dav/datasets).
   Do not scrape or mirror the archive, and do not commit the raw archive.
2. Extract the archive locally. Use `validated_sentences.tsv` for the
   validated sentence corpus when available; alternatively use a clips TSV
   with a `sentence` column. The importer never retains speaker IDs,
   demographics, audio paths or speaker-level data.
3. Run:

```bash
python data/import_common_voice.py \
  --input /path/to/validated_sentences.tsv \
  --output data/processed/common_voice_sw_27.jsonl \
  --language sw \
  --source common-voice-scripted-speech \
  --dataset-version 27.0 \
  --license CC0-1.0 \
  --retrieved-at YYYY-MM-DD
```

For clips TSV input, use `--minimum-votes 2` to retain only sentences
with at least two up-votes and no more down-votes than up-votes.
Empty rows and duplicate normalized sentence text are skipped. Every output
row carries source, version, license, URL and a stable document ID.

4. Review language variety, text quality, duplicates, privacy and source
balance. Then split by document:

```bash
python data/split_dataset.py --input data/processed/common_voice_sw_27.jsonl --output-dir data/approved/common_voice_sw_27
```

5. Combine only reviewed and approved train-split data for tokenizer and
pretraining. Common Voice is read-speech/transcription material; do not treat
it as conversational instruction/response data or SFT by default.

The importer and tests use synthetic fixtures only. No Common Voice archive
or corpus is stored in this repository, and no model has been trained on it.
