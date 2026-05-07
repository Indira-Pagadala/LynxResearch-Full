# app/agents/graph.py

import logging
from langgraph.graph import StateGraph, END
from app.agents.state import ResearchState
from app.agents.scout_agent import scout_agent
from app.agents.analyst_agent import analyst_agent
from app.agents.author_agent_1 import author_agent_1
from app.agents.author_agent_2 import author_agent_2
from app.agents.validator_agent import validator_agent

logger = logging.getLogger(__name__)


def build_research_graph() -> StateGraph:
    """
    Build and compile the full LangGraph research pipeline.
    Returns a compiled graph ready for ainvoke().
    """
    graph = StateGraph(ResearchState)

    # ── Register all nodes ────────────────────────────────────
    graph.add_node("scout", scout_agent)
    graph.add_node("analyst", analyst_agent)
    graph.add_node("author_1", author_agent_1)
    graph.add_node("author_2", author_agent_2)
    graph.add_node("validator", validator_agent)

    # ── Define edges (linear pipeline) ───────────────────────
    graph.set_entry_point("scout")
    graph.add_edge("scout", "analyst")
    graph.add_edge("analyst", "author_1")
    graph.add_edge("author_1", "author_2")
    graph.add_edge("author_2", "validator")
    graph.add_edge("validator", END)

    return graph.compile()


# Singleton compiled graph — import this in your API
research_graph = build_research_graph()