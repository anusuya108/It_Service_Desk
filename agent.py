# agent.py — 3-agent LangGraph pipeline

import os
from typing import TypedDict, Annotated
from dotenv import load_dotenv
from langchain_groq import ChatGroq
from langchain_core.messages import SystemMessage, HumanMessage
from langgraph.graph import StateGraph, END
from langgraph.graph.message import add_messages

from core import classify_issue, should_escalate, get_resolution

load_dotenv()

# ── LLM ──────────────────────────────────────────────
llm = ChatGroq(
    model="llama-3.3-70b-versatile",
    temperature=0,
    api_key=os.environ.get("GROQ_API_KEY")
)


# ── STATE ─────────────────────────────────────────────
class TicketState(TypedDict):
    ticket_id:         str
    user_issue:        str
    category:          str
    priority:          str
    resolution:        str
    escalated:         bool
    reason:            str
    escalation_reason: str
    escalation_report: str
    confidence:        float


# ── LLM CLASSIFIER (fallback) ────────────────────────
def llm_classify(issue: str):
    system_prompt = """You are an IT ticket classifier.

Categories: hardware, software, network, account, other
Priority: low, medium, high, critical

Rules:
- shared drive, vpn, internet, wifi → network
- password, login, access denied → account
- crash, freeze, error, outlook, teams → software
- laptop, keyboard, mouse, monitor, spill → hardware
- multiple users affected → critical priority

Respond ONLY in this exact format:
category: <value>
priority: <value>"""

    try:
        response = llm.invoke([
            SystemMessage(content=system_prompt),
            HumanMessage(content=f"Issue: {issue}")
        ]).content.lower()
    except Exception as e:
        print(f"LLM classify error: {e}")
        return "other", "medium"

    category = "other"
    priority  = "medium"

    for c in ["hardware", "software", "network", "account", "other"]:
        if c in response:
            category = c
            break

    for p in ["critical", "high", "medium", "low"]:
        if p in response:
            priority = p
            break

    return category, priority


# ── AGENT 1: TRIAGE ──────────────────────────────────
def triage_agent(state: TicketState) -> TicketState:
    issue = state["user_issue"]

    # Rule-based first
    rule_cat, rule_pri, reason, confidence = classify_issue(issue)

    final_cat = rule_cat
    final_pri = rule_pri

    # Fall back to LLM if confidence is low
    if confidence < 0.7 or rule_cat == "other":
        llm_cat, llm_pri = llm_classify(issue)

        if confidence < 0.6:
            final_cat = llm_cat
            final_pri = llm_pri
            reason += " | LLM override (low confidence)"
        elif llm_cat != rule_cat:
            final_cat = llm_cat
            final_pri = llm_pri
            reason += " | LLM corrected category"

    return {
        **state,
        "category":   final_cat,
        "priority":   final_pri,
        "reason":     reason,
        "confidence": confidence,
    }


# ── AGENT 2: RESOLUTION ──────────────────────────────
def resolution_agent(state: TicketState) -> TicketState:
    # Pass both category and issue (matching core.py signature)
    resolution = get_resolution(state["category"], state["user_issue"])

    # Pass all 3 args (matching core.py signature)
    escalated, esc_reason = should_escalate(
        state["category"],
        state["priority"],
        state["user_issue"]
    )

    return {
        **state,
        "resolution":        resolution,
        "escalated":         escalated,
        "escalation_reason": esc_reason,
    }


# ── AGENT 3: ESCALATION ──────────────────────────────
def escalation_agent(state: TicketState) -> TicketState:
    if not state["escalated"]:
        return state

    report = f"""ESCALATION REPORT
═══════════════════════════════
Ticket ID  : {state['ticket_id']}
Category   : {state['category'].upper()}
Priority   : {state['priority'].upper()}

Issue:
{state['user_issue']}

Reason for escalation:
{state['escalation_reason']}

Suggested team:
{"SOC — Security Operations" if "ransom" in state['user_issue'].lower() or "breach" in state['user_issue'].lower()
 else "NOC — Network Operations" if state['category'] == "network"
 else "IAM — Identity & Access" if state['category'] == "account"
 else "Infrastructure Team" if state['category'] == "hardware"
 else "Tier-2 Software Support"}

SLA Target:
{"1 hour" if state['priority'] == "critical"
 else "4 hours" if state['priority'] == "high"
 else "1 business day"}
"""

    return {**state, "escalation_report": report}


# ── ROUTING ───────────────────────────────────────────
def route_after_resolution(state: TicketState):
    return "escalation" if state["escalated"] else END


# ── BUILD GRAPH ───────────────────────────────────────
def build_graph():
    graph = StateGraph(TicketState)

    graph.add_node("triage",     triage_agent)
    graph.add_node("resolution", resolution_agent)
    graph.add_node("escalation", escalation_agent)

    graph.set_entry_point("triage")
    graph.add_edge("triage", "resolution")
    graph.add_conditional_edges("resolution", route_after_resolution)
    graph.add_edge("escalation", END)

    return graph.compile()


# ── MAIN FUNCTION ─────────────────────────────────────
def process_ticket(ticket_id: str, user_issue: str) -> dict:
    app = build_graph()

    initial_state: TicketState = {
        "ticket_id":         ticket_id,
        "user_issue":        user_issue,
        "category":          "",
        "priority":          "",
        "resolution":        "",
        "escalated":         False,
        "reason":            "",
        "escalation_reason": "",
        "escalation_report": "",
        "confidence":        0.0,
    }

    return app.invoke(initial_state)


# ── QUICK TEST ────────────────────────────────────────
if __name__ == "__main__":
    tests = [
        ("TKT-001", "My laptop won't turn on after I spilled water on it."),
        ("TKT-002", "I forgot my password and can't log into Outlook."),
        ("TKT-003", "The entire office internet is down. No one can work."),
    ]

    for tid, issue in tests:
        print(f"\n{'='*50}")
        print(f"Ticket : {tid}")
        print(f"Issue  : {issue}")
        result = process_ticket(tid, issue)
        print(f"Category   : {result['category']}")
        print(f"Priority   : {result['priority']}")
        print(f"Escalated  : {result['escalated']}")
        print(f"Resolution : {result['resolution'][:80]}...")