# app.py

import streamlit as st
from graph import build_graph

# Build graph
graph = build_graph()

st.set_page_config(page_title="AI IT Service Desk", layout="centered")

st.title("🧠 AI IT Service Desk")
st.markdown("### 3-Agent System (Triage → Resolution → Escalation)")

user_input = st.text_area("Describe your issue")

if st.button("Submit"):
    if user_input.strip() == "":
        st.warning("Please enter an issue.")
    else:
        result = graph.invoke({"text": user_input})

        st.subheader("📊 Result")

        st.write(f"**Category:** {result['category']}")
        st.write(f"**Priority:** {result['priority']}")
        st.write(f"**Status:** {result['status']}")

        st.markdown("### 🔧 Response")
        st.write(result["response"])
