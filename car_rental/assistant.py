"""Turns one visitor message into one reply, using the right workflow for the session's stage."""

import logging
import threading
from datetime import date, datetime, timedelta

from .agents import availability_window, build_chat_graph, build_search_graph, format_cars, make_tools
from .config import Settings
from .inventory import create_inventory
from .sessions import RateLimiter, Session, SessionStore

log = logging.getLogger(__name__)

RESET_WORDS = {"reset", "restart", "start over", "new search"}

WELCOME = (
    "Hi! Tell me where and when you need a car, for example: "
    "'Barcelona from next Friday to Sunday' or 'a cheap car in Sevilla in December'."
)


class Inventory:
    """Today's fictional fleet, rebuilt automatically when the date changes."""

    def __init__(self, settings: Settings):
        self._settings = settings
        self._day: date | None = None
        self._connection = None
        self._lock = threading.Lock()

    def connection(self, today: date | None = None):
        today = today or date.today()
        with self._lock:
            if self._day != today:
                self._connection = create_inventory(today, self._settings.demo_days_ahead)
                self._day = today
            return self._connection


class Assistant:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.inventory = Inventory(settings)
        self.sessions = SessionStore(ttl=timedelta(minutes=settings.session_ttl_minutes))
        self.limiter = RateLimiter(settings.messages_per_session_per_hour, settings.messages_per_day)
        # Graphs are built lazily so the web page still loads without an API key.
        self._search_graph = None
        self._chat_graph = None

    @property
    def configured(self) -> bool:
        return bool(self.settings.groq_api_key)

    def _graphs(self):
        if self._search_graph is None:
            self._search_graph = build_search_graph(self.settings, self.inventory.connection)
            self._chat_graph = build_chat_graph(self.settings, make_tools(self.settings))
        return self._search_graph, self._chat_graph

    def reply(self, session: Session, message: str, now: datetime | None = None) -> str:
        now = now or datetime.now()
        message = message.strip()
        if message.lower() in RESET_WORDS:
            session.reset()
            return "New search started. " + WELCOME
        if session.stage == "search":
            return self._search(session, message, now.date())
        return self._chat(session, message)

    def _search(self, session: Session, message: str, today: date) -> str:
        search_graph, _ = self._graphs()
        result = search_graph.invoke(
            {"message": message, "today": today, "last_day": availability_window(today, self.settings)}
        )
        if result.get("problems"):
            return "I need a bit more information:\n" + "\n".join(f"• {p}" for p in result["problems"])
        cars = result.get("cars", [])
        criteria = result["criteria"]
        if not cars:
            return (
                f"No cars match in {criteria.location} for those dates. "
                "Try other dates or another city, or send 'reset'."
            )
        session.cars, session.stage = cars, "chat"
        return (
            f"Found {len(cars)} cars (cheapest first):\n{format_cars(cars)}\n\n"
            "Ask me for a recommendation (e.g. 'which is best for a family?') or say which one you want to book. "
            "Send 'reset' to search again."
        )

    def _chat(self, session: Session, message: str) -> str:
        _, chat_graph = self._graphs()
        state = chat_graph.invoke(
            {"messages": [("user", message)], "car_list": format_cars(session.cars)},
            {"configurable": {"thread_id": session.thread_id}},
        )
        return str(state["messages"][-1].content).strip() or "Sorry, I have no answer for that. Could you rephrase it?"
