"""Online Swahili TTS adapter for TTS.ai's free Piper endpoint.

No API key is required for the anonymous free tier. The Swahili Lanfrica
voice is marked non-commercial by its provider; callers must explicitly
acknowledge that restriction before using it. Never embed account keys here.
"""
from __future__ import annotations

import argparse
import json
import os
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

API_BASE = "https://api.tts.ai/v1"


class OnlineSpeechError(RuntimeError):
    """Raised when online speech synthesis fails."""


def synthesize(
    text: str,
    output: str | Path,
    *,
    voice: str = "Lanfrica",
    model: str = "piper",
    language: str = "sw",
    speed: float = 1.0,
    acknowledge_noncommercial: bool = False,
    api_key: str | None = None,
    timeout: int = 30,
    poll_timeout: int = 120,
) -> Path:
    """Generate online audio and save it locally.

    TTS.ai currently documents an anonymous free allowance of 5,000
    characters/day, max 500 characters/request and 10 requests/minute.
    The Lanfrica Swahili Piper voice is non-commercial only.
    """
    clean = text.strip()
    if not clean:
        raise ValueError("Text to speak cannot be empty.")
    if len(clean) > 500 and not api_key:
        raise ValueError("Anonymous free requests are limited to 500 characters.")
    if not 0.5 <= speed <= 2.0:
        raise ValueError("speed must be between 0.5 and 2.0.")
    if voice.lower() == "lanfrica" and not acknowledge_noncommercial:
        raise OnlineSpeechError(
            "Lanfrica ni sauti yenye leseni ya matumizi yasiyo ya kibiashara. "
            "Thibitisha ruhusa hiyo kwa acknowledge_noncommercial=True."
        )

    headers = {"Content-Type": "application/json", "Accept": "application/json"}
    token = api_key or os.getenv("TTS_AI_API_KEY")
    if token:
        headers["Authorization"] = f"Bearer {token}"
    payload = json.dumps({
        "model": model, "text": clean, "voice": voice,
        "language": language, "speed": speed, "format": "mp3",
    }).encode("utf-8")
    request = urllib.request.Request(f"{API_BASE}/tts/", data=payload,
                                     headers=headers, method="POST")
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            job = json.loads(response.read().decode("utf-8"))
    except (urllib.error.URLError, TimeoutError, ValueError) as exc:
        raise OnlineSpeechError(f"TTS.ai request failed: {exc}") from exc

    job_uuid = job.get("uuid")
    if not job_uuid:
        raise OnlineSpeechError(f"TTS.ai did not return a job UUID: {job}")

    deadline = time.monotonic() + poll_timeout
    while time.monotonic() < deadline:
        query = urllib.parse.urlencode({"uuid": job_uuid})
        poll = urllib.request.Request(f"{API_BASE}/speech/results/?{query}",
                                      headers={"Accept": "application/json"})
        try:
            with urllib.request.urlopen(poll, timeout=timeout) as response:
                status = json.loads(response.read().decode("utf-8"))
        except (urllib.error.URLError, TimeoutError, ValueError) as exc:
            raise OnlineSpeechError(f"Could not check TTS job: {exc}") from exc
        if status.get("status") == "failed":
            raise OnlineSpeechError(status.get("error", "TTS job failed"))
        if status.get("status") == "completed":
            result_url = status.get("result_url")
            if not result_url:
                raise OnlineSpeechError("TTS.ai did not return an audio URL.")
            parsed_result = urllib.parse.urlparse(result_url)
            if parsed_result.scheme != "https" or parsed_result.hostname not in {"api.tts.ai", "tts.ai"}:
                raise OnlineSpeechError("TTS.ai returned an untrusted audio URL.")
            try:
                with urllib.request.urlopen(result_url, timeout=timeout) as response:
                    audio = response.read()
            except (urllib.error.URLError, TimeoutError) as exc:
                raise OnlineSpeechError(f"Audio download failed: {exc}") from exc
            if not audio:
                raise OnlineSpeechError("TTS.ai returned an empty audio file.")
            destination = Path(output).expanduser()
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_bytes(audio)
            return destination
        time.sleep(1.5)
    raise OnlineSpeechError("TTS job timed out while waiting for audio.")


def list_voices(*, language: str = "sw", model: str | None = None, timeout: int = 20) -> list[dict]:
    """Fetch available provider voices so callers can verify voice IDs."""
    params = {"language": language}
    if model:
        params["model"] = model
    query = urllib.parse.urlencode(params)
    request = urllib.request.Request(f"{API_BASE}/voices/?{query}", headers={"Accept": "application/json"})
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except (urllib.error.URLError, TimeoutError, ValueError) as exc:
        raise OnlineSpeechError(f"Could not list TTS voices: {exc}") from exc
    voices = payload.get("voices")
    if not isinstance(voices, list):
        raise OnlineSpeechError("TTS.ai returned an invalid voice list.")
    return voices


def main() -> int:
    parser = argparse.ArgumentParser(description="MKUU online Swahili TTS")
    parser.add_argument("text")
    parser.add_argument("--output", default="artifacts/mkuu_online_reply.mp3")
    parser.add_argument("--voice", default="Lanfrica")
    parser.add_argument("--list-voices", action="store_true", help="List provider voices for Swahili and exit")
    parser.add_argument("--acknowledge-noncommercial", action="store_true")
    args = parser.parse_args()
    try:
        if args.list_voices:
            print(json.dumps(list_voices(), ensure_ascii=False, indent=2))
            return 0
        path = synthesize(args.text, args.output, voice=args.voice,
                          acknowledge_noncommercial=args.acknowledge_noncommercial)
    except (OnlineSpeechError, ValueError) as exc:
        parser.error(str(exc))
    print(f"Audio saved: {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
