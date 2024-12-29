from flask import Flask, render_template, request, jsonify
from dotenv import load_dotenv
import os

# Import necessary chatbot functions and workflows
from state import State
from SQLAgent import list_tables_tool_call, info_schema, query_agent, query_tool_node
from utilities import print_colored
from displayAgent import displayAgent
from inputValidationAgent import input_control, locations, today
from langgraph.graph import END, StateGraph, START
from recommendationAgent import recommendationAgent, search_tool_node, should_continue
from supervisor import supervisor_node
from bookingAgent import booking_node
from langgraph.checkpoint.memory import MemorySaver

# Initialize Flask app
app = Flask(__name__)

# First workflow: Input validation and car search
workflow = StateGraph(State)
workflow.add_node("input_validation", input_control)
workflow.add_node("list_table_tools", list_tables_tool_call)
workflow.add_node("get_schema", info_schema)
workflow.add_node("queryAgent", query_agent)
workflow.add_node("query_tool_node", query_tool_node)
workflow.add_node("displayAgent", displayAgent)

workflow.add_edge(START, "input_validation")
workflow.add_conditional_edges(
    "input_validation", 
    lambda x: x["next"], 
    {
        "True": "list_table_tools",
        "False": END 
    }
)
workflow.add_edge("list_table_tools", "get_schema")
workflow.add_edge("get_schema", "queryAgent")
workflow.add_edge("queryAgent", "query_tool_node")
workflow.add_edge("query_tool_node", "displayAgent")
workflow.add_edge("displayAgent", END)

graph = workflow.compile()

# Second workflow: Recommendations and booking
workflow2 = StateGraph(State)
workflow2.add_node("recommendationAgent", recommendationAgent)
workflow2.add_node("search_node", search_tool_node)
workflow2.add_node("supervisor", supervisor_node)
workflow2.add_node("bookingAgent", booking_node)

workflow2.add_edge(START, "supervisor")
workflow2.add_conditional_edges(
    "supervisor", 
    lambda x: x["next"]
)
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
graph2 = workflow2.compile(checkpointer=MemorySaver())

# Global state variables
car_list = []
stategraph2 = False
continue_ = True
exit_ = False
thread = 1

from memory import memory_obj
# Process initial input
def process_initial_input(user_input):
    global graph, stategraph2, car_list

    response = ""
    for event in graph.stream({"messages": [("user", user_input)]}):
        if "input_validation" in event:
            result = event["input_validation"]
            if result["next"] == "False":
                response = (
                    "Invalid Location or Date.\n"
                    f"Valid Locations: {locations}\n"
                    f"Valid Dates: from {today} to 2025-12-31"
                )
            else:
                response = "Input validated. Searching for cars..."

        if "displayAgent" in event:
            car_list = event["displayAgent"]["messages"][0].content
            response += f"\nCars available:\n{car_list}"
            memory_obj.car_list=car_list
            stategraph2 = True  # Move to the next state

    return response
    #return jsonify({"response": response})


# Process secondary input
def process_secondary_input(user_input):
    global graph2, stategraph2, thread, exit_

    response = ""
    config = {"configurable": {"thread_id": thread}}

    # if user_input.lower() == "exit":
    #     stategraph2 = False
    #     car_list = []
    #     continue_ = True
    #     exit_ = True
    #     return "Exiting the chatbot. Have a nice day! :)"

    if user_input.lower() == "reset":
        
        stategraph2 = False
        car_list = []
        continue_ = True
        exit_ = False
        thread=thread+1
        return "Chatbot has been reset. Please restart the conversation by providing a valid DATE and LOCATION."

    for event in graph2.stream({"messages": [("user", user_input)]}, config):
        # if "supervisor" in event:
        #     response += event["supervisor"] CAN ONLY concatanate str not dict
        if "bookingAgent" in event:
            response += f"\n{event['bookingAgent']['messages'][0].content}"
        if "recommendationAgent" in event:
            response += f"\n{event['recommendationAgent']['messages'].content}"
        if 'search_node' in event:
            response+= f"\n{event['search_node']['messages'][0].content}"

    response += "\n\nIf you want to book a car, let us know!"
    response += "\nTo reset, send: 'reset'."
    return response

def get_chat_response():
    return '{"message": "Hello, this is the chat response!"}'


# Flask routes
@app.route("/")
def home():
    return render_template("index.html")


# @app.route("/chat", methods=["POST"])
# def chat():
#     user_input = request.json.get("message")

#     if not user_input:
#         return jsonify({"response": "Invalid input received."})

#     # Check if the user input is 'r' to restart the app
#     if user_input.lower() == 'r':
#         os._exit(0)  # Forcefully restart the app by exiting the process

#     # Process the input based on the state of the chatbot
#     if not stategraph2:
#         bot_response = process_initial_input(user_input)
#     else:
#         bot_response = process_secondary_input(user_input)

#     return jsonify({"response": bot_response})

@app.route("/chat", methods=["POST"])
def chat():
    user_input = request.json.get("message")

    if not user_input:
        return jsonify({"response": "Invalid input received."})

    # Check if the user input is 'reset' to restart the app
    # if user_input.lower() == 'reset':
    #     # Reset variables and state to go back to the first step of the workflow
    #     global stategraph2, car_list, continue_, exit_, thread
        
    #     # Reset state variables to initial state
    #     stategraph2 = False
    #     car_list = []
    #     continue_ = False
    #     exit_ = False
    #     thread = thread + 1  # Clear checkpointer memory

    #     # Provide a response to the user indicating the restart
    #     return jsonify({"response": "Chatbot has been reset. Please restart the conversation by providing a valid DATE and LOCATION."})

    # Process the input based on the state of the chatbot
    if not stategraph2:
        bot_response = process_initial_input(user_input)
    else:
        bot_response = process_secondary_input(user_input)

    return jsonify({"response": bot_response})



if __name__ == "__main__":
    app.run(debug=True)
