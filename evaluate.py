# evaluate.py

import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score

from graph import build_graph
from model import priority_model

df = pd.read_csv("data/data.csv")

train_df, test_df = train_test_split(
    df, test_size=0.2, stratify=df["priority"], random_state=42
)

priority_model.train(train_df["text"], train_df["priority"])

graph = build_graph()

cat_true, cat_pred = [], []
pri_true, pri_pred = [], []
esc_true, esc_pred = [], []

for _, row in test_df.iterrows():
    result = graph.invoke({"text": row["text"]})

    cat_true.append(row["category"])
    cat_pred.append(result["category"])

    pri_true.append(row["priority"])
    pri_pred.append(result["priority"])

    esc_true.append(row["escalation"])
    esc_pred.append("yes" if result["status"]=="escalated" else "no")

cat_acc = accuracy_score(cat_true, cat_pred)
pri_acc = accuracy_score(pri_true, pri_pred)
esc_acc = accuracy_score(esc_true, esc_pred)

overall = (cat_acc + pri_acc + esc_acc) / 3

print("\n=== RESULTS ===")
print(f"Category Accuracy: {cat_acc*100:.2f}%")
print(f"Priority Accuracy: {pri_acc*100:.2f}%")
print(f"Escalation Accuracy: {esc_acc*100:.2f}%")
print(f"Overall Accuracy: {overall*100:.2f}%")
print(f"Total Tickets Tested: {len(test_df)}")