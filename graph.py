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
from state import State

from SQLAgent import *
from utilities import print_colored
from displayAgent import displayAgent
from inputValidationAgent import input_control
from inputValidationAgent import locations, today


workflow=StateGraph(State)

workflow.add_node("input_validation",input_control)
workflow.add_node("list_table_tools",list_tables_tool_call)
workflow.add_node("get_schema",info_schema)
workflow.add_node("queryAgent",query_agent)
workflow.add_node("query_tool_node",query_tool_node)
workflow.add_node("displayAgent",displayAgent)

workflow.add_edge(START,"input_validation")
workflow.add_conditional_edges(
                    "input_validation", 
                    lambda x: x["next"], 
                    {
                       "True": "list_table_tools",
                       "False": END 
                    })
workflow.add_edge("list_table_tools","get_schema")
workflow.add_edge("get_schema","queryAgent")
workflow.add_edge("queryAgent","query_tool_node")
workflow.add_edge("query_tool_node","displayAgent")
workflow.add_edge("displayAgent",END)

graph=workflow.compile()


from langgraph.checkpoint.memory import MemorySaver
from recommendationAgent import recommendationAgent, search_tool_node, should_continue
from supervisor import supervisor_node
from bookingAgent import booking_node

workflow2=StateGraph(State)
workflow2.add_node("recommendationAgent",recommendationAgent)
workflow2.add_node("search_node",search_tool_node)
workflow2.add_node("supervisor",supervisor_node)
workflow2.add_node("bookingAgent",booking_node)

workflow2.add_edge(START,"supervisor")
workflow2.add_conditional_edges(
                    "supervisor", 
                    lambda x: x["next"])
workflow2.add_edge("bookingAgent",END)
workflow2.add_conditional_edges(
    # First, we define the start node. We use `agent`.
    # This means these are the edges taken after the `agent` node is called.
    "recommendationAgent",
    # Next, we pass in the function that will determine which node is called next.
    should_continue,
    # Finally we pass in a mapping.
    # The keys are strings, and the values are other nodes.
    # END is a special node marking that the graph should finish.
    # What will happen is we will call `should_continue`, and then the output of that
    # will be matched against the keys in this mapping.
    # Based on which one it matches, that node will then be called.
    {
        # If `tools`, then we call the tool node.
        "continue": "search_node",
        # Otherwise we finish.
        "end": END,
    },
)
workflow2.add_edge("search_node","recommendationAgent")



car_list = []
stategraph2:bool=False
continue_:bool=True

checkpointer = MemorySaver()
thread=1
graph2=workflow2.compile(checkpointer=checkpointer)

exit_ : bool = False
while not stategraph2 and not exit_:
    
    config={"configurable": {"thread_id": thread}}
    print("Please provide a date and location")
    user_input=input("Date and Location: ")

    for event in graph.stream({"messages": [("user", user_input)]}):
        #print(event)
        if 'input_validation' in event:
            response=event['input_validation']
            if(response['next']=='False'):
                print("\nPlease enter a valid Location and Date.")
                print(f"Valid Locations:{locations}")
                print(f"""Valid Dates include any date from today: {today}, to 2025-12-31""")
        if 'displayAgent' in event:
            car_list=event['displayAgent']['messages'][0].content
            print(car_list)
            memory_obj.car_list=car_list
            stategraph2=True
            continue_=True
   
    while stategraph2:

        user_input=input("user: ")

        if user_input.lower() == 'exit':
            stategraph2=False
            continue_=False
            exit_=True
            print("Have a nice day :)")
            break

        if user_input.lower() =='r':
            thread=thread+1
            stategraph2=False
            continue_=False
            
        
        if continue_:
            for event in graph2.stream({"messages":[("user",user_input)]},config):
                print(event)
                # if 'supervisor' in event:
                #     print(event['supervisor'])
                # if 'bookingAgent' in event:
                #     print(event['bookingAgent']['messages'][0].content)
                    
                # if 'recommendationAgent' in event:
                #     print(event['recommendationAgent']['messages'].content)

        
    

            print_colored("If you want to book a car let us know!" ,color="green")
        
            print_colored("To reset, type: r",color="red")
            







#STATEGRAPH PRINTING:

from langchain_core.runnables.graph import MermaidDrawMethod
# png_data = graph.get_graph().draw_mermaid_png(draw_method=MermaidDrawMethod.API)
# file_path = 'stategraph.png'
# with open(file_path, 'wb') as f:
#     f.write(png_data)
# os.startfile(file_path)

# png_data = graph2.get_graph().draw_mermaid_png(draw_method=MermaidDrawMethod.API)
# file_path = 'stategraph2.png'
# with open(file_path, 'wb') as f:
#     f.write(png_data)
# os.startfile(file_path)