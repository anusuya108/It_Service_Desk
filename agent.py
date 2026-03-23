# agent.py

from typing import TypedDict
from langgraph.graph import StateGraph, END
from core import classify_issue, should_escalate, get_resolution


class TicketState(TypedDict):
    ticket_id: str
    user_issue: str
    category: str
    priority: str
    resolution: str
    escalated: bool
    reason: str
    escalation_reason: str
    confidence: float


def triage_agent(state: TicketState):
    category, priority, reason, confidence = classify_issue(state["user_issue"])

    return {
        **state,
        "category": category,
        "priority": priority,
        "reason": reason,
        "confidence": confidence
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


def route_after_resolution(state: TicketState):
    return "escalation" if state["escalated"] else "__end__"


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
        "escalation_reason": "",
        "confidence": 0.0
    }

    return app.invoke(initial_state)