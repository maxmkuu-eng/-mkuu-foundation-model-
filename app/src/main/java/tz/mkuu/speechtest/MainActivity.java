package tz.mkuu.speechtest;

import android.Manifest;
import android.app.Activity;
import android.content.Intent;
import android.content.SharedPreferences;
import android.content.pm.PackageManager;
import android.os.Bundle;
import android.speech.RecognizerIntent;
import android.speech.tts.TextToSpeech;
import android.view.Gravity;
import android.view.ViewGroup;
import android.widget.Button;
import android.widget.EditText;
import android.widget.LinearLayout;
import android.widget.ScrollView;
import android.widget.TextView;
import org.json.JSONArray;
import org.json.JSONObject;
import java.io.BufferedReader;
import java.io.InputStream;
import java.io.InputStreamReader;
import java.io.OutputStream;
import java.net.HttpURLConnection;
import java.net.URL;
import java.nio.charset.StandardCharsets;
import java.util.ArrayList;
import java.util.Locale;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;

public class MainActivity extends Activity {
    private static final int REQUEST_SPEECH = 41;
    private static final int REQUEST_MIC = 42;
    private static final String PREFS = "mkuu_chat_settings";
    private static final String PRIMARY_MODEL = "gemini-3.1-flash-lite";
    private static final String FALLBACK_MODEL = "gemini-3.8-flash";
    private final ExecutorService executor = Executors.newSingleThreadExecutor();
    private final JSONArray history = new JSONArray();
    private EditText input;
    private EditText apiKeyInput;
    private TextView status;
    private TextView conversation;
    private TextToSpeech tts;
    private boolean ttsReady = false;

    @Override public void onCreate(Bundle state) {
        super.onCreate(state);
        buildUi();
        tts = new TextToSpeech(this, result -> {
            if (result == TextToSpeech.SUCCESS) {
                int language = tts.setLanguage(new Locale("sw", "TZ"));
                ttsReady = language != TextToSpeech.LANG_MISSING_DATA
                        && language != TextToSpeech.LANG_NOT_SUPPORTED;
            }
        });
    }

    private void buildUi() {
        LinearLayout page = new LinearLayout(this);
        page.setOrientation(LinearLayout.VERTICAL);
        page.setPadding(22, 24, 22, 18);
        page.setBackgroundColor(0xFFF7FAFC);

        TextView title = new TextView(this);
        title.setText("MKUU AI");
        title.setTextSize(26);
        title.setTextColor(0xFF102A43);
        title.setGravity(Gravity.CENTER);
        page.addView(title, new LinearLayout.LayoutParams(-1, -2));

        TextView subtitle = new TextView(this);
        subtitle.setText("Msaidizi wa mazungumzo — jaribio la API ya Gemini");
        subtitle.setTextSize(14);
        subtitle.setTextColor(0xFF486581);
        subtitle.setPadding(0, 6, 0, 12);
        page.addView(subtitle);

        apiKeyInput = new EditText(this);
        apiKeyInput.setHint("Weka Gemini API key yako");
        apiKeyInput.setSingleLine(true);
        apiKeyInput.setInputType( android.text.InputType.TYPE_CLASS_TEXT
                | android.text.InputType.TYPE_TEXT_VARIATION_PASSWORD);
        SharedPreferences prefs = getSharedPreferences(PREFS, MODE_PRIVATE);
        apiKeyInput.setText(prefs.getString("api_key", ""));
        page.addView(apiKeyInput, new LinearLayout.LayoutParams(-1, -2));

        Button saveKey = new Button(this);
        saveKey.setText("Hifadhi API key kwenye simu hii");
        saveKey.setOnClickListener(v -> {
            String key = apiKeyInput.getText().toString().trim();
            if (key.isEmpty()) { setStatus("Weka API key kwanza."); return; }
            prefs.edit().putString("api_key", key).apply();
            setStatus("API key imehifadhiwa kwenye simu hii.");
        });
        page.addView(saveKey, new LinearLayout.LayoutParams(-1, -2));

        conversation = new TextView(this);
        conversation.setText("MKUU: Mambo! Niandikie unachotaka tuzungumzie.\n");
        conversation.setTextSize(16);
        conversation.setTextColor(0xFF243B53);
        conversation.setPadding(12, 12, 12, 12);
        conversation.setBackgroundColor(0xFFFFFFFF);
        ScrollView chatScroll = new ScrollView(this);
        chatScroll.addView(conversation);
        LinearLayout.LayoutParams chatParams = new LinearLayout.LayoutParams(-1, 0, 1);
        chatParams.setMargins(0, 12, 0, 12);
        page.addView(chatScroll, chatParams);

        input = new EditText(this);
        input.setHint("Andika ujumbe wako hapa...");
        input.setMinLines(2);
        input.setMaxLines(5);
        input.setGravity(Gravity.TOP | Gravity.START);
        page.addView(input, new LinearLayout.LayoutParams(-1, -2));

        Button send = new Button(this);
        send.setText("Tuma ujumbe");
        send.setOnClickListener(v -> sendMessage());
        page.addView(send, new LinearLayout.LayoutParams(-1, -2));

        Button listen = new Button(this);
        listen.setText("Zungumza kwa microphone");
        listen.setOnClickListener(v -> startListening());
        page.addView(listen, new LinearLayout.LayoutParams(-1, -2));

        Button speak = new Button(this);
        speak.setText("Soma jibu la mwisho kwa sauti");
        speak.setOnClickListener(v -> {
            if (ttsReady) tts.speak(lastAssistantReply, TextToSpeech.QUEUE_FLUSH, null, "mkuu-reply");
            else setStatus("Sauti ya Kiswahili haipatikani kwenye simu hii.");
        });
        page.addView(speak, new LinearLayout.LayoutParams(-1, -2));

        status = new TextView(this);
        status.setText("Tayari. Weka API key kisha tuma ujumbe.");
        status.setTextSize(13);
        status.setTextColor(0xFF486581);
        status.setPadding(0, 10, 0, 0);
        page.addView(status);

        TextView privacy = new TextView(this);
        privacy.setText("Ujumbe hutumwa kwa Google Gemini API. API key huhifadhiwa kwenye simu hii; usitumie key ya siri ya mtu mwingine.");
        privacy.setTextSize(11);
        privacy.setTextColor(0xFF627D98);
        privacy.setPadding(0, 8, 0, 0);
        page.addView(privacy);

        setContentView(page);
    }

    private String lastAssistantReply = "";

    private void sendMessage() {
        String message = input.getText().toString().trim();
        String key = apiKeyInput.getText().toString().trim();
        if (message.isEmpty()) { setStatus("Andika ujumbe kwanza."); return; }
        if (key.isEmpty()) { setStatus("Weka Gemini API key kwanza."); return; }
        getSharedPreferences(PREFS, MODE_PRIVATE).edit().putString("api_key", key).apply();
        input.setText("");
        appendChat("WEWE", message);
        input.setEnabled(false);
        setStatus("MKUU anafikiria...");
        executor.execute(() -> {
            try {
                JSONObject userContent = new JSONObject()
                        .put("role", "user")
                        .put("parts", new JSONArray().put(new JSONObject().put("text", message)));
                history.put(userContent);
                trimHistory();
                String answer;
                try {
                    answer = callGemini(key, PRIMARY_MODEL);
                } catch (Exception primaryError) {
                    answer = callGemini(key, FALLBACK_MODEL);
                    runOnUiThread(() -> setStatus("Modeli ya msingi haikupatikana; nimetumia fallback."));
                }
                String finalAnswer = answer;
                history.put(new JSONObject().put("role", "model")
                        .put("parts", new JSONArray().put(new JSONObject().put("text", answer))));
                runOnUiThread(() -> {
                    lastAssistantReply = finalAnswer;
                    appendChat("MKUU", finalAnswer);
                    input.setEnabled(true);
                    setStatus("Jibu limepatikana.");
                });
            } catch (Exception e) {
                if (history.length() > 0) history.remove(history.length() - 1);
                String error = friendlyError(e);
                runOnUiThread(() -> {
                    input.setEnabled(true);
                    setStatus(error);
                });
            }
        });
    }

    private void trimHistory() {
        while (history.length() > 20) history.remove(0);
    }

    private String callGemini(String key, String model) throws Exception {
        HttpURLConnection connection = null;
        try {
            URL url = new URL("https://generativelanguage.googleapis.com/v1beta/models/"
                    + model + ":generateContent");
            connection = (HttpURLConnection) url.openConnection();
            connection.setRequestMethod("POST");
            connection.setConnectTimeout(20000);
            connection.setReadTimeout(60000);
            connection.setDoOutput(true);
            connection.setRequestProperty("Content-Type", "application/json; charset=UTF-8");
            connection.setRequestProperty("x-goog-api-key", key);
            JSONArray contents = new JSONArray();
            for (int i = 0; i < history.length(); i++) contents.put(history.getJSONObject(i));
            JSONObject system = new JSONObject().put("parts", new JSONArray().put(
                    new JSONObject().put("text",
                            "Wewe ni MKUU AI, msaidizi rafiki aliyeundwa Tanzania. Jibu kwa Kiswahili cha kawaida cha Kitanzania, cha asili na chenye heshima. Elewa Sheng/mtaani inapofaa. Jibu swali moja kwa moja, toa maelezo yenye manufaa, uliza ufafanuzi pale tu inapohitajika. Usijifanye una taarifa za sasa au uwezo ambao huna.")));
            JSONObject body = new JSONObject()
                    .put("systemInstruction", system)
                    .put("contents", contents)
                    .put("generationConfig", new JSONObject()
                            .put("temperature", 0.7)
                            .put("maxOutputTokens", 1200));
            try (OutputStream out = connection.getOutputStream()) {
                out.write(body.toString().getBytes(StandardCharsets.UTF_8));
            }
            int code = connection.getResponseCode();
            InputStream stream = code >= 200 && code < 300
                    ? connection.getInputStream() : connection.getErrorStream();
            StringBuilder response = new StringBuilder();
            try (BufferedReader reader = new BufferedReader(new InputStreamReader(stream, StandardCharsets.UTF_8))) {
                String line;
                while ((line = reader.readLine()) != null) response.append(line);
            }
            JSONObject json = new JSONObject(response.toString());
            if (code < 200 || code >= 300) {
                String detail = json.optJSONObject("error") != null
                        ? json.getJSONObject("error").optString("message", "HTTP " + code) : "HTTP " + code;
                throw new Exception("Gemini API (" + code + "): " + detail);
            }
            JSONArray candidates = json.optJSONArray("candidates");
            if (candidates == null || candidates.length() == 0) throw new Exception("Gemini haikurudisha jibu.");
            JSONObject candidate = candidates.getJSONObject(0);
            JSONObject content = candidate.optJSONObject("content");
            JSONArray parts = content == null ? null : content.optJSONArray("parts");
            StringBuilder answer = new StringBuilder();
            if (parts != null) for (int i = 0; i < parts.length(); i++)
                answer.append(parts.getJSONObject(i).optString("text", ""));
            if (answer.toString().trim().isEmpty()) throw new Exception("Jibu la Gemini halikuwa na maandishi.");
            return answer.toString().trim();
        } finally {
            if (connection != null) connection.disconnect();
        }
    }

    private String friendlyError(Exception e) {
        String message = e.getMessage() == null ? "Hitilafu haijajulikana." : e.getMessage();
        if (message.contains("API_KEY_INVALID") || message.contains("API key not valid"))
            return "API key si sahihi. Hakiki key yako ya Google AI Studio.";
        if (message.contains("429") || message.contains("RESOURCE_EXHAUSTED"))
            return "Kikomo cha matumizi ya Gemini kimefikiwa. Subiri kidogo au kagua quota/billing.";
        if (message.contains("UnknownHost") || message.contains("Unable to resolve host"))
            return "Hakuna intaneti. Unganisha simu kwenye mtandao kisha jaribu tena.";
        return "Imeshindikana kupata jibu: " + message;
    }

    private void appendChat(String speaker, String message) {
        conversation.append("\n" + speaker + ": " + message + "\n");
    }

    private void startListening() {
        if (checkSelfPermission(Manifest.permission.RECORD_AUDIO) != PackageManager.PERMISSION_GRANTED) {
            requestPermissions(new String[]{Manifest.permission.RECORD_AUDIO}, REQUEST_MIC);
            return;
        }
        launchRecognizer();
    }

    private void launchRecognizer() {
        Intent intent = new Intent(RecognizerIntent.ACTION_RECOGNIZE_SPEECH);
        intent.putExtra(RecognizerIntent.EXTRA_LANGUAGE_MODEL, RecognizerIntent.LANGUAGE_MODEL_FREE_FORM);
        intent.putExtra(RecognizerIntent.EXTRA_LANGUAGE, "sw-TZ");
        intent.putExtra(RecognizerIntent.EXTRA_PROMPT, "Zungumza Kiswahili");
        try { startActivityForResult(intent, REQUEST_SPEECH); }
        catch (Exception e) { setStatus("Huduma ya kutambua sauti haipatikani kwenye simu hii."); }
    }

    @Override public void onRequestPermissionsResult(int requestCode, String[] permissions, int[] results) {
        super.onRequestPermissionsResult(requestCode, permissions, results);
        if (requestCode == REQUEST_MIC && results.length > 0 && results[0] == PackageManager.PERMISSION_GRANTED)
            launchRecognizer();
        else if (requestCode == REQUEST_MIC) setStatus("Ruhusa ya microphone imekataliwa.");
    }

    @Override protected void onActivityResult(int requestCode, int resultCode, Intent data) {
        super.onActivityResult(requestCode, resultCode, data);
        if (requestCode == REQUEST_SPEECH && resultCode == RESULT_OK && data != null) {
            ArrayList<String> matches = data.getStringArrayListExtra(RecognizerIntent.EXTRA_RESULTS);
            if (matches != null && !matches.isEmpty()) {
                input.setText(matches.get(0));
                sendMessage();
            } else setStatus("Hakuna maneno yaliyotambuliwa.");
        }
    }

    private void setStatus(String message) { if (status != null) status.setText(message); }

    @Override protected void onDestroy() {
        executor.shutdownNow();
        if (tts != null) { tts.stop(); tts.shutdown(); }
        super.onDestroy();
    }
}
