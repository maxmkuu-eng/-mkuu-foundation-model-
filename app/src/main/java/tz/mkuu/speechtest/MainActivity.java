package tz.mkuu.speechtest;

import android.Manifest;
import android.app.Activity;
import android.content.Intent;
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
import java.util.ArrayList;
import java.util.Locale;

public class MainActivity extends Activity {
    private static final int REQUEST_SPEECH = 41;
    private static final int REQUEST_MIC = 42;
    private EditText input;
    private TextView status;
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
                setStatus(ttsReady
                    ? "TTS tayari. Sauti ya Kiswahili imepatikana kwenye simu."
                    : "TTS imewashwa, lakini sauti ya Kiswahili haipo kwenye simu. Angalia Text-to-speech settings.");
            } else {
                setStatus("Imeshindikana kuanzisha Text-to-Speech kwenye simu hii.");
            }
        });
    }

    private void buildUi() {
        LinearLayout page = new LinearLayout(this);
        page.setOrientation(LinearLayout.VERTICAL);
        page.setPadding(24, 28, 24, 20);
        page.setBackgroundColor(0xFFF7FAFC);

        TextView title = new TextView(this);
        title.setText("MKUU AI — Speech Test");
        title.setTextSize(24);
        title.setTextColor(0xFF102A43);
        title.setGravity(Gravity.CENTER);
        page.addView(title, new LinearLayout.LayoutParams(-1, -2));

        TextView note = new TextView(this);
        note.setText("Jaribio la sauti na maandishi kwenye Android. Hii bado si model ya mazungumzo iliyofunzwa.");
        note.setTextSize(14);
        note.setTextColor(0xFF486581);
        note.setPadding(0, 12, 0, 20);
        page.addView(note);

        input = new EditText(this);
        input.setHint("Andika Kiswahili hapa...");
        input.setText("Habari! Karibu kwenye jaribio la sauti la MKUU AI.");
        input.setMinLines(4);
        input.setGravity(Gravity.TOP | Gravity.START);
        page.addView(input, new LinearLayout.LayoutParams(-1, 0, 1));

        Button speak = new Button(this);
        speak.setText("Soma maandishi kwa sauti");
        speak.setOnClickListener(v -> {
            String text = input.getText().toString().trim();
            if (text.isEmpty()) { setStatus("Andika maandishi kwanza."); return; }
            if (ttsReady) {
                tts.speak(text, TextToSpeech.QUEUE_FLUSH, null, "mkuu-test-utterance");
                setStatus("Inasoma maandishi kwa sauti...");
            } else {
                setStatus("Sauti ya Kiswahili haijapatikana. Kagua mipangilio ya TTS ya simu.");
            }
        });
        page.addView(speak, new LinearLayout.LayoutParams(-1, -2));

        Button stop = new Button(this);
        stop.setText("Simamisha sauti");
        stop.setOnClickListener(v -> {
            if (tts != null) tts.stop();
            setStatus("Sauti imesimamishwa.");
        });
        page.addView(stop, new LinearLayout.LayoutParams(-1, -2));

        Button listen = new Button(this);
        listen.setText("Jaribu kuzungumza (Microphone)");
        listen.setOnClickListener(v -> startListening());
        page.addView(listen, new LinearLayout.LayoutParams(-1, -2));

        status = new TextView(this);
        status.setText("Inaandaa mfumo wa sauti...");
        status.setTextSize(14);
        status.setTextColor(0xFF243B53);
        status.setPadding(0, 18, 0, 0);
        page.addView(status, new LinearLayout.LayoutParams(-1, -2));

        TextView modelStatus = new TextView(this);
        modelStatus.setText("Hali ya language model: HAIPO TAYARI — hakuna trained weights/tokenizer ya kuendesha inference bado.");
        modelStatus.setTextSize(13);
        modelStatus.setTextColor(0xFF9C4221);
        modelStatus.setPadding(0, 12, 0, 0);
        page.addView(modelStatus);

        ScrollView scroll = new ScrollView(this);
        scroll.addView(page);
        setContentView(scroll);
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
        try {
            startActivityForResult(intent, REQUEST_SPEECH);
        } catch (Exception e) {
            setStatus("Huduma ya kutambua sauti haipatikani kwenye simu hii.");
        }
    }

    @Override public void onRequestPermissionsResult(int requestCode, String[] permissions, int[] results) {
        super.onRequestPermissionsResult(requestCode, permissions, results);
        if (requestCode == REQUEST_MIC && results.length > 0 && results[0] == PackageManager.PERMISSION_GRANTED) {
            launchRecognizer();
        } else if (requestCode == REQUEST_MIC) {
            setStatus("Ruhusa ya microphone imekataliwa.");
        }
    }

    @Override protected void onActivityResult(int requestCode, int resultCode, Intent data) {
        super.onActivityResult(requestCode, resultCode, data);
        if (requestCode == REQUEST_SPEECH && resultCode == RESULT_OK && data != null) {
            ArrayList<String> matches = data.getStringArrayListExtra(RecognizerIntent.EXTRA_RESULTS);
            if (matches != null && !matches.isEmpty()) {
                input.setText(matches.get(0));
                setStatus("Sauti imetambuliwa na huduma ya speech recognition ya simu.");
            } else setStatus("Hakuna maneno yaliyotambuliwa.");
        }
    }

    private void setStatus(String message) {
        if (status != null) status.setText(message);
    }

    @Override protected void onDestroy() {
        if (tts != null) { tts.stop(); tts.shutdown(); }
        super.onDestroy();
    }
}
