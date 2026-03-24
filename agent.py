# agent.py — 3-agent LangGraph pipeline
#
# What's fixed vs previous version:
#   - No raw errors ever reach the UI (all try/except handle silently)
#   - Fake confidence score REMOVED — replaced with honest "classification_method"
#   - Triage agent produces visible reasoning, not just labels
#   - Resolution agent uses LLM for dynamic step-by-step guidance
#   - Escalation agent uses LLM reasoning with context (impact, users, business)
#   - Clean fallbacks at every step — system never crashes

import os
from typing import TypedDict
from dotenv import load_dotenv
from langchain_groq import ChatGroq
from langchain_core.messages import SystemMessage, HumanMessage
from langgraph.graph import StateGraph, END

from core import classify_issue, get_team, get_sla

load_dotenv()

# ── LLM SETUP ────────────────────────────────────────
_llm = None

def get_llm():
    """Lazy LLM init — returns None silently if key is missing"""
    global _llm
    if _llm is not None:
        return _llm
    api_key = os.environ.get("GROQ_API_KEY", "").strip()
    if not api_key:
        return None
    try:
        _llm = ChatGroq(
            model="llama-3.3-70b-versatile",
            temperature=0,
            api_key=api_key
        )
        return _llm
    except Exception:
        return None


def call_llm(messages: list, fallback: str = "") -> str:
    """
    Safe LLM call — NEVER raises, NEVER leaks errors to UI.
    Returns fallback string if anything goes wrong.
    """
    try:
        llm = get_llm()
        if llm is None:
            return fallback
        return llm.invoke(messages).content.strip()
    except Exception:
        return fallback


# ── STATE ─────────────────────────────────────────────
class TicketState(TypedDict):
    ticket_id:             str
    user_issue:            str
    category:              str
    priority:              str
    classification_method: str   # "rule-based" | "llm-assisted" | "llm-classified"
    triage_reasoning:      str   # visible reasoning from triage agent
    resolution:            str
    escalated:             bool
    escalation_reason:     str
    escalation_report:     str


# ─────────────────────────────────────────────────────
# AGENT 1 — TRIAGE
# Classifies the ticket. Shows reasoning. No fake scores.
# ─────────────────────────────────────────────────────
def triage_agent(state: TicketState) -> TicketState:
    issue = state["user_issue"]

    rule_cat, rule_pri, rule_reason, match_strength = classify_issue(issue)

    # Strong rule match → trust it, no LLM needed
    if match_strength == "strong":
        return {
            **state,
            "category":             rule_cat,
            "priority":             rule_pri,
            "classification_method": "rule-based",
            "triage_reasoning":     f"Classified by keyword rules. {rule_reason}. Priority set to {rule_pri} based on issue signals.",
        }

    # Weak or no match → ask LLM to reason through it
    llm_prompt = call_llm([
        SystemMessage(content="""You are a senior IT support triage specialist.
Analyse the issue and classify it. Then explain your reasoning briefly.

Categories: hardware, software, network, account, other
Priority:   low, medium, high, critical

Priority guide:
- critical: affects entire office, data loss, security breach, ransomware
- high: user completely blocked from working, physical hardware damage
- medium: significant issue, workaround might exist
- low: minor inconvenience, how-to question, cosmetic issue

Respond ONLY in this exact format:
category: <value>
priority: <value>
reasoning: <2 sentences explaining your classification decision>"""),
        HumanMessage(content=f"Issue: {issue}")
    ])

    # Parse LLM response
    final_cat = rule_cat
    final_pri = rule_pri
    reasoning = rule_reason

    if llm_prompt:
        lines = {
            line.split(":")[0].strip(): ":".join(line.split(":")[1:]).strip()
            for line in llm_prompt.lower().splitlines()
            if ":" in line
        }

        for c in ["hardware","software","network","account","other"]:
            if c in lines.get("category",""):
                final_cat = c
                break

        for p in ["critical","high","medium","low"]:
            if p in lines.get("priority",""):
                final_pri = p
                break

        reasoning = lines.get("reasoning", rule_reason).capitalize()
        method    = "llm-classified" if match_strength == "none" else "llm-assisted"
    else:
        # LLM failed — fall back to rules silently
        method    = "rule-based (llm unavailable)"
        reasoning = f"Classified by keyword rules. {rule_reason}."

    return {
        **state,
        "category":             final_cat,
        "priority":             final_pri,
        "classification_method": method,
        "triage_reasoning":     reasoning,
    }


# ─────────────────────────────────────────────────────
# AGENT 2 — RESOLUTION
# LLM generates specific step-by-step guidance.
# Also decides escalation with reasoning (not just priority check).
# ─────────────────────────────────────────────────────
def resolution_agent(state: TicketState) -> TicketState:
    issue    = state["user_issue"]
    category = state["category"]
    priority = state["priority"]

    # ── LLM Resolution ────────────────────────────────
    resolution = call_llm([
        SystemMessage(content=f"""You are a Level-1 IT Support Engineer providing remote support.

Ticket classification:
- Category: {category}
- Priority: {priority}

Your task: Write specific, actionable troubleshooting steps for this exact issue.

Rules:
- Give exactly 4-5 numbered steps
- Be specific to THIS issue, not generic advice
- If physical damage is involved (liquid spill, cracked screen), instruct user NOT to power on and to bring device to IT desk
- If the issue clearly requires physical presence, say so directly
- End with: "If these steps don't resolve the issue, contact the IT helpdesk with your ticket number."
- Maximum 150 words total"""),
        HumanMessage(content=f"Issue: {issue}")
    ], fallback=_fallback_resolution(category))

    # ── LLM Escalation Decision ────────────────────────
    # Ask LLM to reason about escalation with full context
    esc_response = call_llm([
        SystemMessage(content="""You are an IT escalation manager reviewing a support ticket.

Decide whether this needs Level-2 escalation. Consider:
1. Can this realistically be resolved remotely by Level-1?
2. Does it affect multiple users or business-critical systems?
3. Is there a security, compliance, or data risk?
4. Does it require physical access or specialist skills?
5. Is the user completely unable to work?

Respond ONLY in this exact format:
decision: YES or NO
reason: <one clear sentence explaining the decision>"""),
        HumanMessage(content=f"""Category: {category}
Priority: {priority}
Issue: {issue}
Proposed L1 resolution: {resolution[:250]}""")
    ])

    # Parse escalation response
    escalated  = False
    esc_reason = ""

    if esc_response:
        resp_lower = esc_response.lower()
        escalated  = "decision: yes" in resp_lower
        for line in esc_response.splitlines():
            if line.lower().startswith("reason:"):
                esc_reason = line.split(":",1)[1].strip().capitalize()
                break

    # Override: always escalate critical regardless of LLM
    if priority == "critical":
        escalated  = True
        esc_reason = esc_reason or "Critical priority — immediate senior attention required"

    # Fallback if LLM gave no response
    if not esc_response:
        if priority in ["critical","high"]:
            escalated  = True
            esc_reason = "Escalated based on priority level (LLM unavailable)"

    return {
        **state,
        "resolution":        resolution,
        "escalated":         escalated,
        "escalation_reason": esc_reason,
    }


def _fallback_resolution(category: str) -> str:
    """Used only when LLM is completely unavailable"""
    return {
        "network":  "1. Restart your router and device.\n2. Check all network cables are connected.\n3. Try connecting via a mobile hotspot to isolate the issue.\n4. Flush DNS: open Command Prompt and run ipconfig /flushdns.\n5. If issue persists, contact the Network team with your ticket number.",
        "account":  "1. Use the self-service password reset portal (link in company intranet).\n2. Clear your browser cache and cookies, then retry.\n3. If MFA is failing, check your authenticator app is showing the correct time.\n4. Try a different browser or incognito mode.\n5. If still locked out, contact the IAM team with your ticket number.",
        "hardware": "1. If liquid damage occurred — power off immediately and do NOT turn back on.\n2. Disconnect the power cable and remove the battery if possible.\n3. Do not attempt to dry with heat (no hairdryer).\n4. Bring the device to the IT desk as soon as possible.\n5. Contact the IT helpdesk with your ticket number to arrange a loan device.",
        "software": "1. Close the application completely (check Task Manager to force quit if needed).\n2. Restart your computer and try again.\n3. Check for pending Windows or application updates.\n4. Clear the application cache or temp files.\n5. If issue persists, uninstall and reinstall the application.",
        "other":    "1. Restart your device.\n2. Check if the issue also affects colleagues nearby.\n3. Note any error messages or error codes shown.\n4. Take a screenshot if possible.\n5. Contact the IT helpdesk with your ticket number and the screenshot.",
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
        f"{'═'*42}\n"
        f"Ticket ID  : {state['ticket_id']}\n"
        f"Category   : {state['category'].upper()}\n"
        f"Priority   : {state['priority'].upper()}\n"
        f"Assign to  : {team}\n"
        f"SLA Target : {sla}\n"
        f"\nISSUE:\n{state['user_issue']}\n"
        f"\nESCALATION REASON:\n{state['escalation_reason']}\n"
        f"\nL1 RESOLUTION ATTEMPTED:\n{state['resolution'][:400]}\n"
        f"\nACTION REQUIRED:\n"
        f"Please acknowledge within the SLA window and contact the user directly.\n"
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
    initial_state: TicketState = {
        "ticket_id":             ticket_id,
        "user_issue":            user_issue,
        "category":              "",
        "priority":              "",
        "classification_method": "",
        "triage_reasoning":      "",
        "resolution":            "",
        "escalated":             False,
        "escalation_reason":     "",
        "escalation_report":     "",
    }
    return build_graph().invoke(initial_state)


# ── TEST ──────────────────────────────────────────────
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
        print(f"Category : {r['category']}  | Priority : {r['priority']}")
        print(f"Method   : {r['classification_method']}")
        print(f"Reasoning: {r['triage_reasoning']}")
        print(f"Escalated: {r['escalated']}  | {r['escalation_reason']}")
        print(f"Resolution (first 100 chars): {r['resolution'][:100]}...")