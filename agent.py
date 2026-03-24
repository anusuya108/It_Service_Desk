# agent.py — 3-agent LangGraph pipeline (fully upgraded)
# Upgrade 1: LLM-powered resolution (dynamic, not static templates)
# Upgrade 2: Real confidence score (keyword match strength)
# Upgrade 3: LLM-powered escalation decision (not just priority check)

import os
from typing import TypedDict
from dotenv import load_dotenv
from langchain_groq import ChatGroq
from langchain_core.messages import SystemMessage, HumanMessage
from langgraph.graph import StateGraph, END

from core import classify_issue, should_escalate

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


# ─────────────────────────────────────────────────────
# AGENT 1: TRIAGE
# Rule-based first. LLM corrects when confidence is low.
# ─────────────────────────────────────────────────────
def triage_agent(state: TicketState) -> TicketState:
    issue = state["user_issue"]

    rule_cat, rule_pri, reason, confidence = classify_issue(issue)

    final_cat = rule_cat
    final_pri = rule_pri

    # Use LLM when rules are uncertain
    if confidence < 0.7 or rule_cat == "other":
        try:
            response = llm.invoke([
                SystemMessage(content="""You are an IT ticket classifier.

Categories: hardware, software, network, account, other
Priority:   low, medium, high, critical

Category rules:
- wifi, vpn, internet, shared drive, remote → network
- password, login, access, locked out, mfa → account
- laptop, monitor, keyboard, mouse, printer, spill → hardware
- crash, freeze, error, outlook, teams, excel, app → software

Priority rules:
- critical: entire office down, data loss, ransomware, security breach
- high: one person fully blocked, physical damage, can't work at all
- medium: significant issue but workaround exists
- low: slow, cosmetic, how-to question

Respond ONLY in this exact format (no extra text):
category: <value>
priority: <value>"""),
                HumanMessage(content=f"Issue: {issue}")
            ]).content.lower().strip()

            llm_cat = "other"
            llm_pri = "medium"

            for c in ["hardware", "software", "network", "account", "other"]:
                if c in response:
                    llm_cat = c
                    break
            for p in ["critical", "high", "medium", "low"]:
                if p in response:
                    llm_pri = p
                    break

            if confidence < 0.6:
                final_cat = llm_cat
                final_pri = llm_pri
                reason = f"LLM classified (rule confidence too low: {confidence:.0%})"
                confidence = 0.75
            elif llm_cat != rule_cat:
                final_cat = llm_cat
                final_pri = llm_pri
                reason = f"LLM corrected rule ({rule_cat} → {llm_cat})"
                confidence = 0.78

        except Exception as e:
            reason += f" | LLM fallback failed: {str(e)[:40]}"

    return {
        **state,
        "category":   final_cat,
        "priority":   final_pri,
        "reason":     reason,
        "confidence": round(confidence, 2),
    }


# ─────────────────────────────────────────────────────
# AGENT 2: RESOLUTION
# UPGRADE: LLM generates a real step-by-step resolution.
# Not a static template — dynamic reasoning per ticket.
# ─────────────────────────────────────────────────────
def resolution_agent(state: TicketState) -> TicketState:
    issue    = state["user_issue"]
    category = state["category"]
    priority = state["priority"]

    # ── UPGRADE 1: LLM-powered resolution ─────────────
    try:
        resolution = llm.invoke([
            SystemMessage(content=f"""You are a Level-1 IT Support Engineer.
Your job is to provide clear, step-by-step troubleshooting for IT issues.

Ticket details:
- Category: {category}
- Priority: {priority}

Rules:
- Give 3-5 numbered steps the user can follow RIGHT NOW
- Be specific and practical (not generic)
- If the issue clearly cannot be fixed remotely (e.g. physical damage, liquid spill), 
  say so clearly and advise the user what to do instead
- Keep it under 120 words
- Do NOT say "I" or "we" — address the user directly"""),
            HumanMessage(content=f"Issue: {issue}")
        ]).content.strip()
    except Exception as e:
        # Fallback to basic templates if LLM fails
        fallback = {
            "network":  "1. Restart your router and device.\n2. Check all network cables.\n3. Try connecting to a different network.\n4. Contact the Network team if issue persists.",
            "account":  "1. Use the self-service password reset portal.\n2. Clear your browser cache and retry.\n3. If MFA is failing, contact the IAM team.\n4. Do not share your credentials.",
            "hardware": "1. Do NOT power on the device if liquid damage occurred.\n2. Disconnect power immediately.\n3. Bring the device to the IT desk for inspection.\n4. Backup data if accessible.",
            "software": "1. Close and restart the application.\n2. Clear the app cache or temp files.\n3. Check for pending updates.\n4. Reinstall if the issue persists.",
            "other":    "1. Restart your device.\n2. Check if the issue affects other users.\n3. Note any error messages.\n4. Contact the helpdesk with full details.",
        }
        resolution = fallback.get(category, "Contact the IT helpdesk for assistance.")

    # ── UPGRADE 3: LLM escalation decision ─────────────
    # Rule-based pre-check first (fast)
    rule_escalated, rule_reason = should_escalate(category, priority, issue)

    if rule_escalated:
        escalated    = True
        esc_reason   = rule_reason
    else:
        # Ask LLM to make the final escalation call
        try:
            esc_response = llm.invoke([
                SystemMessage(content="""You are an IT escalation manager.
Decide if this ticket needs to be escalated to Level 2 support.

Escalate if ANY of these are true:
- Cannot be solved remotely
- Affects multiple users
- Involves security, data loss, or compliance
- Requires physical hardware replacement
- User is a senior executive or VIP
- Issue has been unresolved for a long time

Respond ONLY in this exact format:
decision: YES or NO
reason: <one sentence explanation>"""),
                HumanMessage(content=f"Category: {category}\nPriority: {priority}\nIssue: {issue}\nProposed resolution: {resolution[:200]}")
            ]).content.strip().lower()

            escalated  = "decision: yes" in esc_response
            reason_line = [l for l in esc_response.split("\n") if "reason:" in l]
            esc_reason  = reason_line[0].replace("reason:", "").strip().capitalize() if reason_line else "Escalated by AI decision"

        except Exception:
            escalated  = False
            esc_reason = ""

    return {
        **state,
        "resolution":        resolution,
        "escalated":         escalated,
        "escalation_reason": esc_reason,
    }


# ─────────────────────────────────────────────────────
# AGENT 3: ESCALATION
# Builds a structured report for the senior team.
# ─────────────────────────────────────────────────────
def escalation_agent(state: TicketState) -> TicketState:
    if not state["escalated"]:
        return {**state, "escalation_report": ""}

    issue    = state["user_issue"].lower()
    category = state["category"]
    priority = state["priority"]

    team = (
        "SOC — Security Operations Centre"    if any(x in issue for x in ["ransom","breach","hacked","virus","malware"])
        else "NOC — Network Operations Centre" if category == "network"
        else "IAM — Identity & Access Mgmt"   if category == "account"
        else "Infrastructure Team"             if category == "hardware"
        else "Tier-2 Software Support"
    )

    sla = (
        "1 hour"          if priority == "critical"
        else "4 hours"    if priority == "high"
        else "1 business day"
    )

    report = f"""ESCALATION REPORT
{'═'*40}
Ticket ID  : {state['ticket_id']}
Category   : {category.upper()}
Priority   : {priority.upper()}
Assign to  : {team}
SLA Target : {sla}

ISSUE DESCRIPTION:
{state['user_issue']}

ESCALATION REASON:
{state['escalation_reason']}

L1 RESOLUTION ATTEMPTED:
{state['resolution'][:300]}

ACTION REQUIRED:
Please acknowledge this ticket within the SLA window and contact the user directly.
{'═'*40}"""

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
    graph.add_edge("triage",     "resolution")
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
        ("TKT-004", "I clicked a suspicious link and now see a ransom message."),
        ("TKT-005", "Microsoft Teams crashes every time I join a meeting."),
    ]

    for tid, issue in tests:
        print(f"\n{'='*55}")
        print(f"Ticket : {tid}")
        print(f"Issue  : {issue}")
        r = process_ticket(tid, issue)
        print(f"Category   : {r['category']}  |  Priority: {r['priority']}  |  Confidence: {r['confidence']:.0%}")
        print(f"Reason     : {r['reason']}")
        print(f"Escalated  : {r['escalated']}")
        print(f"Resolution : {r['resolution'][:120]}...")
        if r['escalated']:
            print(f"Esc Reason : {r['escalation_reason']}")