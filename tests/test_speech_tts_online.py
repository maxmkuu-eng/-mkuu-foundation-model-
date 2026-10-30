from pathlib import Path
from unittest.mock import patch
import unittest

from speech.tts_online import OnlineSpeechError, synthesize


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


if __name__ == "__main__":
    unittest.main()
