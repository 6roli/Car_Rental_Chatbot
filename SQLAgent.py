from langchain_community.tools.sql_database.tool import (

InfoSQLDatabaseTool,

ListSQLDatabaseTool,

QuerySQLDataBaseTool,

)

from langchain_community.utilities import SQLDatabase

from langchain_core.prompts import ChatPromptTemplate


from typing import Annotated, Optional

from langchain_groq import ChatGroq

from pydantic import BaseModel
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
from state import State
from memory import memory_obj
from langchain_core.messages import ToolMessage
load_dotenv()
groq_api_key=os.getenv("GROQ_API_KEY")
db = SQLDatabase.from_uri("sqlite:///cars_schema.db")
llm = ChatGroq(temperature=0, groq_api_key=groq_api_key, model_name="mixtral-8x7b-32768")

list_tool = ListSQLDatabaseTool(db=db)
info_tool = InfoSQLDatabaseTool(db=db)
query_tool = QuerySQLDataBaseTool(db=db)

def list_tables_tool_call(state: State):
    message=AIMessageChunk(content=list_tool.invoke(""))
    return {"messages": [message]}


def info_schema(state: State):
    message=AIMessageChunk(content=info_tool.invoke(state["messages"][-1].content))

    return {"messages": [message]}


tools=[query_tool]
tools_by_name = {tool.name: tool for tool in tools}
def query_tool_node(state: dict):
    result = []
    for tool_call in state["messages"][-1].tool_calls:
        tool = tools_by_name[tool_call["name"]]
        observation = tool.invoke(tool_call["args"])
    if observation:
        result.append(ToolMessage(content=observation, tool_call_id=tool_call["id"]))
    memory_obj.car_list=result [:]  
    if not observation:
        observation=("No cars found in the database matching the preferences.")
        result.append(AIMessage(content=observation))
    return {"messages": result}
#query_tool_node = ToolNode(tools=[query_tool])

            

description = """You are an SQLite expert. Generate a valid SQL query based on the user's input. YOU
MUST USE QuerySQLDataBaseTool and return the result.

You should:

-LIMIT 20.
-Be aware with case sensitive situations 
-If the user says 'today' --> query : SELECT * FROM cars WHERE location = 'Barcelona' AND date_available = DATE('now');
-Queries should be either for 2024 or 2025

Take these CORRECT SQL commands for dates for inspiration:
- SELECT * FROM cars WHERE date_available = '2025-01-17' LIMIT 20;
- SELECT * FROM cars WHERE date_available >= 2025/01/17 LIMIT 20;
- SELECT * FROM cars WHERE date_available = date('now', '+1 day') LIMIT 20;
- SELECT * FROM cars WHERE strftime('%m', date_available) = '02' LIMIT 20;

Take these correct SQL commands for location:
-SELECT * FROM cars WHERE location = 'Bilbao' LIMIT 20
    (Please note that the words inside the '' start with a capital letter.)



If you need to check availability for a certain month (example: January), take this SQL command example:
- SELECT * FROM cars where date_available>='2025-01-01' LIMIT 10

"""

prompt = ChatPromptTemplate.from_messages(

    [("system", description), ("human", "{messages}")])


def query_agent(state: State):

    llm_with_tool = llm.bind_tools([query_tool])

    prompted_llm = prompt | llm_with_tool

    query=prompted_llm.invoke(state)

    return{"messages":[query]}
    


