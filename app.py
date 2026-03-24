# app.py — IT Service Desk Streamlit UI
# Run: streamlit run app.py

import streamlit as st
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
.desk-header p { font-size:0.85rem; color:#64748b; margin:6px 0 0; }

.stTextArea textarea { background-color:#161b27 !important; border:1px solid #1e2d40 !important;
    border-radius:10px !important; color:#e2e8f0 !important; font-size:0.95rem !important; }
.stTextArea textarea:focus { border-color:#3b82f6 !important; }
.stButton > button { background:#3b82f6 !important; color:white !important; border:none !important;
    border-radius:8px !important; width:100% !important; font-weight:500 !important; padding:0.6rem 2rem !important; }
.stButton > button:hover { background:#2563eb !important; }

.acard { background:#161b27; border:1px solid #1e2d40; border-radius:12px;
         padding:1.25rem 1.4rem; margin:0.6rem 0; position:relative; overflow:hidden; }
.acard::before { content:''; position:absolute; left:0; top:0; bottom:0; width:3px; border-radius:3px 0 0 3px; }
.acard.triage::before     { background:#f59e0b; }
.acard.ok::before         { background:#10b981; }
.acard.esc::before        { background:#ef4444; }
.acard.mem::before        { background:#8b5cf6; }

.alabel { font-family:'JetBrains Mono',monospace; font-size:0.67rem; font-weight:500;
          letter-spacing:0.09em; text-transform:uppercase; margin-bottom:10px; }
.acard.triage .alabel { color:#f59e0b; }
.acard.ok .alabel     { color:#10b981; }
.acard.esc .alabel    { color:#ef4444; }
.acard.mem .alabel    { color:#8b5cf6; }
.acontent { color:#cbd5e1; font-size:0.9rem; line-height:1.75; }

.rbox  { background:#0d1520; border-radius:8px; padding:10px 14px; margin-top:12px;
         font-size:0.84rem; color:#64748b; line-height:1.6; }
.rpill { display:inline-block; background:#0d1520; border:1px solid #1e3a5f; border-radius:6px;
         padding:4px 10px; font-size:0.78rem; color:#64748b; margin-top:8px; font-style:italic; }
.mbox  { background:#130d2a; border:1px solid #2d1f5e; border-radius:8px; padding:10px 14px;
         margin-top:10px; font-size:0.83rem; color:#a78bfa; line-height:1.6; }

.badge { display:inline-block; padding:2px 10px; border-radius:20px; font-size:0.73rem;
         font-weight:500; font-family:'JetBrains Mono',monospace; margin:2px 3px; }
.badge-critical { background:#450a0a; color:#fca5a5; border:1px solid #7f1d1d; }
.badge-high     { background:#431407; color:#fdba74; border:1px solid #7c2d12; }
.badge-medium   { background:#1e3a5f; color:#93c5fd; border:1px solid #1e40af; }
.badge-low      { background:#14532d; color:#86efac; border:1px solid #166534; }
.badge-cat      { background:#1e1b4b; color:#a5b4fc; border:1px solid #3730a3; }

.mrow { display:flex; gap:10px; margin:1.2rem 0; flex-wrap:wrap; }
.mbox2 { flex:1; min-width:80px; background:#161b27; border:1px solid #1e2d40;
         border-radius:10px; padding:0.9rem; text-align:center; }
.mval { font-family:'JetBrains Mono',monospace; font-size:1.2rem; font-weight:500; color:#f1f5f9; }
.mlbl { font-size:0.7rem; color:#475569; margin-top:3px; }

.slbl { font-family:'JetBrains Mono',monospace; font-size:0.67rem; font-weight:500;
        letter-spacing:0.1em; text-transform:uppercase; color:#475569; margin:1.5rem 0 0.75rem; }
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

st.markdown('<div class="slbl">Quick samples</div>', unsafe_allow_html=True)
samples = {
    "Select a sample...":                    "",
    "Spilled water on laptop":               "My laptop won't turn on after I spilled water on it.",
    "Forgot password (Outlook)":             "I forgot my password and can't log into Outlook.",
    "Entire office internet down":           "The entire office internet is down. No one can work.",
    "ERP system down — all staff affected":  "Our ERP system is completely down. All staff are affected.",
    "CEO cannot access email":               "The CEO cannot access his email since this morning.",
    "Ransomware message on screen":          "I clicked a suspicious link and now see a ransom message.",
    "Teams crashes every meeting":           "Microsoft Teams crashes every time I try to join a meeting.",
    "Unknown login on my account":           "Someone is logged into my account on a machine I don't recognise.",
    "Finance drive inaccessible":            "The file share drive is inaccessible for the entire finance department.",
    "VPN not connecting from home":          "I can't connect to the company VPN from home.",
}
selected  = st.selectbox("", list(samples.keys()), label_visibility="collapsed")
prefill   = samples[selected] if selected != "Select a sample..." else ""

st.markdown('<div class="slbl">Describe your issue</div>', unsafe_allow_html=True)
user_issue = st.text_area("", value=prefill, height=110,
    placeholder="e.g. I forgot my password and I am the admin of the production system...",
    label_visibility="collapsed")
submit = st.button("Submit Ticket →")

if submit:
    if not user_issue.strip():
        st.warning("Please describe your issue before submitting.")
    else:
        ticket_id = f"TKT-{st.session_state.counter:03d}"
        st.session_state.counter += 1

        with st.spinner("Analysing your ticket..."):
            try:
                r = process_ticket(ticket_id, user_issue)
            except Exception:
                st.error("Unable to process your ticket right now. Please try again.")
                st.stop()

        r.setdefault("category","other")
        r.setdefault("priority","medium")
        r.setdefault("priority_reason","")
        r.setdefault("triage_reasoning","")
        r.setdefault("similar_past","")
        r.setdefault("resolution","Please contact the IT helpdesk directly.")
        r.setdefault("escalated",False)
        r.setdefault("escalation_reason","")
        r.setdefault("escalation_report","")

        st.session_state.history.insert(0,{"ticket_id":ticket_id,"issue":user_issue,"result":r})

        esc_label = "YES" if r["escalated"] else "NO"
        st.markdown(f"""
        <div class="mrow">
            <div class="mbox2"><div class="mval">{ticket_id}</div><div class="mlbl">Ticket ID</div></div>
            <div class="mbox2"><div class="mval">{r['category'].upper()}</div><div class="mlbl">Category</div></div>
            <div class="mbox2"><div class="mval">{r['priority'].upper()}</div><div class="mlbl">Priority</div></div>
            <div class="mbox2"><div class="mval">{esc_label}</div><div class="mlbl">Escalated</div></div>
        </div>
        """, unsafe_allow_html=True)

        st.markdown('<div class="slbl">Agent outputs</div>', unsafe_allow_html=True)

        reasoning = r["triage_reasoning"] or f"Classified as {r['category']} with {r['priority']} priority."
        pri_why   = r["priority_reason"]
        mem_block = f'<div class="mbox">&#128196; {r["similar_past"]}</div>' if r["similar_past"] else ""

        st.markdown(f"""
        <div class="acard triage">
            <div class="alabel">Agent 1 — Triage</div>
            <div class="acontent">
                Category: <span class="badge badge-cat">{r['category']}</span>
                &nbsp; Priority: <span class="badge badge-{r['priority']}">{r['priority'].upper()}</span>
            </div>
            <div class="rbox">{reasoning}</div>
            {f'<div class="rpill">{pri_why}</div>' if pri_why else ""}
            {mem_block}
        </div>
        """, unsafe_allow_html=True)

        if r["escalated"]:
            res_html = r["resolution"].replace("\n","<br>")
            st.markdown(f"""
            <div class="acard esc">
                <div class="alabel">Agent 2 — Resolution (escalating to L2)</div>
                <div class="acontent">{res_html}</div>
            </div>
            """, unsafe_allow_html=True)
            report_html = r["escalation_report"].replace("\n","<br>")
            st.markdown(f"""
            <div class="acard esc">
                <div class="alabel">Agent 3 — Escalation Report</div>
                <div class="acontent" style="font-family:'JetBrains Mono',monospace;font-size:0.8rem;line-height:1.85;">
                    {report_html}
                </div>
            </div>
            """, unsafe_allow_html=True)
        else:
            res_html = r["resolution"].replace("\n","<br>")
            st.markdown(f"""
            <div class="acard ok">
                <div class="alabel">Agent 2 — Resolution (resolved at L1)</div>
                <div class="acontent">{res_html}</div>
            </div>
            <div class="acard ok">
                <div class="alabel">Agent 3 — Escalation</div>
                <div class="acontent">Not required — ticket resolved at Level 1.</div>
            </div>
            """, unsafe_allow_html=True)

if st.session_state.history:
    st.markdown("---")
    st.markdown('<div class="slbl">Session history</div>', unsafe_allow_html=True)
    for item in st.session_state.history[:10]:
        r   = item["result"]
        icon= "🔴" if r.get("escalated") else "🟢"
        pri = r.get("priority","medium")
        cat = r.get("category","other")
        st.markdown(f"""
        <div style="background:#161b27;border:1px solid #1e2d40;border-radius:8px;
                    padding:0.75rem 1rem;margin:0.35rem 0;display:flex;align-items:center;gap:10px;">
            <span style="font-family:'JetBrains Mono',monospace;font-size:0.72rem;color:#475569;min-width:65px;">{item['ticket_id']}</span>
            <span style="flex:1;font-size:0.84rem;color:#94a3b8;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;">{item['issue'][:72]}</span>
            <span class="badge badge-cat">{cat}</span>
            <span class="badge badge-{pri}">{pri.upper()}</span>
            <span>{icon}</span>
        </div>
        """, unsafe_allow_html=True)

st.markdown("---")
st.markdown("""
<div style="text-align:center;font-size:0.72rem;color:#334155;padding:0.5rem 0 1.5rem;font-family:'JetBrains Mono',monospace;">
    LangGraph &nbsp;·&nbsp; 3 agents &nbsp;·&nbsp; memory &nbsp;·&nbsp; Groq &nbsp;·&nbsp; llama-3.3-70b-versatile
</div>
""", unsafe_allow_html=True)