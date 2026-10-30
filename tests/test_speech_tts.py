from pathlib import Path
from unittest.mock import patch

import pytest

from speech.tts_espeak import SpeechSynthesisError, synthesize


def test_synthesize_writes_audio_file(tmp_path: Path):
    output = tmp_path / "reply.wav"

    def fake_run(command, **kwargs):
        Path(command[command.index("-w") + 1]).write_bytes(b"RIFFfake-wav")
        class Result:
            returncode = 0
            stderr = ""
            stdout = ""
        return Result()

    with patch("speech.tts_espeak.subprocess.run", side_effect=fake_run):
        result = synthesize("Habari, uko poa?", output, engine="espeak-ng")

    assert result == output
    assert output.read_bytes().startswith(b"RIFF")


def test_empty_text_is_rejected(tmp_path: Path):
    with pytest.raises(ValueError):
        synthesize("   ", tmp_path / "empty.wav", engine="espeak-ng")


def test_bad_speed_is_rejected(tmp_path: Path):
    with pytest.raises(ValueError):
        synthesize("Habari", tmp_path / "bad.wav", speed=500, engine="espeak-ng")


def test_missing_audio_is_reported(tmp_path: Path):
    class Result:
        returncode = 0
        stderr = ""
        stdout = ""

    with patch("speech.tts_espeak.subprocess.run", return_value=Result()):
        with pytest.raises(SpeechSynthesisError):
            synthesize("Habari", tmp_path / "missing.wav", engine="espeak-ng")
