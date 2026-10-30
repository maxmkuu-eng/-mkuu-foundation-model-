# MKUU speech capability plan

## Online speech output adapter
- Added `speech/tts_online.py`, an HTTP adapter for TTS.ai's online TTS job API.
- It submits text, polls the job, downloads the resulting MP3 and saves it locally.
- Anonymous access is documented by the provider as up to 5,000 characters/day, 500 characters/request and 10 requests/minute. Limits and availability can change.
- Default configured Swahili voice is Piper's `Lanfrica`. The provider's current terms mark this voice non-commercial only. The adapter refuses to use it unless the caller explicitly acknowledges that restriction. Do not enable this voice in a commercial MKUU release.
- An optional `TTS_AI_API_KEY` environment variable is supported; never commit a key or place it in an Android client.
- Example (personal/non-commercial testing only):
  ```bash
  python -m speech.tts_online "Habari, karibu MKUU AI." --acknowledge-noncommercial
  ```
- The provider's anonymous free allowance is suitable for evaluation, not a guaranteed unlimited production service.

## Offline fallback
- `speech/tts_espeak.py` provides local Swahili TTS when eSpeak NG is installed.
- eSpeak NG is intelligible but synthetic/robotic, not a natural Tanzanian voice.

## Remaining work
- Select a Swahili voice whose license permits MKUU's intended distribution and commercial use, if applicable.
- Integrate the adapter into the actual chat-serving runtime and Android playback UI; this repository does not currently contain that app runtime.
- Implement ASR/microphone capture, permissions, playback controls, interruption and fallback.
- Evaluate pronunciation with Tanzanian native speakers. Do not claim a Tanzanian accent before evaluation.
