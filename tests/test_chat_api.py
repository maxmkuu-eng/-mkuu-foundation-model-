from api.server import HistoryMessage, build_prompt, search_web


def test_build_prompt_includes_search_sources_and_recent_history():
    history = [HistoryMessage(role="user", content="Habari")]
    sources = [{
        "title": "Taarifa rasmi",
        "url": "https://example.org/news",
        "snippet": "Maelezo ya mfano",
    }]
    prompt = build_prompt("Nini kimetokea?", history, sources)
    assert "<|system|>" in prompt
    assert "<|user|>\nHabari" in prompt
    assert "Nini kimetokea?" in prompt
    assert "[1] Taarifa rasmi" in prompt
    assert "https://example.org/news" in prompt


def test_search_web_extracts_result_title_url_and_snippet(monkeypatch):
    class FakeResponse:
        text = (
            '<div class="result">'
            '<a class="result__a" href="https://example.org/page">Habari mpya</a>'
            '<a class="result__snippet">Maelezo ya taarifa</a>'
            '</div>'
        )

        def raise_for_status(self):
            return None

    monkeypatch.setattr("api.server.requests.get", lambda *args, **kwargs: FakeResponse())
    results = search_web("swahili news")
    assert results == [{
        "title": "Habari mpya",
        "url": "https://example.org/page",
        "snippet": "Maelezo ya taarifa",
    }]
