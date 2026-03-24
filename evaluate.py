# evaluate.py — accuracy scoring against tickets.csv
# Run with: python evaluate.py

import os
import json
import pandas as pd
from agent import process_ticket


def run_evaluation(csv_path: str = "data/tickets.csv"):
    if not os.path.exists(csv_path):
        print(f"ERROR: {csv_path} not found.")
        return

    df = pd.read_csv(csv_path)
    df["expected_escalated"] = (
        df["expected_escalated"].astype(str).str.strip().str.lower() == "true"
    )

    total   = len(df)
    cat_ok  = 0
    pri_ok  = 0
    esc_ok  = 0
    results = []

    print(f"\n{'='*65}")
    print(f"  RUNNING EVALUATION — {total} tickets")
    print(f"{'='*65}")
    print(f"  {'ID':<10} {'Cat':>4} {'Pri':>4} {'Esc':>4}  Issue")
    print(f"  {'-'*60}")

    for _, row in df.iterrows():
        pred = process_ticket(row["ticket_id"], row["user_issue"])

        c_ok = pred.get("category","")  == row["expected_category"]
        p_ok = pred.get("priority","")  == row["expected_priority"]
        e_ok = pred.get("escalated",False) == row["expected_escalated"]

        if c_ok: cat_ok += 1
        if p_ok: pri_ok += 1
        if e_ok: esc_ok += 1

        print(
            f"  {row['ticket_id']:<10} "
            f"{'✅' if c_ok else '❌':>4} "
            f"{'✅' if p_ok else '❌':>4} "
            f"{'✅' if e_ok else '❌':>4}  "
            f"{row['user_issue'][:48]}"
        )

        results.append({
            "ticket_id":           row["ticket_id"],
            "issue":               row["user_issue"][:60],
            "expected_category":   row["expected_category"],
            "predicted_category":  pred.get("category",""),
            "category_ok":         c_ok,
            "expected_priority":   row["expected_priority"],
            "predicted_priority":  pred.get("priority",""),
            "priority_ok":         p_ok,
            "expected_escalated":  row["expected_escalated"],
            "predicted_escalated": pred.get("escalated",False),
            "escalation_ok":       e_ok,
        })

    cat_acc = cat_ok / total * 100
    pri_acc = pri_ok / total * 100
    esc_acc = esc_ok / total * 100
    overall = (cat_ok + pri_ok + esc_ok) / (total * 3) * 100

    print(f"\n{'='*65}")
    print(f"  === RESULTS ===")
    print(f"  Category Accuracy  : {cat_acc:.2f}%")
    print(f"  Priority Accuracy  : {pri_acc:.2f}%")
    print(f"  Escalation Accuracy: {esc_acc:.2f}%")
    print(f"  Overall Accuracy   : {overall:.2f}%")
    print(f"  Total Tickets Tested: {total}")
    print(f"{'='*65}")

    # Show wrong cases for debugging
    wrong = [r for r in results if not r["category_ok"] or not r["priority_ok"] or not r["escalation_ok"]]
    if wrong:
        print(f"\n  WRONG CASES ({len(wrong)}):")
        for w in wrong:
            issues = []
            if not w["category_ok"]:
                issues.append(f"Cat: expected={w['expected_category']} got={w['predicted_category']}")
            if not w["priority_ok"]:
                issues.append(f"Pri: expected={w['expected_priority']} got={w['predicted_priority']}")
            if not w["escalation_ok"]:
                issues.append(f"Esc: expected={w['expected_escalated']} got={w['predicted_escalated']}")
            print(f"  {w['ticket_id']}: {w['issue'][:50]}")
            for i in issues:
                print(f"    → {i}")

    # Save results
    os.makedirs("results", exist_ok=True)
    pd.DataFrame(results).to_csv("results/eval_results.csv", index=False)
    with open("results/eval_results.json","w") as f:
        json.dump(results, f, indent=2, default=str)
    print(f"\n  Saved → results/eval_results.csv")
    print(f"  Saved → results/eval_results.json")

    return {
        "category_accuracy":   round(cat_acc,2),
        "priority_accuracy":   round(pri_acc,2),
        "escalation_accuracy": round(esc_acc,2),
        "overall_accuracy":    round(overall,2),
        "total":               total,
    }


if __name__ == "__main__":
    run_evaluation()