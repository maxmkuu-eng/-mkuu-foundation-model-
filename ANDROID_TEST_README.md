# MKUU Android speech test APK

This is a phone-side integration test harness for the repository's speech work.

## What this APK tests
- Android TextToSpeech availability for Swahili (sw-TZ).
- Speaking typed text and stopping playback.
- Microphone permission and Android speech-recognition handoff for Swahili (sw-TZ).

Speech recognition is provided by an installed Android recognition service and may require network access or a separately installed speech service. It is not an ASR model shipped by this repository.

## What it does not test
The APK does not run the MKUU Transformer. The repository currently has no trained checkpoint, trained SentencePiece tokenizer artifact, or Android inference runtime. The app displays this limitation explicitly; it does not fake AI answers.

## Build
GitHub Actions workflow: `.github/workflows/android-test-apk.yml`

Build command:
```bash
gradle :app:assembleDebug --no-daemon
```

The output is `app/build/outputs/apk/debug/app-debug.apk`. It is an unsigned debug APK; no keystore or release-signing configuration is used.
