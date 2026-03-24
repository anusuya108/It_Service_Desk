# agent.py — 3-agent LangGraph IT Service Desk
#
# Architecture decisions made to hit 85%+ accuracy:
#   1. Rules handle strong matches (>= 2 keyword hits) — fast, reliable
#   2. LLM only called for weak/no matches — avoids over-engineering
#   3. LLM given strict structured output format for clean parsing
#   4. Category cross-check: if LLM and rules disagree, LLM wins for weak matches
#   5. Priority: context-first (scope, impact, role) before keyword matching
#   6. Escalation: security/critical forced by rules; LLM decides edge cases
#   7. Memory: past similar tickets improve resolution quality
#   8. Zero internals exposed to user — all errors handled silently

import os
from typing import TypedDict
from dotenv import load_dotenv
from langchain_groq import ChatGroq
from langchain_core.messages import SystemMessage, HumanMessage
from langgraph.graph import StateGraph, END

from core import classify_issue, should_escalate_rules, get_team, get_sla
from memory import find_similar, save_ticket

load_dotenv()

# ── LLM (lazy init, silent fail) ──────────────────────
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

def _call(messages, fallback=""):
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
    priority_reason:   str
    triage_reasoning:  str
    similar_past:      str
    resolution:        str
    escalated:         bool
    escalation_reason: str
    escalation_report: str


# ─────────────────────────────────────────────────────
# AGENT 1 — TRIAGE
# Target: 85%+ category accuracy, 80%+ priority accuracy
#
# Strategy:
#   - Rules classify with strong matches (reliable, fast)
#   - LLM corrects weak/no matches with structured prompt
#   - Priority is context-aware (scope > role > severity > default)
#   - Triage reasoning is always clean and user-facing
# ─────────────────────────────────────────────────────
def triage_agent(state: TicketState) -> TicketState:
    issue = state["user_issue"]
    rule_cat, rule_pri, priority_reason, match_strength = classify_issue(issue)

    final_cat = rule_cat
    final_pri = rule_pri

    # ── LLM correction for weak/no matches ────────────
    if match_strength in ("weak", "none"):
        resp = _call([
            SystemMessage(content="""You are a senior IT support triage specialist.
Classify the IT issue below. Be precise.

CATEGORIES (pick exactly one):
- hardware: physical devices, laptops, monitors, keyboards, printers, webcams
- software: applications, crashes, errors, ERP, Teams, Excel, Outlook, browser
- network: internet, WiFi, VPN, shared drives, file shares, connectivity
- account: passwords, login, access, MFA, account creation, permissions
- other: security incidents, ransomware, file transfers, antivirus alerts

PRIORITY (pick exactly one):
- critical: office-wide outage, data loss, ransomware, security breach, ERP down
- high: user fully blocked, executive affected, physical damage, multi-user impact
- medium: single user affected, partial workaround exists
- low: minor issue, how-to question, cosmetic, slow but working

ESCALATION:
- YES if: cannot fix remotely, security risk, critical/high priority, physical repair needed
- NO if: standard L1 fix available

Respond ONLY in this exact format, no other text:
category: <value>
priority: <value>
escalate: YES or NO
reasoning: <one sentence why>"""),
            HumanMessage(content=f"Issue: {issue}")
        ])

        if resp:
            lines = {}
            for line in resp.lower().splitlines():
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

            raw_reason = lines.get("reasoning","")
            if raw_reason:
                priority_reason = raw_reason.capitalize()

    # ── Generate clean user-facing triage reasoning ───
    triage_reasoning = _call([
        SystemMessage(content="""You are an IT support triage specialist.
Write ONE professional sentence explaining this ticket classification to the user.
Do not mention keywords, rules, algorithms, AI, or LLM.
Format: "This ticket has been classified as [category] with [priority] priority because [clear human reason]." """),
        HumanMessage(content=f"Category: {final_cat}, Priority: {final_pri}, Issue: {issue}")
    ], fallback=f"This ticket has been classified as {final_cat} with {final_pri} priority. {priority_reason}")

    # ── Find similar past ticket ───────────────────────
    similar    = find_similar(issue, final_cat)
    similar_past = ""
    if similar:
        similar_past = (
            f"A similar past issue was resolved as follows: "
            f"\"{similar['issue'].title()}\" — {similar['resolution']}"
        )

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
# Target: 85%+ escalation accuracy
#
# Strategy:
#   - Critical → instant escalation, no L1 steps (correct for office outages)
#   - Security → instant escalation (ransomware, account compromise)
#   - Others → LLM decides escalation with 5 context factors
#   - Resolution is fully LLM-generated, uses past similar case context
#   - Memory saves every ticket for future reference
# ─────────────────────────────────────────────────────
def resolution_agent(state: TicketState) -> TicketState:
    issue    = state["user_issue"]
    category = state["category"]
    priority = state["priority"]
    similar  = state["similar_past"]

    # ── Rule-based escalation override ────────────────
    rule_esc, rule_reason = should_escalate_rules(category, priority, issue)
    if rule_esc:
        resolution = (
            "This issue has been identified as a critical or security incident. "
            "It is being escalated immediately to the senior support team. "
            "A specialist will contact you within the SLA window. "
            "Please do not attempt further troubleshooting."
        )
        save_ticket(state["ticket_id"], issue, category, priority, resolution, True)
        return {
            **state,
            "resolution":        resolution,
            "escalated":         True,
            "escalation_reason": rule_reason,
        }

    # ── LLM-generated resolution ──────────────────────
    past_context = f"\n\nRELEVANT PAST CASE (use if helpful):\n{similar}" if similar else ""

    resolution = _call([
        SystemMessage(content=f"""You are a Level-1 IT Support Engineer providing remote support.

Ticket:
- Category: {category}
- Priority: {priority}{past_context}

Write specific, actionable troubleshooting steps for this exact issue.
Rules:
- Exactly 4 numbered steps
- Specific to THIS issue — not generic advice
- If physical damage (liquid, cracked): step 1 must be "Power off immediately. Do not turn back on."
- Use the past case context if relevant
- Final line always: "If these steps do not resolve the issue, please reply to this ticket."
- Max 130 words. No mention of AI or systems."""),
        HumanMessage(content=f"Issue: {issue}")
    ], fallback=_fallback_resolution(category))

    # ── LLM escalation decision ────────────────────────
    esc_resp = _call([
        SystemMessage(content="""You are an IT escalation manager.
Decide if this ticket needs Level-2 escalation.

Escalate YES if ANY apply:
- Cannot be realistically fixed remotely
- Requires physical hardware repair or replacement
- Affects multiple users or shared systems
- Security, compliance, or data risk present
- Senior executive or VIP affected
- L1 steps are unlikely to resolve it

Respond ONLY in this exact format:
decision: YES or NO
reason: <one sentence>"""),
        HumanMessage(content=f"Category: {category}\nPriority: {priority}\nIssue: {issue}\nProposed resolution: {resolution[:250]}")
    ])

    escalated  = False
    esc_reason = ""
    if esc_resp:
        escalated = "decision: yes" in esc_resp.lower()
        for line in esc_resp.splitlines():
            if line.lower().startswith("reason:"):
                esc_reason = line.split(":",1)[1].strip().capitalize()
                break
    else:
        if priority == "high":
            escalated  = True
            esc_reason = "High priority — escalated per standard policy."

    save_ticket(state["ticket_id"], issue, category, priority, resolution, escalated)

    return {
        **state,
        "resolution":        resolution,
        "escalated":         escalated,
        "escalation_reason": esc_reason,
    }


def _fallback_resolution(category: str) -> str:
    return {
        "network":  "1. Restart your router and device.\n2. Check all network cables.\n3. Try a mobile hotspot to confirm if the issue is local.\n4. If the issue persists, please reply to this ticket.",
        "account":  "1. Use the self-service password reset link on the company intranet.\n2. Clear your browser cache and try again.\n3. Ensure your authenticator app time is synced.\n4. If still locked out, please reply to this ticket.",
        "hardware": "1. Power off the device immediately.\n2. Disconnect all cables and power.\n3. Bring the device to the IT desk for inspection.\n4. If the issue persists, please reply to this ticket.",
        "software": "1. Close the application fully via Task Manager.\n2. Restart your computer.\n3. Check for pending updates.\n4. If the issue persists, please reply to this ticket.",
        "other":    "1. Note any error messages shown.\n2. Take a screenshot if possible.\n3. Check if colleagues are affected.\n4. If the issue persists, please reply to this ticket.",
    }.get(category, "Please contact the IT helpdesk with your ticket number.")


# ─────────────────────────────────────────────────────
# AGENT 3 — ESCALATION
# Builds a structured report for the senior team
# ─────────────────────────────────────────────────────
def escalation_agent(state: TicketState) -> TicketState:
    if not state["escalated"]:
        return {**state, "escalation_report": ""}

    team = get_team(state["category"], state["user_issue"])
    sla  = get_sla(state["priority"])

    report = (
        f"ESCALATION REPORT\n"
        f"{'═'*42}\n"
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
        f"Acknowledge within SLA window. Contact the user directly.\n"
        f"{'═'*42}"
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


# ── QUICK TEST ────────────────────────────────────────
if __name__ == "__main__":
    tests = [
        ("TKT-001", "My laptop won't turn on after I spilled water on it."),
        ("TKT-002", "I forgot my password and can't log into Outlook."),
        ("TKT-003", "The entire office internet is down. No one can work."),
        ("TKT-006", "Our ERP system is completely down. All staff are affected."),
        ("TKT-011", "I clicked a suspicious link and now see a ransom message."),
        ("TKT-015", "The CEO cannot access his email since this morning."),
    ]
    for tid, issue in tests:
        print(f"\n{'='*60}")
        print(f"  {tid}: {issue}")
        r = process_ticket(tid, issue)
        print(f"  Category  : {r['category']}  | Priority : {r['priority']}")
        print(f"  Reason    : {r['priority_reason']}")
        print(f"  Escalated : {r['escalated']}")
        print(f"  Resolution: {r['resolution'][:80]}...")