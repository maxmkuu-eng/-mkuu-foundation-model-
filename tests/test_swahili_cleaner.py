import json

from data.clean_swahili_corpus import clean_corpus


def read_jsonl(path):
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]


def test_cleaner_preserves_colloquial_and_code_switched_text(tmp_path):
    source = tmp_path / "source.txt"
    source.write_text(
        "Mkuu vipi leo? Niko fresh, mambo yanaenda.\n"
        "ha ha ha ha ha nimecheka sana\n"
        "   habari   za   asubuhi   Tanzania  \n",
        encoding="utf-8",
    )
    candidate, review = tmp_path / "candidate.jsonl", tmp_path / "review.jsonl"

    stats = clean_corpus(
        source, candidate, review, source="fixture", version="1",
        source_url="https://example.test/source",
    )

    rows = read_jsonl(candidate)
    texts = [row["text"] for row in rows]
    assert "Mkuu vipi leo? Niko fresh, mambo yanaenda." in texts
    assert "ha ha ha ha ha nimecheka sana" in texts
    assert "habari za asubuhi Tanzania" in texts
    assert stats["candidate_rows"] == 3
    assert not read_jsonl(review)


def test_cleaner_deduplicates_case_insensitive_whitespace_variants(tmp_path):
    source = tmp_path / "source.txt"
    source.write_text("Habari za leo Tanzania\n  HABARI   ZA LEO TANZANIA  \n", encoding="utf-8")

    stats = clean_corpus(
        source, tmp_path / "candidate.jsonl", tmp_path / "review.jsonl",
        source="fixture", version="1", source_url="https://example.test/source",
    )

    assert stats["candidate_rows"] == 1
    assert stats["duplicates"] == 1


def test_cleaner_holds_long_xml_and_possible_phone_rows(tmp_path):
    source = tmp_path / "source.txt"
    source.write_text(
        "x" * 120 + "\n"
        "Normal sentence with <w:WordDocument> fragment\n"
        "Wasiliana nami kwa 0712345678 kwa maelezo zaidi\n",
        encoding="utf-8",
    )

    stats = clean_corpus(
        source, tmp_path / "candidate.jsonl", tmp_path / "review.jsonl",
        source="fixture", version="1", source_url="https://example.test/source",
        max_chars=100,
    )

    held = read_jsonl(tmp_path / "review.jsonl")
    assert len(held) == 3
    assert "TOO_LONG" in held[0]["review_reasons"]
    assert "XML_OR_WORD_ARTIFACT" in held[1]["review_reasons"]
    assert "POSSIBLE_PERSONAL_OR_LINK_DATA" in held[2]["review_reasons"]
    assert stats["candidate_rows"] == 0


def test_cleaner_keeps_provenance_and_marks_license_pending(tmp_path):
    source = tmp_path / "source.txt"
    source.write_text("Hii ni sentensi ya Kiswahili kwa majaribio.\n", encoding="utf-8")

    clean_corpus(
        source, tmp_path / "candidate.jsonl", tmp_path / "review.jsonl",
        source="sw-corpus", version="snapshot-1",
        source_url="https://huggingface.co/datasets/example",
    )

    row = read_jsonl(tmp_path / "candidate.jsonl")[0]
    assert row["source"] == "sw-corpus"
    assert row["dataset_version"] == "snapshot-1"
    assert row["document_id"] == "sw-corpus:snapshot-1:line-1"
    assert row["license"] == "PENDING-REVIEW"
    assert row["license_status"] == "pending"


def test_pretraining_rejects_pending_license_records(tmp_path):
    from training.pretrain import TextDataset

    source = tmp_path / "pending.jsonl"
    source.write_text(
        json.dumps({
            "text": "Hii ni sentensi ya Kiswahili ya kutosha.",
            "license": "PENDING-REVIEW",
            "license_status": "pending",
            "source": "sw-corpus",
        }) + "\\n",
        encoding="utf-8",
    )

    class FakeTokenizer:
        def encode(self, text, out_type=int):
            return [2, 10, 11, 12]

    import pytest
    with pytest.raises(ValueError, match="license status is not approved"):
        TextDataset(source, FakeTokenizer(), 8)
