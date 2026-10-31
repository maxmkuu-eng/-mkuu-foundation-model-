package tz.mkuu.foundationchat

import android.app.Activity
import android.graphics.Color
import android.os.Bundle
import android.view.Gravity
import android.view.ViewGroup
import android.widget.Button
import android.widget.EditText
import android.widget.LinearLayout
import android.widget.ScrollView
import android.widget.TextView
import org.json.JSONArray
import org.json.JSONObject
import java.net.HttpURLConnection
import java.net.URL
import java.nio.charset.StandardCharsets
import java.util.concurrent.Executors

class MainActivity : Activity() {
    private val executor = Executors.newSingleThreadExecutor()
    private val conversation = mutableListOf<Pair<String, String>>()
    private lateinit var apiUrl: EditText
    private lateinit var apiToken: EditText
    private lateinit var messageInput: EditText
    private lateinit var transcript: TextView
    private lateinit var status: TextView
    private lateinit var sendButton: Button
    private val prefs by lazy { getSharedPreferences("mkuu_chat", MODE_PRIVATE) }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        buildScreen()
    }

    private fun buildScreen() {
        val root = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            setPadding(dp(16), dp(14), dp(16), dp(12))
            setBackgroundColor(Color.rgb(248, 250, 252))
        }
        root.addView(TextView(this).apply {
            text = "MKUU AI"
            textSize = 25f
            setTextColor(Color.rgb(18, 44, 75))
            gravity = Gravity.CENTER_VERTICAL
        }, matchWrap())
        root.addView(TextView(this).apply {
            text = "Foundation Model • Internet chat pilot"
            textSize = 13f
            setTextColor(Color.DKGRAY)
        }, matchWrap())

        apiUrl = EditText(this).apply {
            hint = "Colab API URL (https://....trycloudflare.com)"
            textSize = 14f
            setSingleLine(true)
            setText(prefs.getString("api_url", ""))
        }
        root.addView(apiUrl, matchWrap())

        apiToken = EditText(this).apply {
            hint = "Access token kutoka Colab"
            textSize = 14f
            setSingleLine(true)
            setText(prefs.getString("api_token", ""))
        }
        root.addView(apiToken, matchWrap())

        status = TextView(this).apply {
            text = "Weka API URL na access token kutoka Colab ili kuunganisha."
            textSize = 12f
            setTextColor(Color.rgb(70, 90, 110))
            setPadding(0, dp(5), 0, dp(5))
        }
        root.addView(status, matchWrap())

        val scroll = ScrollView(this)
        transcript = TextView(this).apply {
            text = "Karibu MKUU AI. Andika ujumbe wako hapa chini."
            textSize = 16f
            setTextColor(Color.rgb(25, 35, 48))
            setPadding(dp(10), dp(12), dp(10), dp(12))
        }
        scroll.addView(transcript)
        root.addView(scroll, LinearLayout.LayoutParams(
            ViewGroup.LayoutParams.MATCH_PARENT, 0, 1f
        ))

        messageInput = EditText(this).apply {
            hint = "Andika ujumbe..."
            textSize = 16f
            minLines = 1
            maxLines = 4
        }
        root.addView(messageInput, matchWrap())

        sendButton = Button(this).apply {
            text = "Tuma ujumbe"
            setOnClickListener { sendMessage() }
        }
        root.addView(sendButton, matchWrap())
        setContentView(root)
    }

    private fun sendMessage() {
        val message = messageInput.text.toString().trim()
        val baseUrl = apiUrl.text.toString().trim().trimEnd('/')
        val token = apiToken.text.toString().trim()
        if (message.isEmpty()) {
            status.text = "Andika ujumbe kwanza."
            return
        }
        if (!baseUrl.startsWith("https://")) {
            status.text = "Weka URL sahihi ya HTTPS kutoka Colab."
            return
        }
        prefs.edit().putString("api_url", baseUrl).putString("api_token", token).apply()
        val previous = conversation.toList()
        conversation.add("user" to message)
        appendTranscript("Wewe", message)
        messageInput.setText("")
        sendButton.isEnabled = false
        status.text = "MKUU anatafuta taarifa mtandaoni na kuandaa jibu..."
        executor.execute {
            try {
                val response = postChat(baseUrl, token, message, previous)
                val reply = response.optString("reply", "Hakuna jibu lililopokelewa.")
                val sources = response.optJSONArray("sources") ?: JSONArray()
                conversation.add("assistant" to reply)
                runOnUiThread {
                    appendTranscript("MKUU AI", reply)
                    if (sources.length() > 0) {
                        val lines = StringBuilder("\n\nVyanzo vya mtandao:\n")
                        for (i in 0 until sources.length()) {
                            val item = sources.optJSONObject(i) ?: continue
                            lines.append("• ").append(item.optString("title"))
                                .append("\n").append(item.optString("url")).append("\n")
                        }
                        appendTranscript("VYANZO", lines.toString())
                    }
                    status.text = "Imeunganishwa • ${response.optString("model", "MKUU")}"
                    sendButton.isEnabled = true
                }
            } catch (error: Exception) {
                runOnUiThread {
                    status.text = "Imeshindikana: ${error.message ?: "tatizo la connection"}"
                    sendButton.isEnabled = true
                }
            }
        }
    }

    private fun postChat(
        baseUrl: String,
        token: String,
        message: String,
        history: List<Pair<String, String>>
    ): JSONObject {
        val connection = (URL("$baseUrl/chat").openConnection() as HttpURLConnection).apply {
            requestMethod = "POST"
            connectTimeout = 20000
            readTimeout = 180000
            doOutput = true
            setRequestProperty("Content-Type", "application/json; charset=utf-8")
            if (token.isNotEmpty()) setRequestProperty("Authorization", "Bearer $token")
        }
        val historyJson = JSONArray()
        history.takeLast(4).forEach { (role, content) ->
            historyJson.put(JSONObject().put("role", role).put("content", content))
        }
        val body = JSONObject()
            .put("message", message)
            .put("history", historyJson)
            .put("max_new_tokens", 128)
            .toString()
        try {
            connection.outputStream.use {
                it.write(body.toByteArray(StandardCharsets.UTF_8))
            }
            val code = connection.responseCode
            val stream = if (code in 200..299) connection.inputStream else connection.errorStream
            val responseText = stream.bufferedReader().use { it.readText() }
            if (code !in 200..299) {
                val detail = try { JSONObject(responseText).optString("detail", responseText) }
                    catch (_: Exception) { responseText }
                throw IllegalStateException("HTTP $code: $detail")
            }
            return JSONObject(responseText)
        } finally {
            connection.disconnect()
        }
    }

    private fun appendTranscript(speaker: String, message: String) {
        transcript.append("\n\n$speaker\n$message")
    }

    private fun dp(value: Int): Int = (value * resources.displayMetrics.density).toInt()

    private fun matchWrap() = LinearLayout.LayoutParams(
        ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.WRAP_CONTENT
    )

    override fun onDestroy() {
        executor.shutdown()
        super.onDestroy()
    }
}
