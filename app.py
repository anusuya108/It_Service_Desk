"""
IT Service Desk - Streamlit Web UI
Run with: streamlit run app.py
"""

import streamlit as st
import time
from agent import process_ticket

# ─────────────────────────────────────────────
# PAGE CONFIG
# ─────────────────────────────────────────────

st.set_page_config(
    page_title="IT Service Desk",
    page_icon="🖥️",
    layout="centered"
)

# ─────────────────────────────────────────────
# CUSTOM CSS
# ─────────────────────────────────────────────

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;500&family=DM+Sans:wght@300;400;500;600&display=swap');

html, body, [class*="css"] {
    font-family: 'DM Sans', sans-serif;
}

/* Dark industrial background */
.stApp {
    background-color: #0f1117;
    color: #e2e8f0;
}

/* Hide default streamlit header */
#MainMenu, footer, header { visibility: hidden; }

/* Custom header */
.desk-header {
    text-align: center;
    padding: 2.5rem 0 1.5rem;
    border-bottom: 1px solid #1e2533;
    margin-bottom: 2rem;
}
.desk-header h1 {
    font-family: 'JetBrains Mono', monospace;
    font-size: 1.6rem;
    font-weight: 500;
    color: #f1f5f9;
    letter-spacing: -0.02em;
    margin: 0;
}
.desk-header p {
    font-size: 0.85rem;
    color: #64748b;
    margin: 6px 0 0;
    font-weight: 300;
}

/* Ticket input area */
.stTextArea textarea {
    background-color: #161b27 !important;
    border: 1px solid #1e2d40 !important;
    border-radius: 10px !important;
    color: #e2e8f0 !important;
    font-family: 'DM Sans', sans-serif !important;
    font-size: 0.95rem !important;
    padding: 14px 16px !important;
    resize: none !important;
}
.stTextArea textarea:focus {
    border-color: #3b82f6 !important;
    box-shadow: 0 0 0 3px rgba(59,130,246,0.1) !important;
}

/* Submit button */
.stButton > button {
    background: #3b82f6 !important;
    color: white !important;
    border: none !important;
    border-radius: 8px !important;
    padding: 0.6rem 2rem !important;
    font-family: 'DM Sans', sans-serif !important;
    font-size: 0.9rem !important;
    font-weight: 500 !important;
    width: 100% !important;
    transition: all 0.2s !important;
}
.stButton > button:hover {
    background: #2563eb !important;
    transform: translateY(-1px) !important;
}

/* Agent step cards */
.agent-card {
    background: #161b27;
    border: 1px solid #1e2d40;
    border-radius: 12px;
    padding: 1.2rem 1.4rem;
    margin: 0.6rem 0;
    position: relative;
    overflow: hidden;
}
.agent-card::before {
    content: '';
    position: absolute;
    left: 0; top: 0; bottom: 0;
    width: 3px;
    border-radius: 3px 0 0 3px;
}
.agent-card.triage::before   { background: #f59e0b; }
.agent-card.resolution::before { background: #3b82f6; }
.agent-card.escalation::before { background: #ef4444; }
.agent-card.resolved::before   { background: #10b981; }

.agent-label {
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.7rem;
    font-weight: 500;
    letter-spacing: 0.08em;
    text-transform: uppercase;
    margin-bottom: 8px;
}
.agent-card.triage .agent-label   { color: #f59e0b; }
.agent-card.resolution .agent-label { color: #3b82f6; }
.agent-card.escalation .agent-label { color: #ef4444; }
.agent-card.resolved .agent-label   { color: #10b981; }

.agent-content {
    color: #cbd5e1;
    font-size: 0.9rem;
    line-height: 1.6;
}

/* Priority badges */
.badge {
    display: inline-block;
    padding: 2px 10px;
    border-radius: 20px;
    font-size: 0.75rem;
    font-weight: 500;
    font-family: 'JetBrains Mono', monospace;
    margin: 2px 3px;
}
.badge-critical { background: #450a0a; color: #fca5a5; border: 1px solid #7f1d1d; }
.badge-high     { background: #431407; color: #fdba74; border: 1px solid #7c2d12; }
.badge-medium   { background: #1e3a5f; color: #93c5fd; border: 1px solid #1e40af; }
.badge-low      { background: #14532d; color: #86efac; border: 1px solid #166534; }
.badge-cat      { background: #1e1b4b; color: #a5b4fc; border: 1px solid #3730a3; }

/* Metrics row */
.metrics-row {
    display: flex;
    gap: 12px;
    margin: 1.2rem 0;
}
.metric-box {
    flex: 1;
    background: #161b27;
    border: 1px solid #1e2d40;
    border-radius: 10px;
    padding: 1rem;
    text-align: center;
}
.metric-val {
    font-family: 'JetBrains Mono', monospace;
    font-size: 1.4rem;
    font-weight: 500;
    color: #f1f5f9;
}
.metric-lbl {
    font-size: 0.75rem;
    color: #475569;
    margin-top: 3px;
    font-weight: 300;
}

/* History item */
.history-item {
    background: #161b27;
    border: 1px solid #1e2d40;
    border-radius: 8px;
    padding: 0.9rem 1.1rem;
    margin: 0.4rem 0;
    display: flex;
    align-items: center;
    gap: 12px;
    cursor: pointer;
    transition: border-color 0.15s;
}
.history-item:hover { border-color: #334155; }
.history-id {
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.75rem;
    color: #475569;
    min-width: 60px;
}
.history-issue {
    flex: 1;
    font-size: 0.85rem;
    color: #94a3b8;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
}

/* Section label */
.section-lbl {
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.68rem;
    font-weight: 500;
    letter-spacing: 0.1em;
    text-transform: uppercase;
    color: #475569;
    margin: 1.5rem 0 0.8rem;
}

/* Divider */
hr { border-color: #1e2533 !important; }

/* Spinner override */
.stSpinner > div { border-top-color: #3b82f6 !important; }

/* Selectbox */
.stSelectbox select, div[data-baseweb="select"] {
    background: #161b27 !important;
    border-color: #1e2d40 !important;
    color: #e2e8f0 !important;
}
</style>
""", unsafe_allow_html=True)


# ─────────────────────────────────────────────
# SESSION STATE
# ─────────────────────────────────────────────

if "history" not in st.session_state:
    st.session_state.history = []
if "ticket_counter" not in st.session_state:
    st.session_state.ticket_counter = 1
if "last_result" not in st.session_state:
    st.session_state.last_result = None


# ─────────────────────────────────────────────
# HELPER FUNCTIONS
# ─────────────────────────────────────────────

def priority_badge(priority: str) -> str:
    cls = f"badge-{priority.lower()}" if priority.lower() in ["critical","high","medium","low"] else "badge-medium"
    return f'<span class="badge {cls}">{priority.upper()}</span>'

def category_badge(category: str) -> str:
    return f'<span class="badge badge-cat">{category}</span>'

def render_agent_card(css_class: str, label: str, content: str):
    st.markdown(f"""
    <div class="agent-card {css_class}">
        <div class="agent-label">{label}</div>
        <div class="agent-content">{content}</div>
    </div>
    """, unsafe_allow_html=True)


# ─────────────────────────────────────────────
# HEADER
# ─────────────────────────────────────────────

st.markdown("""
<div class="desk-header">
    <h1>// IT Service Desk</h1>
    <p>3-agent AI pipeline &nbsp;·&nbsp; Triage → Resolution → Escalation</p>
</div>
""", unsafe_allow_html=True)


# ─────────────────────────────────────────────
# SAMPLE TICKETS (quick fill)
# ─────────────────────────────────────────────

st.markdown('<div class="section-lbl">Quick samples</div>', unsafe_allow_html=True)

samples = {
    "Select a sample...": "",
    "💧 Spilled water on laptop": "My laptop won't turn on after I spilled water on it.",
    "🔑 Forgot password": "I forgot my password and can't log into Outlook.",
    "🌐 Office internet down": "The entire office internet is down. No one can work.",
    "🦠 Ransomware screen": "I clicked a suspicious link and now see a ransom message on screen.",
    "📺 Monitor flickering": "My monitor keeps flickering and goes black randomly.",
    "🔒 Strange login": "Someone is logged in as me on a machine I don't recognise.",
}

selected = st.selectbox("", list(samples.keys()), label_visibility="collapsed")


# ─────────────────────────────────────────────
# TICKET INPUT
# ─────────────────────────────────────────────

st.markdown('<div class="section-lbl">Describe your issue</div>', unsafe_allow_html=True)

prefill = samples[selected] if selected != "Select a sample..." else ""
user_issue = st.text_area(
    "",
    value=prefill,
    height=110,
    placeholder="e.g. My laptop won't start after the Windows update...",
    label_visibility="collapsed"
)

submit = st.button("Submit Ticket →")


# ─────────────────────────────────────────────
# PROCESS TICKET
# ─────────────────────────────────────────────

if submit:
    if not user_issue.strip():
        st.warning("Please describe your issue first.")
    else:
        ticket_id = f"TKT-{st.session_state.ticket_counter:03d}"
        st.session_state.ticket_counter += 1

        # Show live agent progress
        st.markdown('<div class="section-lbl">Agent pipeline</div>', unsafe_allow_html=True)

        progress_placeholder = st.empty()

        with progress_placeholder.container():
            with st.spinner("Agent 1 — Triage: classifying your ticket..."):
                time.sleep(0.3)

        result = None
        with st.spinner("Running all 3 agents..."):
            result = process_ticket(ticket_id, user_issue)

        progress_placeholder.empty()

        # Store in history
        st.session_state.history.insert(0, {
            "ticket_id": ticket_id,
            "issue": user_issue,
            "result": result
        })
        st.session_state.last_result = result

        # ── Metrics row ──────────────────────────────
        escalated_text = "Yes" if result["escalated"] else "No"
        st.markdown(f"""
        <div class="metrics-row">
            <div class="metric-box">
                <div class="metric-val">{ticket_id}</div>
                <div class="metric-lbl">Ticket ID</div>
            </div>
            <div class="metric-box">
                <div class="metric-val">{result['category'].upper()}</div>
                <div class="metric-lbl">Category</div>
            </div>
            <div class="metric-box">
                <div class="metric-val">{result['priority'].upper()}</div>
                <div class="metric-lbl">Priority</div>
            </div>
            <div class="metric-box">
                <div class="metric-val">{escalated_text}</div>
                <div class="metric-lbl">Escalated</div>
            </div>
        </div>
        """, unsafe_allow_html=True)

        # ── Agent cards ──────────────────────────────
        st.markdown('<div class="section-lbl">Agent outputs</div>', unsafe_allow_html=True)

        # Triage card
        render_agent_card(
            "triage",
            "Agent 1 — Triage",
            f"Category: {category_badge(result['category'])} &nbsp; Priority: {priority_badge(result['priority'])}"
        )

        # Resolution card
        if result["escalated"]:
            resolution_preview = result["resolution"].replace("ESCALATE:", "").strip()[:300]
            render_agent_card(
                "escalation",
                "Agent 2 — Resolution  (could not resolve)",
                f"Could not resolve remotely. Reason: <em>{resolution_preview}...</em>"
            )
            # Escalation card
            escalation_text = result["escalation_reason"][:500].replace("\n", "<br>")
            render_agent_card(
                "escalation",
                "Agent 3 — Escalation Report",
                escalation_text
            )
        else:
            resolution_text = result["resolution"][:500].replace("\n", "<br>")
            render_agent_card(
                "resolved",
                "Agent 2 — Resolution  (resolved)",
                resolution_text
            )
            render_agent_card(
                "resolved",
                "Agent 3 — Escalation",
                "Not required. Issue resolved at Level 1."
            )


# ─────────────────────────────────────────────
# TICKET HISTORY
# ─────────────────────────────────────────────

if st.session_state.history:
    st.markdown("---")
    st.markdown('<div class="section-lbl">Ticket history this session</div>', unsafe_allow_html=True)

    for item in st.session_state.history[:8]:
        r = item["result"]
        esc_icon = "🔴" if r["escalated"] else "🟢"
        st.markdown(f"""
        <div class="history-item">
            <span class="history-id">{item['ticket_id']}</span>
            <span class="history-issue">{item['issue'][:80]}</span>
            {category_badge(r['category'])}
            {priority_badge(r['priority'])}
            <span style="font-size:0.8rem">{esc_icon}</span>
        </div>
        """, unsafe_allow_html=True)


# ─────────────────────────────────────────────
# FOOTER
# ─────────────────────────────────────────────

st.markdown("---")
st.markdown("""
<div style="text-align:center; font-size:0.75rem; color:#334155; padding: 0.5rem 0 1.5rem; font-family:'JetBrains Mono',monospace;">
    LangGraph · 3 agent · Groq LLM
</div>
""", unsafe_allow_html=True)