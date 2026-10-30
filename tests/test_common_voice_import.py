import json

import pytest

from data.import_common_voice import import_tsv


def test_imports_text_and_provenance_but_discards_speaker_data(tmp_path):
    source = tmp_path / "validated_sentences.tsv"
    source.write_text(
        "sentence_id\tsentence\tvariant\tsentence_domain\tsource\n"
        "s1\t Habari   za asubuhi \tsw-TZ\tgeneral\tcommunity\n"
        "s2\tKaribu Tanzania\tsw\ttravel\tcommunity\n",
        encoding="utf-8",
    )
    output = tmp_path / "out.jsonl"
    result = import_tsv(
        source, output, language="sw", source="common-voice-scripted",
        source_url="https://mozilladatacollective.com/datasets",
        dataset_version="27.0", retrieved_at="2026-10-30",
    )
    rows = [json.loads(line) for line in output.read_text(encoding="utf-8").splitlines()]
    assert result == {"written": 2, "rejected": 0}
    assert rows[0]["text"] == "Habari za asubuhi"
    assert rows[0]["license"] == "CC0-1.0"
    assert rows[0]["document_id"].endswith(":s1")
    assert "client_id" not in rows[0] and "age" not in rows[0]


def test_deduplicates_and_rejects_unvalidated_rows(tmp_path):
    source = tmp_path / "clips.tsv"
    source.write_text(
        "sentence_id\tsentence\tup_votes\tdown_votes\n"
        "a\tSentensi moja ya majaribio\t4\t1\n"
        "b\t Sentensi   moja ya majaribio \t3\t0\n"
        "c\tHii imekataliwa\t1\t2\n",
        encoding="utf-8",
    )
    result = import_tsv(
        source, tmp_path / "out.jsonl", language="sw", source="cv",
        source_url="https://example.org/dataset", dataset_version="27.0",
        minimum_votes=2,
    )
    assert result == {"written": 1, "rejected": 2}


def test_requires_sentence_column(tmp_path):
    source = tmp_path / "bad.tsv"
    source.write_text("text\nhello\n", encoding="utf-8")
    with pytest.raises(ValueError, match="sentence"):
        import_tsv(
            source, tmp_path / "out.jsonl", language="sw", source="cv",
            source_url="https://example.org", dataset_version="27.0",
        )
