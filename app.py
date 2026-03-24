# app.py — Streamlit web UI
# Run with: streamlit run app.py

import streamlit as st
import os
from agent import process_ticket

st.set_page_config(page_title="IT Service Desk", page_icon="🖥️", layout="centered")

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;500&family=DM+Sans:wght@300;400;500&display=swap');
html, body, [class*="css"] { font-family: 'DM Sans', sans-serif; }
.stApp { background-color: #0f1117; color: #e2e8f0; }
#MainMenu, footer, header { visibility: hidden; }
.desk-header { text-align:center; padding:2rem 0 1.5rem; border-bottom:1px solid #1e2533; margin-bottom:2rem; }
.desk-header h1 { font-family:'JetBrains Mono',monospace; font-size:1.5rem; font-weight:500; color:#f1f5f9; margin:0; }
.desk-header p  { font-size:0.85rem; color:#64748b; margin:6px 0 0; }
.stTextArea textarea { background-color:#161b27 !important; border:1px solid #1e2d40 !important; border-radius:10px !important; color:#e2e8f0 !important; font-size:0.95rem !important; }
.stTextArea textarea:focus { border-color:#3b82f6 !important; }
.stButton > button { background:#3b82f6 !important; color:white !important; border:none !important; border-radius:8px !important; width:100% !important; font-weight:500 !important; font-size:0.9rem !important; padding:0.6rem 2rem !important; }
.stButton > button:hover { background:#2563eb !important; }
.agent-card { background:#161b27; border:1px solid #1e2d40; border-radius:12px; padding:1.2rem 1.4rem; margin:0.6rem 0; position:relative; overflow:hidden; }
.agent-card::before { content:''; position:absolute; left:0; top:0; bottom:0; width:3px; border-radius:3px 0 0 3px; }
.agent-card.triage::before     { background:#f59e0b; }
.agent-card.resolution::before { background:#10b981; }
.agent-card.escalation::before { background:#ef4444; }
.agent-label { font-family:'JetBrains Mono',monospace; font-size:0.7rem; font-weight:500; letter-spacing:0.08em; text-transform:uppercase; margin-bottom:8px; }
.agent-card.triage .agent-label     { color:#f59e0b; }
.agent-card.resolution .agent-label { color:#10b981; }
.agent-card.escalation .agent-label { color:#ef4444; }
.agent-content { color:#cbd5e1; font-size:0.9rem; line-height:1.6; }
.badge { display:inline-block; padding:2px 10px; border-radius:20px; font-size:0.75rem; font-weight:500; font-family:'JetBrains Mono',monospace; margin:2px 3px; }
.badge-critical{ background:#450a0a; color:#fca5a5; border:1px solid #7f1d1d; }
.badge-high    { background:#431407; color:#fdba74; border:1px solid #7c2d12; }
.badge-medium  { background:#1e3a5f; color:#93c5fd; border:1px solid #1e40af; }
.badge-low     { background:#14532d; color:#86efac; border:1px solid #166534; }
.badge-cat     { background:#1e1b4b; color:#a5b4fc; border:1px solid #3730a3; }
.metrics-row { display:flex; gap:12px; margin:1.2rem 0; }
.metric-box  { flex:1; background:#161b27; border:1px solid #1e2d40; border-radius:10px; padding:1rem; text-align:center; }
.metric-val  { font-family:'JetBrains Mono',monospace; font-size:1.3rem; font-weight:500; color:#f1f5f9; }
.metric-lbl  { font-size:0.75rem; color:#475569; margin-top:3px; }
.section-lbl { font-family:'JetBrains Mono',monospace; font-size:0.68rem; font-weight:500; letter-spacing:0.1em; text-transform:uppercase; color:#475569; margin:1.5rem 0 0.8rem; }
hr { border-color:#1e2533 !important; }
</style>
""", unsafe_allow_html=True)

st.markdown("""
<div class="desk-header">
    <h1>// IT Service Desk</h1>
    <p>3-agent AI pipeline &nbsp;·&nbsp; Triage → Resolution → Escalation</p>
</div>
""", unsafe_allow_html=True)

if "history" not in st.session_state:
    st.session_state.history = []
if "counter" not in st.session_state:
    st.session_state.counter = 1

st.markdown('<div class="section-lbl">Quick samples</div>', unsafe_allow_html=True)

samples = {
    "Select a sample...": "",
    "Spilled water on laptop":     "My laptop won't turn on after I spilled water on it.",
    "Forgot Outlook password":     "I forgot my password and can't log into Outlook.",
    "Entire office internet down": "The entire office internet is down. No one can work.",
    "Ransomware on screen":        "I clicked a suspicious link and now I see a ransom message.",
    "Monitor flickering":          "My monitor keeps flickering and sometimes goes completely black.",
    "Strange login on my account": "Someone is logged in as me on a machine I don't recognise.",
    "Teams crashes on every call": "Microsoft Teams crashes every time I try to join a meeting.",
}

selected  = st.selectbox("", list(samples.keys()), label_visibility="collapsed")
prefill   = samples[selected] if selected != "Select a sample..." else ""

st.markdown('<div class="section-lbl">Describe your issue</div>', unsafe_allow_html=True)
user_issue = st.text_area("", value=prefill, height=110,
                           placeholder="e.g. My laptop won't start after the Windows update...",
                           label_visibility="collapsed")
submit = st.button("Submit Ticket →")

if submit:
    if not user_issue.strip():
        st.warning("Please describe your issue first.")
    else:
        ticket_id = f"TKT-{st.session_state.counter:03d}"
        st.session_state.counter += 1

        with st.spinner("Running 3 agents..."):
            result = process_ticket(ticket_id, user_issue)

        result.setdefault("category",          "other")
        result.setdefault("priority",          "medium")
        result.setdefault("confidence",        0.0)
        result.setdefault("reason",            "")
        result.setdefault("resolution",        "")
        result.setdefault("escalated",         False)
        result.setdefault("escalation_reason", "")
        result.setdefault("escalation_report", "")

        st.session_state.history.insert(0, {"ticket_id": ticket_id, "issue": user_issue, "result": result})

        conf_pct  = f"{result['confidence']*100:.0f}%"
        esc_label = "YES" if result["escalated"] else "NO"

        st.markdown(f"""
        <div class="metrics-row">
            <div class="metric-box"><div class="metric-val">{ticket_id}</div><div class="metric-lbl">Ticket ID</div></div>
            <div class="metric-box"><div class="metric-val">{result['category'].upper()}</div><div class="metric-lbl">Category</div></div>
            <div class="metric-box"><div class="metric-val">{result['priority'].upper()}</div><div class="metric-lbl">Priority</div></div>
            <div class="metric-box"><div class="metric-val">{conf_pct}</div><div class="metric-lbl">Confidence</div></div>
            <div class="metric-box"><div class="metric-val">{esc_label}</div><div class="metric-lbl">Escalated</div></div>
        </div>
        """, unsafe_allow_html=True)

        st.markdown('<div class="section-lbl">Agent outputs</div>', unsafe_allow_html=True)

        st.markdown(f"""
        <div class="agent-card triage">
            <div class="agent-label">Agent 1 — Triage</div>
            <div class="agent-content">
                Category: <span class="badge badge-cat">{result['category']}</span>
                &nbsp; Priority: <span class="badge badge-{result['priority']}">{result['priority'].upper()}</span>
                <br><small style="color:#475569;margin-top:6px;display:block">{result['reason']}</small>
            </div>
        </div>
        """, unsafe_allow_html=True)

        res_class = "escalation" if result["escalated"] else "resolution"
        res_label = "Agent 2 — Resolution (could not resolve)" if result["escalated"] else "Agent 2 — Resolution (resolved)"
        st.markdown(f"""
        <div class="agent-card {res_class}">
            <div class="agent-label">{res_label}</div>
            <div class="agent-content">{result['resolution']}</div>
        </div>
        """, unsafe_allow_html=True)

        if result["escalated"]:
            report_html = result["escalation_report"].replace("\n", "<br>")
            st.markdown(f"""
            <div class="agent-card escalation">
                <div class="agent-label">Agent 3 — Escalation Report</div>
                <div class="agent-content" style="font-family:'JetBrains Mono',monospace;font-size:0.8rem;">{report_html}</div>
            </div>
            """, unsafe_allow_html=True)
        else:
            st.markdown("""
            <div class="agent-card resolution">
                <div class="agent-label">Agent 3 — Escalation</div>
                <div class="agent-content">Not required — issue resolved at Level 1.</div>
            </div>
            """, unsafe_allow_html=True)

if st.session_state.history:
    st.markdown("---")
    st.markdown('<div class="section-lbl">Session history</div>', unsafe_allow_html=True)
    for item in st.session_state.history[:8]:
        r = item["result"]
        icon = "🔴" if r.get("escalated") else "🟢"
        st.markdown(f"""
        <div style="background:#161b27;border:1px solid #1e2d40;border-radius:8px;padding:0.8rem 1rem;margin:0.4rem 0;display:flex;align-items:center;gap:12px;">
            <span style="font-family:'JetBrains Mono',monospace;font-size:0.75rem;color:#475569;min-width:65px">{item['ticket_id']}</span>
            <span style="flex:1;font-size:0.85rem;color:#94a3b8;overflow:hidden;text-overflow:ellipsis;white-space:nowrap">{item['issue'][:70]}</span>
            <span class="badge badge-cat">{r.get('category','?')}</span>
            <span class="badge badge-{r.get('priority','medium')}">{r.get('priority','?').upper()}</span>
            <span>{icon}</span>
        </div>
        """, unsafe_allow_html=True)

st.markdown("---")
st.markdown("""
<div style="text-align:center;font-size:0.75rem;color:#334155;padding:0.5rem 0 1.5rem;font-family:'JetBrains Mono',monospace;">
    LangGraph · 3 agents · Groq LLM · llama-3.3-70b-versatile
</div>
""", unsafe_allow_html=True)