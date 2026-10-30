"""Offline tests for the online TTS adapter; no provider calls are made."""
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from speech.tts_online import OnlineSpeechError, list_voices, synthesize


def http_response(payload: bytes):
    response = MagicMock()
    response.__enter__.return_value = response
    response.read.return_value = payload
    return response


class OnlineTtsGuardTests(unittest.TestCase):
    def test_rejects_empty_text(self):
        with self.assertRaises(ValueError):
            synthesize(" ", "out.mp3")

    def test_rejects_long_anonymous_text(self):
        with self.assertRaises(ValueError):
            synthesize("x" * 501, "out.mp3")

    def test_requires_voice_license_acknowledgement(self):
        with self.assertRaises(OnlineSpeechError):
            synthesize("Habari", "out.mp3")

    def test_rejects_bad_speed(self):
        with self.assertRaises(ValueError):
            synthesize("Habari", "out.mp3", speed=3.0)

    @patch("speech.tts_online.urllib.request.urlopen")
    def test_lists_swahili_voices(self, mocked_open):
        mocked_open.return_value = http_response(json.dumps({"voices": [{"id": "sw_voice"}]}).encode())
        self.assertEqual(list_voices(), [{"id": "sw_voice"}])
        self.assertIn("language=sw", mocked_open.call_args.args[0].full_url)

    @patch("speech.tts_online.time.sleep")
    @patch("speech.tts_online.urllib.request.urlopen")
    def test_submits_polls_and_saves_audio(self, mocked_open, _sleep):
        mocked_open.side_effect = [
            http_response(b'{"uuid":"job-123","status":"queued"}'),
            http_response(b'{"status":"completed","result_url":"https://api.tts.ai/audio.mp3"}'),
            http_response(b"FAKE-MP3"),
        ]
        with tempfile.TemporaryDirectory() as folder:
            output = Path(folder) / "reply.mp3"
            result = synthesize("Habari", output, acknowledge_noncommercial=True)
            self.assertEqual(result, output)
            self.assertEqual(output.read_bytes(), b"FAKE-MP3")
        self.assertEqual(mocked_open.call_count, 3)

    @patch("speech.tts_online.urllib.request.urlopen")
    def test_rejects_untrusted_audio_url(self, mocked_open):
        mocked_open.side_effect = [
            http_response(b'{"uuid":"job-123"}'),
            http_response(b'{"status":"completed","result_url":"https://evil.example/a.mp3"}'),
        ]
        with self.assertRaises(OnlineSpeechError):
            synthesize("Habari", "ignored.mp3", acknowledge_noncommercial=True)


if __name__ == "__main__":
    unittest.main()
