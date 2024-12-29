from typing import Literal
from typing_extensions import TypedDict

from datetime import datetime
from langchain_groq import ChatGroq
from langgraph.graph import END, StateGraph, START
from langchain_core.messages import HumanMessage, SystemMessage

import os
from dotenv import load_dotenv
load_dotenv()
groq_api_key=os.getenv("GROQ_API_KEY")
# Llistat de localitzacions vàlides
locations = ["Madrid", "Barcelona", "Sevilla", "Valencia", "Malaga", "Granada", "Bilbao", "Alicante", "Zaragoza", "Palma"]
today = datetime.now().date()

# Missatge del sistema
system = f"""You are in charge of validating the user input by using the function `Router`. 
The `Router` function accepts a dictionary with the following key:
- `next`: Either "START" or "NEXT", based on whether the input meets the criteria.

To validate the user input, follow these criteria:
1. The input must mention **both a location and dates**.
2. The location must be one of the following: {locations}.
3. The date or dates must be between {today} and 2025/12/31.
4. If the user does not mention a year assume 2025 to validate the input.

If the input matches all the criteria, set `next` to "True". Otherwise, set it to "False".

Examples:
- Input: "Bilbao and January 2025" → `Router(next="True")`
- Input: "Canada and January" → `Router(next="False")`
- Input: "Barcelona November" → `Router(next="True")`
- Input: "Barcelona November 2024" → `Router(next="False")`
- Input: "Barcelona Today" → `Router(next="True")`



Your task is to process the input and decide the value of `next`.
"""


# Classe Router per tipificar la resposta
class Router(TypedDict):
    next: Literal["True", "False"]

# Configuració del model Groq
llm = ChatGroq(temperature=0,model="llama-3.3-70b-versatile")

# Funció de validació
def input_control(state):
    # Afegeix el missatge del sistema i els missatges de l'usuari al context
    messages = [
        {"role": "system", "content": system},
    ] + state["messages"]
    
    # Crida al model amb resposta estructurada
    response = llm.with_structured_output(Router).invoke(messages)
    goto = response["next"]
    
    return {"next": goto}


#TEST------------
# # Definició d'estat inicial
# state = {"messages": [HumanMessage(role="user", content="Canada and january")]}

# # Crida a la funció
# result = input_control(state)

# # Mostra el resultat
# print(result)
