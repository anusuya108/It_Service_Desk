"""
IT Service Desk — 3-Agent LangGraph System
LLM: Groq (free, fast)
Agent: Triage → Resolution → Escalation
"""

import os
from typing import TypedDict, Annotated, Literal
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from langchain_groq import ChatGroq
from langgraph.graph import StateGraph, END
from langgraph.graph.message import add_messages
from dotenv import load_dotenv

load_dotenv()


# ─────────────────────────────────────────────────────────────
# 1. SHARED STATE  —  the "clipboard" passed between all agents
# ─────────────────────────────────────────────────────────────

class TicketState(TypedDict):
    messages:           Annotated[list, add_messages]
    ticket_id:          str
    user_issue:         str
    category:           str   # hardware / software / network / account / other
    priority:           str   # low / medium / high / critical
    resolution:         str
    escalated:          bool
    escalation_reason:  str
    current_agent:      str


# ─────────────────────────────────────────────────────────────
# 2. LLM  —  swap model name for a different Groq model
# ─────────────────────────────────────────────────────────────

llm = ChatGroq(model="llama-3.3-70b-versatile", temperature=0, 
GROQ_API_KEY = os.getenv("GROQ_API_KEY"))


# ─────────────────────────────────────────────────────────────
# 3. AGENT 1 — TRIAGE
# ─────────────────────────────────────────────────────────────

def triage_agent(state: TicketState) -> TicketState:
    print(f"\n{'='*55}")
    print(f"[TRIAGE] Ticket: {state['ticket_id']}")
    print(f"  Issue: {state['user_issue'][:80]}")

    system_prompt = """You are an IT Service Desk Triage Agent.

Analyse the user's IT issue and classify it.

Reply in EXACTLY this format — no extra text, no explanation:
CATEGORY: <hardware|software|network|account|other>
PRIORITY: <low|medium|high|critical>

Priority rules:
- critical : production system down, data loss, active security breach, 50+ users affected
- high     : multiple users blocked, business process stopped, no workaround
- medium   : single user affected, workaround exists
- low      : cosmetic issue, how-to question, minor inconvenience

Category rules:
- hardware : physical device issues (laptop, printer, monitor, keyboard, mouse)
- software : application crashes, errors, installation, configuration
- network  : internet, VPN, Wi-Fi, file share, DNS
- account  : passwords, permissions, new user setup, MFA
- other    : security incidents, data requests, general queries
"""

    response = llm.invoke([
        SystemMessage(content=system_prompt),
        HumanMessage(content=f"User issue: {state['user_issue']}")
    ])

    category = "other"
    priority  = "medium"

    for line in response.content.strip().split("\n"):
        line = line.strip()
        if line.upper().startswith("CATEGORY:"):
            category = line.split(":", 1)[1].strip().lower()
        elif line.upper().startswith("PRIORITY:"):
            priority = line.split(":", 1)[1].strip().lower()

    # Validate
    valid_cats = {"hardware", "software", "network", "account", "other"}
    valid_pris = {"low", "medium", "high", "critical"}
    if category not in valid_cats: category = "other"
    if priority  not in valid_pris: priority  = "medium"

    print(f"  → Category: {category.upper()}   Priority: {priority.upper()}")

    return {
        **state,
        "category":      category,
        "priority":      priority,
        "current_agent": "triage",
        "messages":      state["messages"] + [
            AIMessage(content=f"[Triage] Category={category}, Priority={priority}")
        ],
    }


# ─────────────────────────────────────────────────────────────
# 4. AGENT 2 — RESOLUTION
# ─────────────────────────────────────────────────────────────

def resolution_agent(state: TicketState) -> TicketState:
    print(f"\n[RESOLUTION] Attempting to resolve {state['ticket_id']} ...")

    system_prompt = f"""You are an IT Support Resolution Agent (Level 1).

Ticket details:
  Category : {state['category']}
  Priority : {state['priority']}

You have access to standard IT knowledge and can resolve most common issues remotely.

Instructions:
1. If you CAN resolve the issue:
   - Provide a clear numbered step-by-step solution
   - Keep it simple — write for a non-technical user
   - End with: "Please reply if the issue persists."

2. If you CANNOT resolve the issue (requires physical access, senior admin rights,
   vendor involvement, security investigation, or priority is critical):
   - Start your ENTIRE response with exactly: ESCALATE: <one-line reason>
   - Do not add anything else

Cannot resolve examples:
- Physical hardware damage (spilled liquid, broken screen)
- Active ransomware / security breach
- Server or database outage affecting many users
- Requires senior admin or vendor access
"""

    response = llm.invoke([
        SystemMessage(content=system_prompt),
        HumanMessage(content=f"User issue: {state['user_issue']}")
    ])

    resolution_text = response.content.strip()
    needs_escalation = resolution_text.upper().startswith("ESCALATE:")

    print(f"  → Escalate: {needs_escalation}")

    return {
        **state,
        "resolution":    resolution_text,
        "escalated":     needs_escalation,
        "current_agent": "resolution",
        "messages":      state["messages"] + [
            AIMessage(content=f"[Resolution] {resolution_text}")
        ],
    }


# ─────────────────────────────────────────────────────────────
# 5. AGENT 3 — ESCALATION
# ─────────────────────────────────────────────────────────────

def escalation_agent(state: TicketState) -> TicketState:
    print(f"\n[ESCALATION] Creating escalation report for {state['ticket_id']} ...")

    # Team routing map
    team_map = {
        "hardware": "Infrastructure & Desktop Support Team",
        "network":  "Network Operations Centre (NOC)",
        "account":  "Identity & Access Management (IAM) Team",
        "software": "Tier-2 Application Support Team",
        "other":    "Security Operations Centre (SOC)",
    }

    sla_map = {
        "critical": "1 hour",
        "high":     "4 hours",
        "medium":   "1 business day",
        "low":      "3 business days",
    }

    assigned_team = team_map.get(state["category"], "Tier-2 Support Team")
    sla_target    = sla_map.get(state["priority"], "1 business day")

    system_prompt = f"""You are an IT Escalation Manager.

A Level-1 ticket has been escalated because it could not be resolved remotely.

Ticket info:
  Ticket ID      : {state['ticket_id']}
  Category       : {state['category']}
  Priority       : {state['priority']}
  Assigned team  : {assigned_team}
  SLA target     : {sla_target}
  L1 agent note  : {state['resolution']}

Write a professional escalation summary with these 4 sections:
1. ISSUE SUMMARY     — one paragraph describing the problem
2. REASON ESCALATED  — why L1 could not resolve it
3. RECOMMENDED ACTION — what the senior team should do first
4. SLA & ASSIGNMENT  — team assigned and response time required

Keep it concise and professional.
"""

    response = llm.invoke([
        SystemMessage(content=system_prompt),
        HumanMessage(content=f"Original user issue: {state['user_issue']}")
    ])

    escalation_text = response.content.strip()
    print(f"  → Escalation report written. Assigned to: {assigned_team}")

    return {
        **state,
        "escalation_reason": escalation_text,
        "current_agent":     "escalation",
        "messages":          state["messages"] + [
            AIMessage(content=f"[Escalation] {escalation_text}")
        ],
    }


# ─────────────────────────────────────────────────────────────
# 6. ROUTING FUNCTIONS
# ─────────────────────────────────────────────────────────────

def route_after_triage(state: TicketState) -> Literal["resolution_agent"]:
    return "resolution_agent"


def route_after_resolution(state: TicketState) -> Literal["escalation_agent", "__end__"]:
    return "escalation_agent" if state.get("escalated") else "__end__"


# ─────────────────────────────────────────────────────────────
# 7. BUILD THE GRAPH
# ─────────────────────────────────────────────────────────────

def build_graph():
    graph = StateGraph(TicketState)

    graph.add_node("triage_agent",     triage_agent)
    graph.add_node("resolution_agent", resolution_agent)
    graph.add_node("escalation_agent", escalation_agent)

    graph.set_entry_point("triage_agent")
    graph.add_conditional_edges("triage_agent",     route_after_triage)
    graph.add_conditional_edges("resolution_agent", route_after_resolution)
    graph.add_edge("escalation_agent", END)

    return graph.compile()


# ─────────────────────────────────────────────────────────────
# 8. PUBLIC FUNCTION — called by app.py and evaluate.py
# ─────────────────────────────────────────────────────────────

def process_ticket(ticket_id: str, user_issue: str) -> dict:
    """
    Run the full 3-agent pipeline for one ticket.
    Returns the final state dict with all fields populated.
    """
    app = build_graph()

    initial_state: TicketState = {
        "messages":          [HumanMessage(content=user_issue)],
        "ticket_id":         ticket_id,
        "user_issue":        user_issue,
        "category":          "",
        "priority":          "",
        "resolution":        "",
        "escalated":         False,
        "escalation_reason": "",
        "current_agent":     "none",
    }

    return app.invoke(initial_state)


# ─────────────────────────────────────────────────────────────
# 9. QUICK TERMINAL TEST
# ─────────────────────────────────────────────────────────────

if __name__ == "__main__":
    test_tickets = [
        ("TKT-001", "My laptop won't turn on after I spilled coffee on it."),
        ("TKT-002", "I forgot my Outlook password and I'm locked out."),
        ("TKT-003", "The entire office internet is down. Nobody can work."),
    ]

    for tid, issue in test_tickets:
        result = process_ticket(tid, issue)

        print(f"\n{'─'*55}")
        print(f"RESULT FOR {result['ticket_id']}")
        print(f"  Category  : {result['category']}")
        print(f"  Priority  : {result['priority']}")
        print(f"  Escalated : {result['escalated']}")
        if result["escalated"]:
            print(f"  Report    :\n{result['escalation_reason'][:300]}...")
        else:
            print(f"  Resolution:\n{result['resolution'][:300]}...")