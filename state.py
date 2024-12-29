from langchain_community.tools.sql_database.tool import (

InfoSQLDatabaseTool,

ListSQLDatabaseTool,

QuerySQLDataBaseTool,

)

from langchain_community.utilities import SQLDatabase

from langchain_core.prompts import ChatPromptTemplate


from typing import Annotated

from langchain_groq import ChatGroq

from typing_extensions import TypedDict

from langgraph.graph import END, StateGraph, START

from langgraph.graph.message import AnyMessage, add_messages

from langgraph.prebuilt import ToolNode

from langchain_core.messages import (
    AIMessage,
    HumanMessage,
    SystemMessage,
    AIMessageChunk,
    filter_messages,
)
from typing import Literal
from dotenv import load_dotenv
import os

class State(TypedDict):
    messages:Annotated[list[AnyMessage],add_messages]
    next:str
    car_list:list


