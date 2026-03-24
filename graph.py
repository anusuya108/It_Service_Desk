# graph.py

from langgraph.graph import StateGraph
from core import classify_category, rule_priority, should_escalate
from model import priority_model
from retriever import retrieve


def triage(state):
    state["category"] = classify_category(state["text"])
    return state


def priority(state):
    text = state["text"]

    rule_pred, rule_conf = rule_priority(text)

    if rule_pred:
        state["priority"] = rule_pred
        state["confidence"] = rule_conf
    else:
        pred, conf = priority_model.predict(text)
        state["priority"] = pred
        state["confidence"] = conf

    return state


def retrieval(state):
    sim_text, score = retrieve(state["text"])
    state["similar"] = sim_text
    state["score"] = score
    return state


def decision(state):
    if should_escalate(state["priority"], state["confidence"]):
        return "escalation"
    return "resolution"


def resolution(state):
    state["response"] = "Issue handled at Level 1 support."
    state["status"] = "resolved"
    return state


def escalation(state):
    state["response"] = "Escalated to higher support."
    state["status"] = "escalated"
    return state


def build_graph():
    builder = StateGraph(dict)

    builder.add_node("triage", triage)
    builder.add_node("priority", priority)
    builder.add_node("retrieval", retrieval)
    builder.add_node("resolution", resolution)
    builder.add_node("escalation", escalation)

    builder.set_entry_point("triage")

    builder.add_edge("triage", "priority")
    builder.add_edge("priority", "retrieval")

    builder.add_conditional_edges(
        "retrieval",
        decision,
        {"resolution": "resolution", "escalation": "escalation"}
    )

    builder.set_finish_point("resolution")
    builder.set_finish_point("escalation")

    return builder.compile()