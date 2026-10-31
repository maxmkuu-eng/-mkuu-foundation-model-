package tz.mkuu.foundationchat

import android.app.Activity
import android.graphics.Color
import android.os.Bundle
import android.view.Gravity
import android.view.View
import android.widget.*
import org.json.JSONObject
import java.net.HttpURLConnection
import java.net.URL
import kotlin.concurrent.thread

class MainActivity : Activity() {
    private lateinit var endpoint: EditText
    private lateinit var apiKey: EditText
    private lateinit var input: EditText
    private lateinit var messages: LinearLayout
    private lateinit var scroll: ScrollView
    private lateinit var send: Button
    private val prefs by lazy { getSharedPreferences("mkuu_foundation", MODE_PRIVATE) }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        window.statusBarColor = Color.rgb(245, 249, 255)
        window.navigationBarColor = Color.WHITE
        window.decorView.systemUiVisibility = View.SYSTEM_UI_FLAG_LIGHT_STATUS_BAR
        buildScreen()
        addMessage("MKUU Foundation Model", "Karibu. Weka anwani ya server yako, kisha tuma ujumbe kujaribu model.", false)
    }

    private fun buildScreen() {
        val root = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            setPadding(18, 14, 18, 12)
            setBackgroundColor(Color.rgb(245, 249, 255))
        }
        val title = TextView(this).apply {
            text = "MKUU"
            textSize = 26f
            setTextColor(Color.rgb(20, 57, 100))
            gravity = Gravity.CENTER_VERTICAL
            setPadding(4, 6, 4, 2)
        }
        val subtitle = TextView(this).apply {
            text = "FOUNDATION MODEL • TEST CHAT"
            textSize = 11f
            setTextColor(Color.rgb(76, 112, 151))
            setPadding(4, 0, 4, 8)
        }
        endpoint = EditText(this).apply {
            hint = "Server URL, mfano https://jina.hf.space"
            textSize = 13f
            singleLine = true
            setText(prefs.getString("endpoint", ""))
        }
        apiKey = EditText(this).apply {
            hint = "Test API key (kama imewekwa)"
            textSize = 13f
            singleLine = true
            setText(prefs.getString("api_key", ""))
        }
        val settingsLabel = TextView(this).apply {
            text = "SERVER YA MODEL"
            textSize = 10f
            setTextColor(Color.DKGRAY)
        }
        val settings = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            setPadding(10, 4, 10, 4)
            setBackgroundColor(Color.WHITE)
            addView(settingsLabel)
            addView(endpoint)
            addView(apiKey)
        }
        messages = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            setPadding(2, 12, 2, 12)
        }
        scroll = ScrollView(this).apply {
            isFillViewport = true
            addView(messages)
        }
        input = EditText(this).apply {
            hint = "Andika ujumbe kwa MKUU..."
            textSize = 15f
            minLines = 1
            maxLines = 4
            setPadding(14, 10, 14, 10)
            setBackgroundColor(Color.WHITE)
        }
        send = Button(this).apply {
            text = "TUMA"
            setTextColor(Color.WHITE)
            setBackgroundTintList(android.content.res.ColorStateList.valueOf(Color.rgb(18, 92, 158)))
            setOnClickListener { sendMessage() }
        }
        val composer = LinearLayout(this).apply {
            orientation = LinearLayout.HORIZONTAL
            gravity = Gravity.CENTER_VERTICAL
            addView(input, LinearLayout.LayoutParams(0, -2, 1f))
            addView(send, LinearLayout.LayoutParams(-2, -2))
        }
        root.addView(title)
        root.addView(subtitle)
        root.addView(settings)
        root.addView(scroll, LinearLayout.LayoutParams(-1, 0, 1f))
        root.addView(composer)
        setContentView(root)
    }

    private fun addMessage(label: String, body: String, user: Boolean) {
        val card = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            setPadding(13, 9, 13, 9)
            setBackgroundColor(if (user) Color.rgb(222, 239, 255) else Color.WHITE)
        }
        val who = TextView(this).apply {
            text = label
            textSize = 11f
            setTextColor(Color.rgb(35, 91, 145))
        }
        val text = TextView(this).apply {
            this.text = body
            textSize = 15f
            setTextColor(Color.rgb(28, 39, 52))
            setPadding(0, 4, 0, 0)
        }
        card.addView(who)
        card.addView(text)
        val wrapper = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            setPadding(if (user) 34 else 0, 4, if (user) 0 else 34, 4)
            addView(card)
        }
        messages.addView(wrapper)
        scroll.post { scroll.fullScroll(View.FOCUS_DOWN) }
    }

    private fun sendMessage() {
        val message = input.text.toString().trim()
        val base = endpoint.text.toString().trim().trimEnd('/')
        if (message.isEmpty()) return
        if (!base.startsWith("https://")) {
            Toast.makeText(this, "Weka HTTPS server URL kwanza", Toast.LENGTH_LONG).show()
            return
        }
        prefs.edit().putString("endpoint", base).putString("api_key", apiKey.text.toString().trim()).apply()
        addMessage("WEWE", message, true)
        input.text.clear()
        send.isEnabled = false
        send.text = "..."
        thread {
            var connection: HttpURLConnection? = null
            try {
                connection = (URL("$base/chat").openConnection() as HttpURLConnection).apply {
                    requestMethod = "POST"
                    connectTimeout = 30000
                    readTimeout = 180000
                    doOutput = true
                    setRequestProperty("Content-Type", "application/json; charset=utf-8")
                    val key = apiKey.text.toString().trim()
                    if (key.isNotEmpty()) setRequestProperty("X-Mkuu-Key", key)
                }
                val payload = JSONObject().put("message", message).put("max_new_tokens", 96).toString()
                connection.outputStream.use { it.write(payload.toByteArray(Charsets.UTF_8)) }
                val code = connection.responseCode
                val stream = if (code in 200..299) connection.inputStream else connection.errorStream
                val response = stream.bufferedReader().use { it.readText() }
                val body = JSONObject(response)
                if (code !in 200..299) throw IllegalStateException(body.optString("detail", "HTTP $code"))
                val answer = body.optString("answer", "").ifBlank { "(Model haijatoa maandishi.)" }
                runOnUiThread { addMessage("MKUU FOUNDATION", answer, false) }
            } catch (e: Exception) {
                runOnUiThread { addMessage("TATIZO LA MUUNGANISHO", e.message ?: "Imeshindikana kuwasiliana na server.", false) }
            } finally {
                connection?.disconnect()
                runOnUiThread { send.isEnabled = true; send.text = "TUMA" }
            }
        }
    }
}
