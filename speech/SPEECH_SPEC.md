# MKUU speech capability plan

## Online speech output adapter
- `speech/tts_online.py` integrates with TTS.ai's documented online TTS API: submit text, poll the job and download MP3 output.
- Anonymous free tier: 5,000 characters/day per IP, up to 500 characters/request and 10 requests/minute, subject to provider changes.
- List current Swahili voices: `python -m speech.tts_online --list-voices`.
- Generate an MP3 (personal/non-commercial testing only with the configured Lanfrica voice): `python -m speech.tts_online "Habari, karibu MKUU AI." --acknowledge-noncommercial`.
- The provider marks Lanfrica as non-commercial only. The adapter requires explicit acknowledgement and must not be enabled in a commercial MKUU release. Select a voice with suitable commercial rights before commercial deployment.
- Optional account key is read from `TTS_AI_API_KEY`; never commit it or embed it in an Android client.
- The adapter validates provider download hosts and has mocked tests for submission, polling, download and invalid URLs.

## Offline fallback
- `speech/tts_espeak.py` uses the installed eSpeak NG executable for local Swahili TTS.
- eSpeak NG is intelligible but synthetic/robotic, not a natural Tanzanian voice.

## Remaining integration
- This repository is a model/training project and has no deployed chat-serving backend or Android UI. The adapter is callable Python code; it does not automatically speak each chat response inside the Android app.
- Android integration requires a backend endpoint that calls this adapter and returns audio, plus an Android audio player and a user-controlled auto-speak setting. Do not expose provider credentials in the app.
- ASR/microphone capture, permissions, interruption controls and native-speaker pronunciation evaluation remain unimplemented.
