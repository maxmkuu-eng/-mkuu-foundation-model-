"""Offline Swahili text-to-speech adapter powered by eSpeak NG.

Install the system package first (for example: sudo apt install espeak-ng).
This module deliberately does not download models or call paid/cloud APIs.
"""
from __future__ import annotations

import argparse
import shutil
import subprocess
from pathlib import Path
from typing import Sequence


class SpeechSynthesisError(RuntimeError):
    """Raised when the local speech engine is unavailable or fails."""


def find_engine() -> str:
    """Return the eSpeak NG executable path or raise a helpful error."""
    executable = shutil.which("espeak-ng")
    if not executable:
        raise SpeechSynthesisError(
            "eSpeak NG haijawekwa. Install espeak-ng, kisha jaribu tena."
        )
    return executable


def synthesize(
    text: str,
    output: str | Path,
    *,
    voice: str = "sw",
    speed: int = 155,
    engine: str | None = None,
) -> Path:
    """Synthesize text to a WAV file using the selected eSpeak NG voice."""
    clean_text = text.strip()
    if not clean_text:
        raise ValueError("Text to speak cannot be empty.")
    if not 80 <= speed <= 300:
        raise ValueError("speed must be between 80 and 300 words per minute.")
    if not voice or any(ch.isspace() for ch in voice):
        raise ValueError("voice must be a single eSpeak voice identifier.")

    executable = engine or find_engine()
    destination = Path(output).expanduser()
    destination.parent.mkdir(parents=True, exist_ok=True)
    command: Sequence[str] = (
        executable, "-v", voice, "-s", str(speed), "-w", str(destination), clean_text
    )
    try:
        result = subprocess.run(
            command, check=False, capture_output=True, text=True, timeout=120
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise SpeechSynthesisError(f"eSpeak NG imeshindwa kuanzisha: {exc}") from exc
    if result.returncode != 0 or not destination.is_file() or destination.stat().st_size == 0:
        detail = (result.stderr or result.stdout or "No audio file was produced").strip()
        raise SpeechSynthesisError(f"Speech synthesis failed: {detail}")
    return destination


def speak(text: str, *, voice: str = "sw", speed: int = 155) -> None:
    """Speak immediately through the device's default audio output."""
    clean_text = text.strip()
    if not clean_text:
        raise ValueError("Text to speak cannot be empty.")
    executable = find_engine()
    try:
        result = subprocess.run(
            [executable, "-v", voice, "-s", str(speed), clean_text],
            check=False, capture_output=True, text=True, timeout=120
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise SpeechSynthesisError(f"eSpeak NG imeshindwa kuzungumza: {exc}") from exc
    if result.returncode != 0:
        raise SpeechSynthesisError((result.stderr or result.stdout or "eSpeak NG failed").strip())


def main() -> int:
    parser = argparse.ArgumentParser(description="MKUU offline Swahili text-to-speech")
    parser.add_argument("text", help="Text to speak")
    parser.add_argument("--voice", default="sw", help="eSpeak voice code (default: sw)")
    parser.add_argument("--speed", type=int, default=155, help="Words per minute (80-300)")
    parser.add_argument("--output", help="Write WAV audio to this path instead of playing")
    args = parser.parse_args()
    try:
        if args.output:
            path = synthesize(args.text, args.output, voice=args.voice, speed=args.speed)
            print(f"Audio saved: {path}")
        else:
            speak(args.text, voice=args.voice, speed=args.speed)
    except (SpeechSynthesisError, ValueError) as exc:
        parser.error(str(exc))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
