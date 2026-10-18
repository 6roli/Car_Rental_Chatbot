"""Flask web server: the chat page and a small JSON API.

Run locally:  flask --app car_rental.web run
On Render:    gunicorn car_rental.web:app  (see render.yaml)
"""

import logging
import os
from datetime import datetime

from flask import Flask, jsonify, render_template, request, session

from .assistant import WELCOME, Assistant
from .config import settings

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
log = logging.getLogger(__name__)

app = Flask(__name__)
app.config.update(
    SECRET_KEY=settings.flask_secret_key,
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE="Lax",
    # Render serves over HTTPS; locally Flask runs on plain http.
    SESSION_COOKIE_SECURE=bool(os.getenv("RENDER")),
    MAX_CONTENT_LENGTH=16 * 1024,
)
assistant = Assistant(settings)

PORTFOLIO_URL = os.getenv("PORTFOLIO_URL", "https://portfolio.gabriel-olius.workers.dev/projects/car-rental-chatbot/")


@app.after_request
def security_headers(response):
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Content-Security-Policy"] = (
        "default-src 'self'; style-src 'self' 'unsafe-inline'; script-src 'self'; frame-ancestors 'none'"
    )
    return response


@app.get("/")
def home():
    return render_template("index.html", welcome=WELCOME, configured=assistant.configured, portfolio_url=PORTFOLIO_URL)


@app.get("/health")
def health():
    return {"status": "ok", "configured": assistant.configured, "active_sessions": len(assistant.sessions)}


@app.post("/chat")
def chat():
    payload = request.get_json(silent=True) or {}
    message = payload.get("message")
    if not isinstance(message, str) or not message.strip():
        return jsonify(error="Please type a message."), 400
    if len(message) > settings.max_message_length:
        return jsonify(error=f"Messages are limited to {settings.max_message_length} characters."), 400
    if not assistant.configured:
        return jsonify(error="The demo is not configured yet (missing GROQ_API_KEY on the server)."), 503

    visitor = assistant.sessions.get_or_create(session.get("sid"), now=_now())
    session["sid"] = visitor.id
    refusal = assistant.limiter.check(visitor, _now())
    if refusal:
        return jsonify(error=refusal), 429

    try:
        return jsonify(reply=assistant.reply(visitor, message))
    except Exception as error:  # noqa: BLE001 — every failure becomes a friendly message
        return _friendly_error(error)


def _friendly_error(error: Exception):
    name = type(error).__name__
    # Groq's free quota is shared by all visitors; when exhausted it answers 429.
    if name == "RateLimitError" or "rate limit" in str(error).lower():
        log.warning("Groq rate limit reached: %s", error)
        return jsonify(error="The AI service is busy or today's free quota is used up. Please try again in a few minutes."), 503
    if name in {"APITimeoutError", "APIConnectionError"}:
        log.warning("Groq unreachable: %s", error)
        return jsonify(error="The AI service did not answer in time. Please try again."), 503
    log.exception("Unexpected error")
    return jsonify(error="Something went wrong on our side. Please try again, or send 'reset'."), 500


def _now() -> datetime:
    return datetime.now()
