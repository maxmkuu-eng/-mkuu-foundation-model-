# MKUU Foundation Chat and Android APK Pilot

## What this adds
- A small Android chat client in \`app/\`.
- A FastAPI service in \`api/\` that loads the repository's own MKUU checkpoint and SentencePiece tokenizer.
- DuckDuckGo HTML retrieval to add current web snippets and source links to the model prompt.
- A Colab notebook that mounts the existing Google Drive checkpoint, starts the API on the Colab GPU, and exposes a temporary HTTPS endpoint.
- A GitHub Actions workflow that builds and uploads a normal **debug APK**. No release keystore or signing secret is required.

The API does not call Gemini, OpenAI, or another hosted language model. The foundation model generates the response; web retrieval supplies external context. Search availability depends on the public search service and internet connection.

## 1. Build the APK
1. Open the repository's Actions tab.
2. Select **Build MKUU Android Debug APK**.
3. Run the workflow manually, or push an app/workflow change to \`colab-t4-pilot\`.
4. Open the successful workflow run and download the \`mkuu-foundation-chat-debug\` artifact.
5. Extract \`app-debug.apk\` and install it on an Android phone.

The APK is a debug test build, not a Play Store release.

## 2. Start the temporary model server
1. Open \`notebooks/MKUU_Chat_API_Colab.ipynb\` in Google Colab.
2. Select a GPU runtime (T4 if available).
3. Run every cell from top to bottom and approve Google Drive access.
4. The notebook expects these existing Drive files:
   - \`MyDrive/MKUU-Foundation-Model/checkpoints/last.pt\`
   - \`MyDrive/MKUU-Foundation-Model/mkuu_swahili_spm.model\`
5. The last cell prints an HTTPS Cloudflare URL and a one-time access token. Keep the Colab runtime running.

If either Drive file is missing, the notebook stops with a clear error; it does not silently substitute another model.

## 3. Connect the Android app
1. Open MKUU AI on the phone.
2. Paste the printed HTTPS URL into **Colab API URL**.
3. Paste the printed token into **Access token**.
4. Send a test message.

The app sends the message and recent in-memory conversation turns to \`/chat\`. The API searches the web, passes retrieved snippets to the MKUU model, and returns the generated response with source links. The URL and token are saved locally in app preferences. Do not share the token.

## Important pilot limitations
- Colab is a temporary server. If the runtime stops, the API and tunnel stop; start the notebook again and update the URL/token in the app.
- The current 300M checkpoint was trained for a limited pilot run. Successful loading and generation do **not** prove conversational quality, factual accuracy, or Tanzanian Kiswahili fluency. Human testing and additional supervised fine-tuning are still required.
- The APK is a network client; the 300M model is not embedded in the APK and does not run offline on the phone.
- DuckDuckGo HTML search is a best-effort public retrieval adapter, not a guaranteed search API. Some queries may return no results or be rate-limited.
- The Cloudflare trycloudflare URL is public to anyone who obtains it. The API token protects chat requests; keep it private and stop the tunnel after testing.
- This is a development pilot, not a production deployment. A stable hosted server, authentication lifecycle, abuse controls, monitoring, and privacy review are still needed before public release.
