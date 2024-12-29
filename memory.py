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

class Memory:
    def __init__(self, name="Default"):
        # Initialize the user_preferences dictionary with the specified keys
        self.user_preferences = {
            "Make": None,
            "Model": None,
            "Color": None,
            "Location": None,
            "Date_available": None,
            "Price_per_day": None,
            "Year":None
        }
        # Initialize the chat_history list
        self.chat_history = []
        #Initialize car list
        self.car_list=[]
        # Initialize a string variable
        self.name = name

    def add_preference(self, key, value):
        # Add or update a key-value pair in the user_preferences dictionary
        if key in self.user_preferences:
            self.user_preferences[key] = value
        else:
            print(f"Key '{key}' is not valid. Valid keys are: Make, Model, Color, Location, Dates, Price.")

    def get_preference(self, key):
        # Retrieve a value from the user_preferences dictionary by key
        return self.user_preferences.get(key, "Preference not found")

    def display_preferences(self):
        # Display the entire user_preferences dictionary
        return self.user_preferences

    def display_name(self):
        # Display the string variable (name)
        return self.name

    def add_to_chat_history(self, item):
        # Add an item to the chat_history list
        self.chat_history.append(item)

    def display_chat_history(self):
        # Display the entire chat_history list
        return self.chat_history
    def reset_preferences(self):
        """Reset all user preferences to None"""
        for key in self.user_preferences:
            self.user_preferences[key] = None
        print("User preferences have been reset.")

# Example of usage
memory_obj = Memory("Conversation")  # Passing a name
# memory_obj.add_preference("Make", "Toyota")
# memory_obj.add_preference("Model", "Corolla")
# memory_obj.add_preference("Color", "Red")
# memory_obj.add_preference("Location", "New York")
# memory_obj.add_preference("Dates", "2024-12-20 to 2024-12-25")
# memory_obj.add_preference("Price", "$300")

# memory_obj.add_to_chat_history("User inquired about car availability.")
# memory_obj.add_to_chat_history("User updated preferences.")

# print(memory_obj.display_name())  # Output: Alice's Memory
# print(memory_obj.get_preference("Make"))  # Output: Toyota
# print(memory_obj.display_preferences())  # Output: {'Make': 'Toyota', 'Model': 'Corolla', 'Color': 'Red', 'Location': 'New York', 'Dates': '2024-12-20 to 2024-12-25', 'Price': '$300'}
# print(memory_obj.display_chat_history())  # Output: ['User inquired about car availability.', 'User updated preferences.']

    