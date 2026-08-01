import os
from dotenv import load_dotenv
from typing import Annotated, TypedDict

from langchain_openai import ChatOpenAI
from langchain_core.tools import tool
from langchain_core.messages import BaseMessage
from langgraph.graph import StateGraph, END
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode

load_dotenv()

#hardcoding for now
@tool
def get_weather(city: str) -> str:
    """Returns the current weather for a given city."""
    fake_weather_data = {
        "san francisco": "62°F, foggy",
        "new york": "78°F, sunny",
        "chennai": "91°F, humid",
    }
    return fake_weather_data.get(city.lower(), f"No weather data for {city}.")

@tool
def calculate(expression: str) -> str:
    """Evaluates a simple math expression, e.g. '15 * 3' or '100 / 4'."""
    try:
        result = eval(expression, {"__builtins__": {}}, {})
        return str(result)
    except Exception as e:
        return f"Error evaluating expression: {e}"

tools = [get_weather, calculate]

class AgentState(TypedDict):
    messages: Annotated[list[BaseMessage], add_messages]

llm = ChatOpenAI(model="gpt-4o", temperature=0)
llm_with_tools = llm.bind_tools(tools)

def call_llm(state: AgentState) -> AgentState:
    response = llm_with_tools.invoke(state["messages"])
    return {"messages": [response]}

def should_continue(state: AgentState) -> str:
    last_message = state["messages"][-1]
    if last_message.tool_calls:
        return "tools"
    return END

graph_builder = StateGraph(AgentState)

graph_builder.add_node("llm", call_llm)
graph_builder.add_node("tools", ToolNode(tools))

graph_builder.set_entry_point("llm")
graph_builder.add_conditional_edges("llm", should_continue, {"tools": "tools", END: END})
graph_builder.add_edge("tools", "llm")

graph = graph_builder.compile()

if __name__ == "__main__":
    from langchain_core.messages import HumanMessage

    user_input = "What's the weather in Chennai, and what's 340 divided by 4?"

    result = graph.invoke({"messages": [HumanMessage(content=user_input)]})

    print("\n--- Full conversation ---")
    for msg in result["messages"]:
        print(f"[{msg.__class__.__name__}] {msg.content if msg.content else msg.tool_calls}")

    print("\n--- Final answer ---")
    print(result["messages"][-1].content)