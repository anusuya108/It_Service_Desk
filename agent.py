# agent.py — 3-agent LangGraph pipeline
#
# Design principles:
#   - Zero internal debug info ever reaches the user
#   - Critical tickets skip resolution and escalate immediately
#   - LLM failure is completely invisible — rules take over silently
#   - Every field has a safe default — nothing ever crashes

import os
from typing import TypedDict
from dotenv import load_dotenv
from langchain_groq import ChatGroq
from langchain_core.messages import SystemMessage, HumanMessage
from langgraph.graph import StateGraph, END

from core import classify_issue, get_team, get_sla

load_dotenv()

# ── LLM — initialised once, fails silently ────────────
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


def _llm_call(messages: list, fallback: str = "") -> str:
    """Safe LLM call. Returns fallback silently on any failure."""
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
    triage_reasoning:  str   # clean user-facing explanation
    resolution:        str
    escalated:         bool
    escalation_reason: str
    escalation_report: str


# ─────────────────────────────────────────────────────
# AGENT 1 — TRIAGE
# Classifies the ticket. Shows clean reasoning to user.
# LLM corrects weak matches. All internals hidden.
# ─────────────────────────────────────────────────────
def triage_agent(state: TicketState) -> TicketState:
    issue = state["user_issue"]
    rule_cat, rule_pri, match_strength = classify_issue(issue)

    final_cat = rule_cat
    final_pri = rule_pri
    reasoning = ""

    if match_strength == "strong":
        # Rules are confident — no LLM needed
        reasoning = _llm_call([
            SystemMessage(content="""You are an IT support triage specialist.
Write ONE clear sentence explaining why this ticket was classified the way it was.
Do not mention keywords, rules, or AI. Write as a professional support agent would.
Format: "This ticket has been classified as [category] with [priority] priority because [reason]." """),
            HumanMessage(content=f"Category: {final_cat}, Priority: {final_pri}, Issue: {issue}")
        ], fallback=f"This ticket has been classified as {final_cat} with {final_pri} priority.")

    else:
        # Weak or no match — use LLM to classify properly
        response = _llm_call([
            SystemMessage(content="""You are a senior IT support triage specialist.
Classify this IT issue and explain your reasoning.

Categories: hardware, software, network, account, other
Priority:   low, medium, high, critical

Priority rules:
- critical: entire office affected, data loss, ransomware, security breach
- high: user completely blocked, physical damage, senior executive affected
- medium: significant issue, some workaround may exist
- low: minor issue, cosmetic, how-to question

Respond ONLY in this format:
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
                    break

            # Get clean reasoning — strip any internal references
            raw_reason = lines.get("reasoning","")
            reasoning  = raw_reason.capitalize() if raw_reason else \
                         f"This ticket has been classified as {final_cat} with {final_pri} priority."
        else:
            # LLM not available — use rules silently, show clean message
            reasoning = f"This ticket has been classified as {final_cat} with {final_pri} priority."

    return {
        **state,
        "category":        final_cat,
        "priority":        final_pri,
        "triage_reasoning": reasoning,
    }


# ─────────────────────────────────────────────────────
# AGENT 2 — RESOLUTION
# Critical tickets → skip steps, escalate immediately.
# Others → LLM generates specific actionable steps.
# ─────────────────────────────────────────────────────
def resolution_agent(state: TicketState) -> TicketState:
    issue    = state["user_issue"]
    category = state["category"]
    priority = state["priority"]

    # ── CRITICAL: no point giving basic steps ─────────
    if priority == "critical":
        resolution = (
            "This issue has been identified as a critical incident. "
            "It is being escalated immediately to the senior support team. "
            "Please do not attempt further troubleshooting — a specialist will contact you shortly."
        )
        return {
            **state,
            "resolution":        resolution,
            "escalated":         True,
            "escalation_reason": "Critical incident — immediate escalation required, no L1 resolution attempted",
        }

    # ── STANDARD: LLM generates specific steps ────────
    resolution = _llm_call([
        SystemMessage(content=f"""You are a Level-1 IT Support Engineer providing remote support.

Ticket:
- Category: {category}
- Priority: {priority}

Write specific, actionable troubleshooting steps for this exact issue.
Rules:
- 4 numbered steps maximum
- Be specific to THIS issue, not generic advice
- If physical damage is involved, tell user to power off immediately and bring device to IT desk
- End with: "If these steps do not resolve the issue, please reply to this ticket for further assistance."
- Maximum 120 words
- Do not mention AI, LLM, or classification systems"""),
        HumanMessage(content=f"Issue: {issue}")
    ], fallback=_fallback_resolution(category))

    # ── ESCALATION DECISION via LLM ───────────────────
    esc_response = _llm_call([
        SystemMessage(content="""You are an IT escalation manager.
Decide if this ticket needs Level-2 escalation.

Escalate if ANY of these apply:
- Cannot realistically be fixed remotely
- Affects multiple users
- Security, compliance, or data risk involved
- Physical hardware replacement needed
- User is completely unable to work with no workaround

Respond ONLY in this format:
decision: YES or NO
reason: <one sentence>"""),
        HumanMessage(content=f"Category: {category}\nPriority: {priority}\nIssue: {issue}\nProposed resolution: {resolution[:200]}")
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
        # LLM unavailable — fall back to priority rules silently
        if priority == "high":
            escalated  = True
            esc_reason = "Escalated due to high priority impact"

    return {
        **state,
        "resolution":        resolution,
        "escalated":         escalated,
        "escalation_reason": esc_reason,
    }


def _fallback_resolution(category: str) -> str:
    return {
        "network":  "1. Restart your router and device.\n2. Check all network cables are securely connected.\n3. Try connecting via a mobile hotspot to confirm if the issue is local.\n4. If the issue persists, please reply to this ticket for further assistance.",
        "account":  "1. Use the self-service password reset link on the company intranet.\n2. Clear your browser cache and cookies, then try again.\n3. If MFA is failing, ensure your authenticator app time is correct.\n4. If still locked out, please reply to this ticket for further assistance.",
        "hardware": "1. If liquid damage occurred — power off immediately and do not turn back on.\n2. Disconnect all cables and the power source.\n3. Bring the device to the IT desk as soon as possible for inspection.\n4. If these steps do not resolve the issue, please reply to this ticket for further assistance.",
        "software": "1. Close the application fully using Task Manager if needed.\n2. Restart your computer and reopen the application.\n3. Check for any pending Windows or application updates.\n4. If the issue persists, please reply to this ticket for further assistance.",
        "other":    "1. Restart your device.\n2. Check if the issue affects other colleagues.\n3. Note any error messages or codes displayed.\n4. If the issue persists, please reply to this ticket for further assistance.",
    }.get(category, "Please contact the IT helpdesk directly with your ticket number.")


# ─────────────────────────────────────────────────────
# AGENT 3 — ESCALATION
# Builds a clean structured report for the senior team.
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
        f"\nREASON FOR ESCALATION:\n{state['escalation_reason']}\n"
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
        "triage_reasoning":  "",
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
        ("TKT-002", "I forgot my password and can't log into Outlook."),
        ("TKT-003", "The entire office internet is down. No one can work."),
        ("TKT-004", "I clicked a suspicious link and now see a ransom message."),
        ("TKT-005", "Microsoft Teams crashes every time I join a meeting."),
        ("TKT-006", "The CEO cannot access his email since this morning."),
    ]
    for tid, issue in tests:
        print(f"\n{'='*55}")
        print(f"  {tid}: {issue}")
        r = process_ticket(tid, issue)
        print(f"  Category  : {r['category']}  |  Priority : {r['priority']}")
        print(f"  Escalated : {r['escalated']}")
        print(f"  Reasoning : {r['triage_reasoning'][:90]}")
        print(f"  Resolution: {r['resolution'][:90]}...")