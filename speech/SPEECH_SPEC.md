# MKUU speech capability plan

## User-facing goal
MKUU should support spoken conversation: the user can speak Kiswahili (including natural Tanzanian pronunciation and code-switching), MKUU transcribes and understands it, then replies in generated speech. Text chat must continue to work independently.

## Speech output implemented: offline eSpeak NG adapter
- `speech/tts_espeak.py` now provides a working local Text-to-Speech adapter using the eSpeak NG executable.
- Default voice identifier is `sw` (Swahili); output can be played directly or saved as a WAV file.
- No paid API, network request, cloud account, or model download is required at runtime.
- Install eSpeak NG on the host first. On Debian/Ubuntu: `sudo apt install espeak-ng`.
- Example: `python -m speech.tts_espeak "Habari, karibu MKUU AI."`
- Save audio: `python -m speech.tts_espeak "Habari, karibu MKUU AI." --output artifacts/mkuu_reply.wav`
- Speech is intelligible but synthetic/robotic; it is not a trained natural Tanzanian voice. Native-speaker pronunciation testing is still required.

## Required full voice pipeline
1. **Speech input / ASR:** audio capture, voice activity detection, transcription, language identification, punctuation and optional transcript correction. Evaluate Tanzanian Kiswahili, regional accents, mtaani slang, names, numbers and Swanglish.
2. **Conversation model:** pass the transcript through the same MKUU conversation interface and preserve conversation context.
3. **Speech output / TTS:** synthesize the assistant response, with a natural Kiswahili voice, correct pronunciation, pacing and optional speaking-rate controls. The initial offline eSpeak NG adapter is implemented as a baseline.
4. **Turn-taking:** interruption/barge-in, replay, mute, transcript display, permission handling and graceful fallback to text.
5. **Privacy:** request microphone permission explicitly, show when recording is active, avoid retaining raw audio by default, and document any storage/retention.

## Zero-budget integration strategy
- Prefer locally runnable, open-source components with licenses that permit the intended use.
- Do not add paid API dependencies or hard-code a cloud provider.
- Benchmark actual device memory, latency and supported languages before choosing a runtime.
- Keep ASR and TTS replaceable; neither is part of the current text Transformer weights.
- Do not claim Tanzanian accent quality until native speakers evaluate transcription and pronunciation.

## Current status and limitations
The repository now has an executable TTS path when eSpeak NG is installed. This is speech synthesis, not a trained MKUU voice model. ASR, microphone capture, Android playback integration, interruption controls, voice dataset and speech checkpoints are not implemented. The Python adapter runs on a host with the eSpeak NG command-line program; it does not by itself add a microphone or speaker button to the separate Android app.
