import streamlit as st
from graph import build_graph

graph = build_graph()

st.title("AI IT Service Desk")

text = st.text_area("Describe your issue")

if st.button("Submit"):
    result = graph.invoke({"text": text})

    st.write("Category:", result["category"])
    st.write("Priority:", result["priority"])
    st.write("Status:", result["status"])
    st.write("Response:", result["response"])