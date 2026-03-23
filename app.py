import streamlit as st
from agent import process_ticket
import pandas as pd
import os

st.set_page_config(page_title="IT Service Desk AI", layout="centered")

st.title("🖥️ IT Service Desk (AI Multi-Agent System)")

issue = st.text_area("Describe your issue")

if st.button("Submit Ticket"):
    result = process_ticket("TKT-NEW", issue)

    st.subheader("📊 Ticket Analysis")

    col1, col2, col3 = st.columns(3)
    col1.metric("Category", result["category"].upper())
    col2.metric("Priority", result["priority"].upper())
    col3.metric("Confidence", f"{result['confidence']*100:.0f}%")

    st.subheader("🧠 Reasoning")
    st.info(result["reason"])

    st.subheader("🛠️ Resolution")
    st.success(result["resolution"])

    if result["escalated"]:
        st.error("🚨 Escalated to Level 2")
        st.write(result["escalation_reason"])
    else:
        st.success("✅ Resolved at Level 1")

# Evaluation
if os.path.exists("results/eval_results.csv"):
    df = pd.read_csv("results/eval_results.csv")

    st.subheader("📈 Evaluation Dashboard")
    st.dataframe(df)

    accuracy = (
        df["category_ok"].mean() +
        df["priority_ok"].mean() +
        df["escalation_ok"].mean()
    ) / 3 * 100

    st.metric("Overall Accuracy", f"{accuracy:.2f}%")