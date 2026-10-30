# MKUU speech capability plan

## User-facing goal
MKUU should support spoken conversation: the user can speak Kiswahili (including natural Tanzanian pronunciation and code-switching), MKUU transcribes and understands it, then replies in generated speech. Text chat must continue to work independently.

## Required pipeline
1. **Speech input / ASR:** audio capture, voice activity detection, transcription, language identification, punctuation and optional transcript correction. Evaluate Tanzanian Kiswahili, regional accents, mtaani slang, names, numbers and Swanglish.
2. **Conversation model:** pass the transcript through the same MKUU conversation interface and preserve conversation context.
3. **Speech output / TTS:** synthesize the assistant response, with a natural Kiswahili voice, correct pronunciation, pacing and optional speaking-rate controls.
4. **Turn-taking:** interruption/barge-in, replay, mute, transcript display, permission handling and graceful fallback to text.
5. **Privacy:** request microphone permission explicitly, show when recording is active, avoid retaining raw audio by default, and document any storage/retention.

## Zero-budget integration strategy
- Define provider-neutral ASR and TTS interfaces; prefer locally runnable, open-source models with licenses that permit the intended use.
- Do not add paid API dependencies or hard-code a cloud provider.
- Benchmark actual device memory, latency and supported languages before choosing a runtime.
- Keep ASR and TTS as replaceable components; neither is part of the current text Transformer weights.
- Do not claim Tanzanian Kiswahili voice support until native speakers evaluate transcription and pronunciation.

## Status
Design specification only. This repository currently has no audio encoder, ASR model, TTS model, microphone/audio runtime, voice dataset, or speech checkpoint. The text-only MKUU model cannot yet listen or speak aloud.
