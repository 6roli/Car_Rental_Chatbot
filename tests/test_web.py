import pytest

from car_rental import web


@pytest.fixture
def client(monkeypatch):
    # Pretend a key is configured, and replace the model-backed reply with a stub.
    monkeypatch.setattr(type(web.assistant), "configured", property(lambda self: True))
    monkeypatch.setattr(web.assistant, "reply", lambda session, message: f"echo:{message}:{session.id[:4]}")
    web.app.config["TESTING"] = True
    return web.app.test_client()


def test_home_page_shows_demo_notice(client):
    page = client.get("/").get_data(as_text=True)
    assert "fleet is fictional" in page
    assert "← Portfolio" in page


def test_chat_replies_and_keeps_the_visitor_session(client):
    first = client.post("/chat", json={"message": "hi"}).get_json()["reply"]
    second = client.post("/chat", json={"message": "again"}).get_json()["reply"]
    assert first.split(":")[2] == second.split(":")[2]  # same session id prefix


def test_chat_rejects_bad_input(client):
    assert client.post("/chat", json={}).status_code == 400
    assert client.post("/chat", json={"message": "   "}).status_code == 400
    assert client.post("/chat", json={"message": "x" * 5000}).status_code == 400


def test_rate_limit_answers_429(client, monkeypatch):
    monkeypatch.setattr(web.assistant.limiter, "check", lambda session, now: "limit reached")
    response = client.post("/chat", json={"message": "hi"})
    assert response.status_code == 429 and response.get_json()["error"] == "limit reached"


def test_model_errors_become_friendly_messages(client, monkeypatch):
    class RateLimitError(Exception):
        pass

    def fail(session, message):
        raise RateLimitError("429 rate limit")

    monkeypatch.setattr(web.assistant, "reply", fail)
    response = client.post("/chat", json={"message": "hi"})
    assert response.status_code == 503 and "quota" in response.get_json()["error"]


def test_security_headers_and_health(client):
    response = client.get("/health")
    assert response.get_json()["status"] == "ok"
    assert "default-src 'self'" in response.headers["Content-Security-Policy"]


def test_missing_model_and_bad_key_have_clear_messages(client, monkeypatch):
    for name, expected in [("NotFoundError", "no longer available"), ("AuthenticationError", "key was rejected")]:
        error_class = type(name, (Exception,), {})

        def fail(session, message, error_class=error_class):
            raise error_class("boom")

        monkeypatch.setattr(web.assistant, "reply", fail)
        response = client.post("/chat", json={"message": "hi"})
        assert response.status_code == 503 and expected in response.get_json()["error"]
