"""The agents and the two LangGraph workflows.

1. Search workflow  (one pass per message until cars are found)
       extract_criteria (LLM) → check_criteria (Python) → search_inventory (Python SQL)

   The model only turns free text into structured criteria. Validation, the SQL
   query and the list formatting are plain Python: cheaper, faster and they cannot
   invent cars or write a wrong query.

2. Conversation workflow  (after cars are found)
       supervisor (LLM router) → recommendation (LLM, optional weather search)
                               → booking (LLM, simulated)

Every visitor has their own LangGraph thread, so conversations never mix.
"""

from datetime import date, timedelta
from typing import Annotated, Literal, TypedDict

from langchain_core.messages import AnyMessage, SystemMessage
from langchain_core.tools import BaseTool
from langchain_groq import ChatGroq
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import END, START, StateGraph
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode, tools_condition
from pydantic import BaseModel, Field

from .config import Settings
from .inventory import LOCATIONS, Car, match_location, search_cars
from .models import ModelChoice, model_options

# --------------------------------------------------------------------------- models


def make_llm(settings: Settings, model: str) -> ChatGroq:
    if not settings.groq_api_key:
        raise RuntimeError("GROQ_API_KEY is not set")
    # One retry only: on a rate limit we prefer telling the visitor quickly.
    return ChatGroq(
        model=model, temperature=0, api_key=settings.groq_api_key, max_retries=1, timeout=45, **model_options(model)
    )


# --------------------------------------------------------------------- 1. search


class SearchCriteria(BaseModel):
    """What the visitor is looking for, extracted from their message."""

    location: str | None = Field(None, description="City where the car is picked up, as written by the user")
    start_date: date | None = Field(None, description="First day of the rental (YYYY-MM-DD)")
    end_date: date | None = Field(None, description="Last day of the rental (YYYY-MM-DD); same as start for one day")
    max_price_per_day: float | None = Field(None, description="Maximum price per day in euros, if mentioned")


class SearchState(TypedDict, total=False):
    message: str
    today: date
    last_day: date
    criteria: SearchCriteria
    problems: list[str]
    cars: list[Car]


EXTRACTION_PROMPT = """You extract car rental search criteria from the user's message.
Today is {today} ({weekday}). Resolve relative dates ("tomorrow", "next weekend", "in March")
to exact dates on or after today. If only a month is given, use its first and last day.
If only one day is given, use it as both start and end. Leave fields empty when not mentioned.
Copy the city exactly as the user wrote it, even if it is not one of our pickup cities ({locations});
another step checks it."""


def build_search_graph(settings: Settings, models: ModelChoice, connection_provider):
    """`connection_provider()` returns today's inventory connection."""
    extractor = make_llm(settings, models.fast).with_structured_output(SearchCriteria)

    def extract_criteria(state: SearchState) -> SearchState:
        today = state["today"]
        system = EXTRACTION_PROMPT.format(today=today.isoformat(), weekday=today.strftime("%A"), locations=", ".join(LOCATIONS))
        criteria = extractor.invoke([SystemMessage(system), ("user", state["message"])])
        return {"criteria": criteria}

    def check_criteria(state: SearchState) -> SearchState:
        return {"problems": validate_criteria(state["criteria"], state["today"], state["last_day"])}

    def search_inventory(state: SearchState) -> SearchState:
        criteria = state["criteria"]
        cars = search_cars(
            connection_provider(),
            match_location(criteria.location),  # validated above
            criteria.start_date,
            criteria.end_date or criteria.start_date,
            criteria.max_price_per_day,
        )
        return {"cars": cars}

    graph = StateGraph(SearchState)
    graph.add_node("extract_criteria", extract_criteria)
    graph.add_node("check_criteria", check_criteria)
    graph.add_node("search_inventory", search_inventory)
    graph.add_edge(START, "extract_criteria")
    graph.add_edge("extract_criteria", "check_criteria")
    graph.add_conditional_edges(
        "check_criteria", lambda state: "invalid" if state["problems"] else "valid", {"invalid": END, "valid": "search_inventory"}
    )
    graph.add_edge("search_inventory", END)
    return graph.compile()


def validate_criteria(criteria: SearchCriteria, today: date, last_day: date) -> list[str]:
    """Human-readable problems with the request; empty when it can be searched."""
    problems = []
    if not criteria.location:
        problems.append(f"Tell me the pickup city ({', '.join(LOCATIONS)}).")
    elif not match_location(criteria.location):
        problems.append(f"We don't operate in {criteria.location}. Available cities: {', '.join(LOCATIONS)}.")
    if not criteria.start_date:
        problems.append("Tell me the dates (for example: 'from 3 to 7 March' or 'next weekend').")
    else:
        end = criteria.end_date or criteria.start_date
        if criteria.start_date < today:
            problems.append(f"The start date {criteria.start_date.isoformat()} is in the past.")
        if end < criteria.start_date:
            problems.append("The end date is before the start date.")
        if end > last_day:
            problems.append(f"This demo has availability up to {last_day.isoformat()}.")
    return problems


def format_cars(cars: list[Car]) -> str:
    return "\n".join(f"• {car.describe()}" for car in cars)


# --------------------------------------------------------------- 2. conversation


class ChatState(TypedDict):
    messages: Annotated[list[AnyMessage], add_messages]
    car_list: str
    next: str


class Route(BaseModel):
    """Which agent should answer."""

    next: Literal["recommendation", "booking"] = Field(
        description="'booking' if the user wants to book or gives a name, phone or email; otherwise 'recommendation'"
    )


SUPERVISOR_PROMPT = """You route messages for a car rental assistant.
Choose 'booking' if the user wants to book or reserve a car, or provides a name, phone number or email.
Choose 'recommendation' for questions, comparisons or advice about the cars."""

RECOMMENDATION_PROMPT = """You are a friendly assistant of a car rental company (a portfolio demo with a fictional fleet).
Recommend cars ONLY from this list of available cars, quoting their # number. Never invent cars or prices.
Double-check prices when talking about the cheapest or most expensive options.
Write plain text without Markdown (no asterisks or # headings); use '- ' for lists. Keep answers short.
{tool_hint}
Available cars:
{car_list}"""

BOOKING_PROMPT = """You are a friendly assistant of a car rental company. This is a PORTFOLIO DEMO with a fictional fleet:
no real booking is ever made and nothing is stored.
Help the user choose one car from the list (by its # number) and ask for a name and an email or phone number.
Always remind them, briefly, to use made-up details, not real personal data.
When you have a car and contact details, confirm a SIMULATED booking with a short summary and say no real booking was made.
Write plain text without Markdown (no asterisks or # headings); use '- ' for lists. Keep answers short.
Available cars:
{car_list}"""


def build_chat_graph(settings: Settings, models: ModelChoice, tools: list[BaseTool]):
    router = make_llm(settings, models.fast).with_structured_output(Route)
    main_llm = make_llm(settings, models.main)
    recommender = main_llm.bind_tools(tools) if tools else main_llm
    tool_hint = (
        "If the user asks about the weather at the destination, you may use the web search tool once."
        if tools
        else "You cannot look up the weather; say so if asked."
    )

    def supervisor(state: ChatState) -> dict:
        route = router.invoke([SystemMessage(SUPERVISOR_PROMPT), state["messages"][-1]])
        return {"next": route.next}

    def recommendation(state: ChatState) -> dict:
        system = RECOMMENDATION_PROMPT.format(tool_hint=tool_hint, car_list=state["car_list"])
        return {"messages": [recommender.invoke([SystemMessage(system), *state["messages"][-12:]])]}

    def booking(state: ChatState) -> dict:
        system = BOOKING_PROMPT.format(car_list=state["car_list"])
        return {"messages": [main_llm.invoke([SystemMessage(system), *state["messages"][-12:]])]}

    graph = StateGraph(ChatState)
    graph.add_node("supervisor", supervisor)
    graph.add_node("recommendation", recommendation)
    graph.add_node("booking", booking)
    graph.add_edge(START, "supervisor")
    graph.add_conditional_edges("supervisor", lambda state: state["next"], {"recommendation": "recommendation", "booking": "booking"})
    if tools:
        graph.add_node("tools", ToolNode(tools))
        graph.add_conditional_edges("recommendation", tools_condition, {"tools": "tools", END: END})
        graph.add_edge("tools", "recommendation")
    else:
        graph.add_edge("recommendation", END)
    graph.add_edge("booking", END)
    # In-memory checkpoints: conversation history per thread, lost on restart (fine for a demo).
    return graph.compile(checkpointer=InMemorySaver())


def make_tools(settings: Settings) -> list[BaseTool]:
    """Weather search via Tavily, only when a TAVILY_API_KEY is configured."""
    if not settings.tavily_api_key:
        return []
    from langchain_tavily import TavilySearch

    return [TavilySearch(max_results=1, tavily_api_key=settings.tavily_api_key)]


def availability_window(today: date, settings: Settings) -> date:
    return today + timedelta(days=settings.demo_days_ahead)
