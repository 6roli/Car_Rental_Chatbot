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


from PyQt5.QtWidgets import (
    QApplication,
    QMainWindow,
    QVBoxLayout,
    QLineEdit,
    QPushButton,
    QTextBrowser,
    QWidget,
)
import sys


def process_initial_input(user_input):
    global stategraph2, car_list
    response_messages = []
    for event in graph.stream({"messages": [("user", user_input)]}):
        if 'input_validation' in event:
            response = event['input_validation']
            if response['next'] == 'False':
                response_messages.append(
                    f"Invalid Location or Date.\nValid Locations: {locations}\nValid Dates: {today} to 2025-12-31"
                )
        if 'displayAgent' in event:
            car_list = event['displayAgent']['messages'][0].content
            response_messages.append(f"Available Cars: {car_list}")
            memory_obj.car_list = car_list
            stategraph2 = True
    return "\n".join(response_messages)


def process_secondary_input(user_input):
    global stategraph2, continue_, exit_, thread
    response_messages = []

    if user_input.lower() == 'exit':
        stategraph2 = False
        continue_ = False
        exit_ = True
        return "Have a nice day :)"

    if user_input.lower() == 'r':
        thread += 1
        stategraph2 = False
        continue_ = False
        return "Resetting session..."

    if continue_:
        config = {"configurable": {"thread_id": thread}}
        for event in graph2.stream({"messages": [("user", user_input)]}, config):
            if 'supervisor' in event:
                response_messages.append(str(event['supervisor']))
            if 'bookingAgent' in event:
                response_messages.append(event['bookingAgent']['messages'][0].content)
            if 'recommendationAgent' in event:
                response_messages.append(event['recommendationAgent']['messages'].content)

        response_messages.append("If you want to book a car, let us know!")
        response_messages.append("To reset, type: r")

    return "\n".join(response_messages)


class ChatbotUI(QMainWindow):
    def __init__(self):
        super().__init__()
        self.init_ui()

    def init_ui(self):
        # Window settings
        self.setWindowTitle("Car Rental Chatbot")
        self.setGeometry(100, 100, 600, 500)

        # Central widget
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)

        # Layout
        self.layout = QVBoxLayout()
        self.central_widget.setLayout(self.layout)

        # Chat display area
        self.chat_display = QTextBrowser()
        self.chat_display.setStyleSheet("font-size: 16px;")
        self.layout.addWidget(self.chat_display)

        # Input field
        self.input_field = QLineEdit()
        self.input_field.setPlaceholderText("Type your message here...")
        self.input_field.setStyleSheet("font-size: 16px; padding: 5px;")
        self.layout.addWidget(self.input_field)

        # Send button
        self.send_button = QPushButton("Send")
        self.send_button.setStyleSheet(
            "font-size: 16px; padding: 10px; background-color: #4CAF50; color: white;"
        )
        self.layout.addWidget(self.send_button)

        # Button action
        self.send_button.clicked.connect(self.handle_user_input)

    def handle_user_input(self):
        user_message = self.input_field.text().strip()
        if not user_message:
            return

        self.chat_display.append(f"You: {user_message}")
        self.input_field.clear()

        if not stategraph2:
            bot_response = process_initial_input(user_message)
        else:
            bot_response = process_secondary_input(user_message)

        self.chat_display.append(f"Bot: {bot_response}")

        if exit_:
            QApplication.quit()


# Run the app
if __name__ == "__main__":
    app = QApplication(sys.argv)
    main_window = ChatbotUI()
    main_window.show()
    sys.exit(app.exec_())