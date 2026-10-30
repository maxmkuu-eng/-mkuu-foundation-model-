import json

import pytest

from data.split_dataset import split_records


def write_rows(path, rows):
    with path.open("w", encoding="utf-8") as stream:
        for row in rows:
            stream.write(json.dumps(row, ensure_ascii=False) + "\\n")


def test_split_is_deterministic_and_keeps_documents_together(tmp_path):
    source = tmp_path / "input.jsonl"
    rows = [
        {"text": f"Unique sample text number {i}", "language": "sw-TZ",
         "license": "CC0-1.0", "source": "test-corpus",
         "document_id": f"doc-{i}"}
        for i in range(30)
    ]
    rows += [{"text": "Second paragraph from document zero", "language": "sw-TZ",
              "license": "CC0-1.0", "source": "test-corpus",
              "document_id": "doc-0"}]
    write_rows(source, rows)

    first, second = tmp_path / "first", tmp_path / "second"
    counts = split_records(source, first)
    split_records(source, second)

    assert sum(counts.values()) == len(rows)
    for name in ("train", "validation", "test"):
        assert (first / f"{name}.jsonl").read_text() == (second / f"{name}.jsonl").read_text()

    document_splits = {}
    for name in ("train", "validation", "test"):
        with (first / f"{name}.jsonl").open(encoding="utf-8") as stream:
            for line in stream:
                row = json.loads(line)
                assert row["split"] == name
                previous = document_splits.setdefault(row["document_id"], name)
                assert previous == name


def test_split_rejects_missing_provenance(tmp_path):
    source = tmp_path / "bad.jsonl"
    write_rows(source, [{"text": "A sufficiently long example", "language": "sw"}])
    with pytest.raises(ValueError, match="missing required fields"):
        split_records(source, tmp_path / "out")


def test_split_rejects_duplicate_text(tmp_path):
    source = tmp_path / "dupes.jsonl"
    base = {"language": "sw", "license": "CC0-1.0", "source": "test"}
    rows = [
        {**base, "text": "Duplicate sentence in corpus", "document_id": "a"},
        {**base, "text": "  Duplicate   sentence in corpus ", "document_id": "b"},
        {**base, "text": "Another unique sentence in corpus", "document_id": "c"},
    ]
    write_rows(source, rows)
    with pytest.raises(ValueError, match="duplicate text"):
        split_records(source, tmp_path / "out")
