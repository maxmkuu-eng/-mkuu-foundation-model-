# MKUU AI Android chat test

This APK is a temporary full chat integration using the Google Gemini Developer API.

## Features
- Text chat with real model-generated answers.
- Multi-turn conversation context (up to 10 recent exchanges).
- Tanzania-focused Swahili system instruction.
- Voice input through the Android speech-recognition service.
- Optional text-to-speech playback for the latest answer.
- Primary model: `gemini-3.1-flash-lite`; fallback: `gemini-3.8-flash`.

## Setup
1. Create a Gemini API key in Google AI Studio: https://aistudio.google.com/app/apikey
2. Install the debug APK.
3. Paste your key into the API key field and save it.
4. Type a message or use the microphone. The app sends the conversation to Gemini and displays its answer.

The API key is stored in the app's private preferences on this phone. It is not embedded in the APK or committed to this repository. Anyone who can extract app data from a compromised/rooted device may be able to recover it. For production, move API calls behind a secured backend; do not ship a shared developer key in a public APK.

## Important
This is a temporary external-API integration for testing MKUU's chat experience. It does not mean the repository's own foundation model has been trained or is running. The long-term target remains replacing the API call with the repository's own inference runtime and trained model weights.

## Build
`gradle :app:assembleDebug --no-daemon`

The output is `app/build/outputs/apk/debug/app-debug.apk`. No release keystore or signing configuration is used.
