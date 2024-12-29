
from typing import Literal, TypedDict
from state import State
from langchain_groq import ChatGroq

llm=ChatGroq(temperature=0)

system="""You are a worker from a car rental company.
Based on the user input you have to decide if the user wants to get a car
recommendation or if he wants to book a car.

Return "recommendationAgent" for recommendation purposes.
Return "bookingAgent" for booking purposes.

IMPORTANT NOTES: 
-If the user types in a name  --> redirect to "bookingAgent"
-If the user types in a phone number --> redirect to "bookingAgent"
"""

class Router(TypedDict):
    next:Literal["recommendationAgent","bookingAgent"]

from langchain_core.prompts import ChatPromptTemplate

prompt=ChatPromptTemplate.from_messages(
    [
        ("system",system),
        ("human","{messages}")
    ]
)

chain=prompt|llm.with_structured_output(Router)

def supervisor_node(state:State):
    human_input=state["messages"][-1]
    response=chain.invoke({"messages":human_input})
    next_=response["next"]
    return{"next":next_}

    
# def supervisor_node(state:State):
#     messages = [
#         {"role": "system", "content": system},
#     ] + state["messages"]
#     response=llm.with_structured_output(Router).invoke(messages)
#     next_=response["next"]
#     return{"next":next_}


#TEST--------------
# from langchain_core.messages import HumanMessage
# state={"messages":HumanMessage(content="I want a car suitable for the weather")}

# result=supervisor_node(state)

# print(result)