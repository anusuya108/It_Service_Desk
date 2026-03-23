# app.py

import streamlit as st
from agent import process_ticket
import pandas as pd
import os

st.title("IT Service Desk (3-Agent System)")

issue = st.text_area("Describe your issue")

if st.button("Submit Ticket"):
    result = process_ticket("TKT-NEW", issue)

    st.subheader("Result")
    st.json(result)

    st.subheader("Reasoning")
    st.write(result["reason"])

    if result["escalated"]:
        st.error("Escalated to Level 2")
    else:
        st.success("Resolved at Level 1")

# Evaluation display
if os.path.exists("results/eval_results.csv"):
    df = pd.read_csv("results/eval_results.csv")

    st.subheader("Evaluation Results")
    st.dataframe(df)

    accuracy = (
        df["category_ok"].mean() +
        df["priority_ok"].mean() +
        df["escalation_ok"].mean()
    ) / 3 * 100

    st.metric("Overall Accuracy", f"{accuracy:.2f}%")