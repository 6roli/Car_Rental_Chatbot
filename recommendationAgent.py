import json
from typing import Annotated, Literal, TypedDict

from langchain_groq import ChatGroq
from langchain_core.tools import tool
from langgraph.graph import END, START, StateGraph, MessagesState
from langgraph.prebuilt import ToolNode
from langchain_core.prompts import ChatPromptTemplate
from langgraph.graph.message import AnyMessage, add_messages

import os
from dotenv import load_dotenv

from memory import memory_obj
from state import State

load_dotenv()

llm=ChatGroq(temperature=0, model_name="llama-3.3-70b-versatile")
system="""
        You are a helpful worker from a car rental company.
        ********************************************************
        IMPORTANT!!!!! TOOL USAGE INDICATIONS:
        ONLY CALL THE TOOL TO SEARCH FOR WEATHER FORECAST PURPOSES. 
        *********************************************************
        Based on the cars you have available, recommend a car that fits the user's preferences.
        User preferences can include color, price, fuel efficiency, type of drive.....

        The cars you have available follow the following format:
        Make,Model,Year,Price per day, availability date, location,color.

        Please do not get confused with the values.
        Please DOUBLE CHECK, when saying the cheapest and most expensive cars.
        

             
        """
prompt=ChatPromptTemplate.from_messages(
    [
        ("system",system),
        ("system","{car_list}"),
        ("human","{messages}"),
    ]
)

from langchain_community.tools.tavily_search import TavilySearchResults
tavily_api_key=os.getenv("TAVILY_API_KEY")
tavily_tool=TavilySearchResults(max_results=1)
toolkit=[tavily_tool]

chain=prompt|llm.bind_tools(toolkit)
chain2=prompt|llm
def recommendationAgent(state:State):
    
    return{"messages":chain.invoke({"messages":state["messages"],"car_list":memory_obj.car_list})}


from langchain_core.messages import ToolMessage
tools_by_name = {tool.name: tool for tool in toolkit}

def search_tool_node(state:State):
    """Tool to look up the weather forecast"""
    result=[]
    for tool_call in state["messages"][-1].tool_calls:
        tool_result = tools_by_name[tool_call["name"]].invoke(tool_call["args"])
        result.append(
            ToolMessage(
                content=json.dumps(tool_result),
                name=tool_call["name"],
                tool_call_id=tool_call["id"],
            )
        )
    return {"messages": result}

    # Define the conditional edge that determines whether to continue or not
def should_continue(state: State):
    messages = state["messages"]
    last_message = messages[-1]
    # If there is no function call, then we finish
    if not last_message.tool_calls:
        return "end"
    # Otherwise if there is, we continue
    else:
        return "continue"

