# graph.py

from langgraph.graph import StateGraph
from core import classify_category, rule_priority, should_escalate


def triage(state):
    state["category"] = classify_category(state["text"])
    return state


def priority(state):
    state["priority"] = rule_priority(state["text"])
    return state


def decision(state):
    if should_escalate(state["priority"]):
        return "escalation"
    return "resolution"


def resolution(state):
    state["status"] = "resolved"
    state["response"] = "Resolved at Level 1."
    return state


def escalation(state):
    state["status"] = "escalated"
    state["response"] = "Escalated to support team."
    return state


def build_graph():
    builder = StateGraph(dict)

    builder.add_node("triage", triage)
    builder.add_node("priority", priority)
    builder.add_node("resolution", resolution)
    builder.add_node("escalation", escalation)

    builder.set_entry_point("triage")

    builder.add_edge("triage", "priority")

    builder.add_conditional_edges(
        "priority",
        decision,
        {
            "resolution": "resolution",
            "escalation": "escalation"
        }
    )

    builder.set_finish_point("resolution")
    builder.set_finish_point("escalation")

    return builder.compile()