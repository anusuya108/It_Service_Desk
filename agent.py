# agent.py

from typing import TypedDict
from langgraph.graph import StateGraph, END
from core import classify_issue, should_escalate, get_resolution


# ─────────────────────────────
# STATE
# ─────────────────────────────

class TicketState(TypedDict):
    ticket_id: str
    user_issue: str
    category: str
    priority: str
    resolution: str
    escalated: bool
    reason: str
    escalation_reason: str


# ─────────────────────────────
# AGENTS
# ─────────────────────────────

def triage_agent(state: TicketState):
    category, priority, reason = classify_issue(state["user_issue"])

    return {
        **state,
        "category": category,
        "priority": priority,
        "reason": reason,
    }


def resolution_agent(state: TicketState):
    resolution = get_resolution(state["category"])

    escalated, esc_reason = should_escalate(
        state["category"],
        state["priority"],
        state["user_issue"]
    )

    return {
        **state,
        "resolution": resolution,
        "escalated": escalated,
        "escalation_reason": esc_reason
    }


def escalation_agent(state: TicketState):
    if not state["escalated"]:
        return state

    report = f"""
ISSUE SUMMARY:
{state['user_issue']}

REASON:
{state['escalation_reason']}

CATEGORY: {state['category']}
PRIORITY: {state['priority']}
"""

    return {
        **state,
        "escalation_report": report
    }


# ─────────────────────────────
# ROUTING
# ─────────────────────────────

def route_after_resolution(state: TicketState):
    return "escalation" if state["escalated"] else "__end__"


# ─────────────────────────────
# GRAPH
# ─────────────────────────────

def build_graph():
    graph = StateGraph(TicketState)

    graph.add_node("triage", triage_agent)
    graph.add_node("resolution", resolution_agent)
    graph.add_node("escalation", escalation_agent)

    graph.set_entry_point("triage")
    graph.add_edge("triage", "resolution")
    graph.add_conditional_edges("resolution", route_after_resolution)
    graph.add_edge("escalation", END)

    return graph.compile()


# ─────────────────────────────
# MAIN FUNCTION
# ─────────────────────────────

def process_ticket(ticket_id: str, user_issue: str):
    app = build_graph()

    initial_state: TicketState = {
        "ticket_id": ticket_id,
        "user_issue": user_issue,
        "category": "",
        "priority": "",
        "resolution": "",
        "escalated": False,
        "reason": "",
        "escalation_reason": ""
    }

    return app.invoke(initial_state)