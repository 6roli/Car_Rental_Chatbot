from typing import Annotated, List, Literal, TypedDict

from langchain_groq import ChatGroq
from langchain_core.tools import tool
from langgraph.graph import END, START, StateGraph, MessagesState
from langgraph.prebuilt import ToolNode
from langchain_core.prompts import ChatPromptTemplate
from langgraph.graph.message import AnyMessage, add_messages

import os
from dotenv import load_dotenv
from pydantic import BaseModel

from memory import memory_obj
from state import State


load_dotenv()

llm=ChatGroq(temperature=0, model_name="mixtral-8x7b-32768")

system="""You will receive a list of Available cars and need to organise each car into the following format:
    -ID: id_value
    -Make: make_value
    -Model: model_value
    -Year: year_value
    -Price: price_value
    -Availability date: date_value
    -Location: location_value
    -Color: color_value

    Please show the key and value for each car. 
    Present it in a neat way.

    NOTE:
    If you did not find any cars please tell the user:
    -You did not find any cars for the dates and location provided.
    -Tell them to Send 'reset' to try other DATES or Locations.
    """

prompt=ChatPromptTemplate.from_messages([
    ("system",system),
    ("placeholder","{messages}")
])




from pydantic import BaseModel
from typing import List
from datetime import date

# Define the schema for a single car
class Car(BaseModel):
    id: int
    make: str
    model: str
    year: int
    price: float
    availability_date: date
    location: str
    color: str

# Define the schema for a list of cars
class CarList(BaseModel):
    cars: List[Car]

chain=prompt|llm
chain_with_structured_output=prompt|llm.with_structured_output(CarList)
def displayAgent(state: State):
    
    result=chain.invoke(state)
    return{"messages":[result]}