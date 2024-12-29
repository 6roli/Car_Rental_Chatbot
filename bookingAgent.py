


from langchain_core.prompts import ChatPromptTemplate
from langchain_groq import ChatGroq
from dotenv import load_dotenv
import os

load_dotenv()
os.getenv("GROQ_API_KEY")
llm=ChatGroq(temperature=0, model="llama-3.3-70b-versatile")
system="""You are a worker from a car rental company.
Based on the cars you have available, complete the process to book the car the user want.

To complete the booking ask the user:
-Name
-PhoneNumber or email

If the user has provided the necessary data, please finish the conversation very friendly and politetly.

"""

prompt=ChatPromptTemplate.from_messages(
    [
        ("system",system),
        ("system","{car_list}"),
        ("human","{messages}")
    ]
)

chain=prompt|llm

from state import State
from memory import memory_obj

def booking_node(state:State):
    response=chain.invoke({"messages":state["messages"],"car_list":memory_obj.car_list})
    return{"messages":[response]}


#Test
# from langchain_core.messages import HumanMessage
# state={"messages": "i want to book the BMW","car_list":"""Available cars:
#        1. BMW
#        2. Audi"""}
# result=booking_node(state)
# print(result)