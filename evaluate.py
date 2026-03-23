# evaluate.py

import pandas as pd
from agent import process_ticket

df = pd.read_csv("data/tickets.csv")

results = []

for _, row in df.iterrows():
    pred = process_ticket(row["ticket_id"], row["user_issue"])

    results.append({
        "ticket_id": row["ticket_id"],
        "category_ok": pred["category"] == row["expected_category"],
        "priority_ok": pred["priority"] == row["expected_priority"],
        "escalation_ok": pred["escalated"] == row["expected_escalated"]
    })

res_df = pd.DataFrame(results)

accuracy = (
    res_df["category_ok"].mean() +
    res_df["priority_ok"].mean() +
    res_df["escalation_ok"].mean()
) / 3 * 100

print(f"\nOverall Accuracy: {accuracy:.2f}%")

res_df.to_csv("results/eval_results.csv", index=False)