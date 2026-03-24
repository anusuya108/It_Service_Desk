# agent.py — 3-agent LangGraph pipeline (intelligent version)
#
# What makes this genuinely intelligent now:
#   1. Triage agent shows WHY it decided — visible reasoning in plain English
#   2. Resolution agent is fully LLM-driven — dynamic, context-aware, not templates
#   3. Memory — finds similar past tickets and uses them to improve resolution
#   4. Escalation agent uses LLM reasoning with 5 context factors
#   5. Context-aware priority — admin of production, CEO, multi-user all handled
#   6. Zero internals leak — all debug info stays server-side

import os
from typing import TypedDict
from dotenv import load_dotenv
from langchain_groq import ChatGroq
from langchain_core.messages import SystemMessage, HumanMessage
from langgraph.graph import StateGraph, END

from core import classify_issue, get_team, get_sla
from memory import find_similar, save_ticket

load_dotenv()

# ── LLM SETUP ─────────────────────────────────────────
_llm = None

def _get_llm():
    global _llm
    if _llm is not None:
        return _llm
    key = os.environ.get("GROQ_API_KEY","").strip()
    if not key:
        return None
    try:
        _llm = ChatGroq(model="llama-3.3-70b-versatile", temperature=0, api_key=key)
        return _llm
    except Exception:
        return None


def _call(messages: list, fallback: str = "") -> str:
    """Safe LLM call — never raises, never leaks errors."""
    try:
        llm = _get_llm()
        if llm is None:
            return fallback
        return llm.invoke(messages).content.strip()
    except Exception:
        return fallback


# ── STATE ─────────────────────────────────────────────
class TicketState(TypedDict):
    ticket_id:         str
    user_issue:        str
    category:          str
    priority:          str
    priority_reason:   str   # WHY this priority was chosen — shown to user
    triage_reasoning:  str   # full triage explanation — shown to user
    similar_past:      str   # past similar issue found — shown to user
    resolution:        str
    escalated:         bool
    escalation_reason: str
    escalation_report: str


# ─────────────────────────────────────────────────────
# AGENT 1 — TRIAGE
# Classifies ticket + explains WHY + finds similar past issues
# ─────────────────────────────────────────────────────
def triage_agent(state: TicketState) -> TicketState:
    issue = state["user_issue"]

    # Step 1: Rule-based classification with reasoning
    rule_cat, rule_pri, priority_reason, match_strength = classify_issue(issue)

    final_cat    = rule_cat
    final_pri    = rule_pri
    triage_reasoning = ""

    # Step 2: LLM verifies weak/no matches + generates professional reasoning
    if match_strength in ("weak","none"):
        response = _call([
            SystemMessage(content="""You are a senior IT support triage specialist.
Classify this IT issue and explain your reasoning professionally.

Categories: hardware, software, network, account, other
Priority:   low, medium, high, critical

Priority rules:
- critical: office-wide outage, data loss, ransomware, security breach
- high: user completely blocked, physical damage, executive affected, production system
- medium: single user affected, workaround may exist
- low: minor issue, how-to question, cosmetic problem

Respond ONLY in this exact format:
category: <value>
priority: <value>
reasoning: <one professional sentence explaining the classification>"""),
            HumanMessage(content=f"Issue: {issue}")
        ])

        if response:
            lines = {}
            for line in response.lower().splitlines():
                if ":" in line:
                    k, _, v = line.partition(":")
                    lines[k.strip()] = v.strip()
            for c in ["hardware","software","network","account","other"]:
                if c in lines.get("category",""):
                    final_cat = c
                    break
            for p in ["critical","high","medium","low"]:
                if p in lines.get("priority",""):
                    final_pri = p
                    priority_reason = lines.get("reasoning","").capitalize() or priority_reason
                    break
            triage_reasoning = lines.get("reasoning","").capitalize()

    # Step 3: Generate clean triage explanation if not already set
    if not triage_reasoning:
        triage_reasoning = _call([
            SystemMessage(content="""You are an IT support triage specialist.
Write ONE professional sentence explaining this ticket classification.
Do not mention keywords, rules, algorithms, or AI.
Format exactly: "This ticket has been classified as [category] with [priority] priority because [clear business reason]." """),
            HumanMessage(content=f"Category: {final_cat}, Priority: {final_pri}, Issue: {issue}")
        ], fallback=f"This ticket has been classified as {final_cat} with {final_pri} priority. {priority_reason}")

    # Step 4: Find similar past issue from memory
    similar    = find_similar(issue, final_cat)
    similar_past = ""
    if similar:
        similar_past = f"Similar past issue: \"{similar['issue'].title()}\" — {similar['resolution']}"

    return {
        **state,
        "category":        final_cat,
        "priority":        final_pri,
        "priority_reason": priority_reason,
        "triage_reasoning": triage_reasoning,
        "similar_past":    similar_past,
    }


# ─────────────────────────────────────────────────────
# AGENT 2 — RESOLUTION
# Fully LLM-driven. Uses past similar issue context.
# Critical tickets escalate immediately — no pointless steps.
# ─────────────────────────────────────────────────────
def resolution_agent(state: TicketState) -> TicketState:
    issue    = state["user_issue"]
    category = state["category"]
    priority = state["priority"]
    similar  = state["similar_past"]

    # Critical → immediate escalation, no L1 steps
    if priority == "critical":
        resolution = (
            "This issue has been identified as a critical incident. "
            "It is being escalated immediately to the senior support team. "
            "Please do not attempt further troubleshooting — a specialist will contact you within 1 hour."
        )
        save_ticket(state["ticket_id"], issue, category, priority, resolution, True)
        return {
            **state,
            "resolution":        resolution,
            "escalated":         True,
            "escalation_reason": "Critical incident — immediate escalation, no L1 resolution attempted.",
        }

    # Build context from past similar issue if available
    past_context = ""
    if similar:
        past_context = f"\n\nRELEVANT PAST CASE:\n{similar}\nUse this context to improve your advice if relevant."

    # Fully LLM-driven resolution
    resolution = _call([
        SystemMessage(content=f"""You are a Level-1 IT Support Engineer providing remote support.

Ticket details:
- Category: {category}
- Priority: {priority}{past_context}

Write specific, actionable troubleshooting steps for this exact issue.

Rules:
- Give exactly 4 numbered steps tailored to THIS specific issue
- If physical damage involved (liquid spill, cracked screen): tell user to power off IMMEDIATELY, do not turn on, bring to IT desk
- Reference the past case context if it is relevant and helpful
- End every response with: "If these steps do not resolve the issue, please reply to this ticket for further assistance."
- Maximum 140 words
- Write as a human support engineer — no mention of AI or systems"""),
        HumanMessage(content=f"Issue: {issue}")
    ], fallback=_fallback(category))

    # LLM escalation decision with full context
    esc_response = _call([
        SystemMessage(content="""You are an IT escalation manager reviewing a support ticket.
Decide whether this needs Level-2 escalation.

Escalate YES if ANY of these apply:
- Issue cannot realistically be fixed remotely
- Affects multiple users or a shared system
- Involves security, compliance, or data risk
- Requires physical hardware repair or replacement
- User is a senior executive or VIP
- L1 resolution steps are unlikely to work

Respond ONLY in this exact format:
decision: YES or NO
reason: <one clear sentence>"""),
        HumanMessage(content=f"Category: {category}\nPriority: {priority}\nIssue: {issue}\nProposed resolution: {resolution[:250]}")
    ])

    escalated  = False
    esc_reason = ""
    if esc_response:
        escalated = "decision: yes" in esc_response.lower()
        for line in esc_response.splitlines():
            if line.lower().startswith("reason:"):
                esc_reason = line.split(":",1)[1].strip().capitalize()
                break
    else:
        # LLM unavailable — rule fallback
        if priority == "high":
            escalated  = True
            esc_reason = "High priority issue escalated per standard policy."

    # Save to memory for future reference
    save_ticket(state["ticket_id"], issue, category, priority, resolution, escalated)

    return {
        **state,
        "resolution":        resolution,
        "escalated":         escalated,
        "escalation_reason": esc_reason,
    }


def _fallback(category: str) -> str:
    return {
        "network":  "1. Restart your router and device.\n2. Check all network cables are connected.\n3. Try a mobile hotspot to confirm if the issue is local.\n4. If the issue persists, please reply to this ticket for further assistance.",
        "account":  "1. Use the self-service password reset link on the company intranet.\n2. Clear your browser cache and try again.\n3. Ensure your authenticator app time is synced correctly.\n4. If still locked out, please reply to this ticket for further assistance.",
        "hardware": "1. If liquid damage — power off immediately, do not turn back on.\n2. Disconnect all cables and the power source.\n3. Bring the device to the IT desk for inspection.\n4. If the issue persists, please reply to this ticket for further assistance.",
        "software": "1. Close the application fully using Task Manager.\n2. Restart your computer and reopen the application.\n3. Check for pending Windows or application updates.\n4. If the issue persists, please reply to this ticket for further assistance.",
        "other":    "1. Restart your device.\n2. Note any error messages shown.\n3. Check if the issue affects colleagues nearby.\n4. If the issue persists, please reply to this ticket for further assistance.",
    }.get(category, "Please contact the IT helpdesk directly with your ticket number.")


# ─────────────────────────────────────────────────────
# AGENT 3 — ESCALATION
# Structured report for the senior team
# ─────────────────────────────────────────────────────
def escalation_agent(state: TicketState) -> TicketState:
    if not state["escalated"]:
        return {**state, "escalation_report": ""}

    team = get_team(state["category"], state["user_issue"])
    sla  = get_sla(state["priority"])

    report = (
        f"ESCALATION REPORT\n"
        f"{'═'*40}\n"
        f"Ticket ID  : {state['ticket_id']}\n"
        f"Category   : {state['category'].upper()}\n"
        f"Priority   : {state['priority'].upper()}\n"
        f"Assign to  : {team}\n"
        f"SLA Target : {sla}\n"
        f"\nISSUE:\n{state['user_issue']}\n"
        f"\nPRIORITY JUSTIFICATION:\n{state['priority_reason']}\n"
        f"\nESCALATION REASON:\n{state['escalation_reason']}\n"
        f"\nL1 NOTES:\n{state['resolution'][:400]}\n"
        f"\nACTION REQUIRED:\n"
        f"Acknowledge within SLA window and contact the user directly.\n"
        f"{'═'*40}"
    )

    return {**state, "escalation_report": report}


# ── ROUTING ───────────────────────────────────────────
def route_after_resolution(state: TicketState):
    return "escalation" if state["escalated"] else END


# ── GRAPH ─────────────────────────────────────────────
def build_graph():
    graph = StateGraph(TicketState)
    graph.add_node("triage",     triage_agent)
    graph.add_node("resolution", resolution_agent)
    graph.add_node("escalation", escalation_agent)
    graph.set_entry_point("triage")
    graph.add_edge("triage",     "resolution")
    graph.add_conditional_edges("resolution", route_after_resolution)
    graph.add_edge("escalation", END)
    return graph.compile()


# ── MAIN ──────────────────────────────────────────────
def process_ticket(ticket_id: str, user_issue: str) -> dict:
    initial: TicketState = {
        "ticket_id":         ticket_id,
        "user_issue":        user_issue,
        "category":          "",
        "priority":          "",
        "priority_reason":   "",
        "triage_reasoning":  "",
        "similar_past":      "",
        "resolution":        "",
        "escalated":         False,
        "escalation_reason": "",
        "escalation_report": "",
    }
    return build_graph().invoke(initial)


# ── TEST ──────────────────────────────────────────────
if __name__ == "__main__":
    tests = [
        ("TKT-001", "My laptop won't turn on after I spilled water on it."),
        ("TKT-002", "I forgot my password and I am the admin of the production system."),
        ("TKT-003", "The entire office internet is down. No one can work."),
        ("TKT-004", "The CEO cannot access his email since this morning."),
        ("TKT-005", "Microsoft Teams crashes every time I join a meeting."),
    ]
    for tid, issue in tests:
        print(f"\n{'='*60}")
        print(f"  {tid}: {issue}")
        r = process_ticket(tid, issue)
        print(f"  Category  : {r['category']}  | Priority : {r['priority']}")
        print(f"  Reasoning : {r['priority_reason']}")
        print(f"  Escalated : {r['escalated']}")
        if r['similar_past']:
            print(f"  Past case : {r['similar_past'][:80]}...")
        print(f"  Resolution: {r['resolution'][:100]}...")