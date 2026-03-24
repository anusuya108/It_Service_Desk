# evaluate.py — score agent accuracy against tickets.csv
import os, json
import pandas as pd
from agent import process_ticket

def run_evaluation(csv_path="data/tickets.csv"):
    if not os.path.exists(csv_path):
        print(f"ERROR: {csv_path} not found.")
        return

    df = pd.read_csv(csv_path)
    df["expected_escalated"] = df["expected_escalated"].astype(str).str.strip().str.lower() == "true"

    total = len(df)
    cat_ok = pri_ok = esc_ok = 0
    results = []

    print(f"\n{'='*60}\n  EVALUATION — {total} tickets\n{'='*60}")

    for _, row in df.iterrows():
        pred = process_ticket(row["ticket_id"], row["user_issue"])

        c_ok = pred.get("category","") == row["expected_category"]
        p_ok = pred.get("priority","")  == row["expected_priority"]
        e_ok = pred.get("escalated",False) == row["expected_escalated"]

        if c_ok: cat_ok += 1
        if p_ok: pri_ok += 1
        if e_ok: esc_ok += 1

        results.append({
            "ticket_id": row["ticket_id"],
            "issue": row["user_issue"][:60],
            "expected_category": row["expected_category"],
            "predicted_category": pred.get("category",""),
            "category_ok": c_ok,
            "expected_priority": row["expected_priority"],
            "predicted_priority": pred.get("priority",""),
            "priority_ok": p_ok,
            "expected_escalated": row["expected_escalated"],
            "predicted_escalated": pred.get("escalated",False),
            "escalation_ok": e_ok,
        })

        print(f"  {row['ticket_id']}  Cat{'✅' if c_ok else '❌'}  Pri{'✅' if p_ok else '❌'}  Esc{'✅' if e_ok else '❌'}  {row['user_issue'][:45]}")

    print(f"\n{'='*60}")
    print(f"  Category accuracy  : {cat_ok/total*100:.1f}%")
    print(f"  Priority accuracy  : {pri_ok/total*100:.1f}%")
    print(f"  Escalation accuracy: {esc_ok/total*100:.1f}%")
    print(f"  Overall accuracy   : {(cat_ok+pri_ok+esc_ok)/(total*3)*100:.1f}%")
    print(f"{'='*60}")

    os.makedirs("results", exist_ok=True)
    pd.DataFrame(results).to_csv("results/eval_results.csv", index=False)
    with open("results/eval_results.json","w") as f:
        json.dump(results, f, indent=2, default=str)
    print(f"\n  Saved → results/eval_results.csv")

if __name__ == "__main__":
    run_evaluation()