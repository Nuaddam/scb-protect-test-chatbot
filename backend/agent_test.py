# graph.py
from langgraph.graph import StateGraph, END
from shared import AgentState
from nodes import interview_node
from langgraph.checkpoint.memory import MemorySaver

def from_router(state):
    return state.get("route", "interview")

g = StateGraph(AgentState)
g.add_node("interview", interview_node)
g.set_entry_point("interview")

# After interview is complete, stop
g.add_edge("interview", END)


checkpointer = MemorySaver()

# Compile the agent
agent = g.compile(checkpointer=checkpointer)
