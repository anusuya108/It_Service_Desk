"""
Evaluation Module
Loads tickets from tickets.csv, runs the agent pipeline,
and scores category / priority / escalation accuracy.

Run: python evaluate.py
"""

import os
import csv
import json
from agent import process_ticket


# ─────────────────────────────────────────────────────────────
# 1. LOAD DATASET FROM CSV
#    Create tickets.csv in the same folder, or use the
#    built-in fallback dataset below.
# ─────────────────────────────────────────────────────────────

FALLBACK_TICKETS = [
    {
        "ticket_id":           "TKT-001",
        "user_issue":          "My laptop won't turn on after I spilled coffee on it.",
        "expected_category":   "hardware",
        "expected_priority":   "high",
        "expected_escalated":  True,
    },
    {
        "ticket_id":           "TKT-002",
        "user_issue":          "I forgot my password and can't log into Outlook.",
        "expected_category":   "account",
        "expected_priority":   "medium",
        "expected_escalated":  False,
    },
    {
        "ticket_id":           "TKT-003",
        "user_issue":          "The entire office internet is down. No one can work.",
        "expected_category":   "network",
        "expected_priority":   "critical",
        "expected_escalated":  True,
    },
    {
        "ticket_id":           "TKT-004",
        "user_issue":          "Microsoft Teams crashes when I try to join a meeting.",
        "expected_category":   "software",
        "expected_priority":   "high",
        "expected_escalated":  False,
    },
    {
        "ticket_id":           "TKT-005",
        "user_issue":          "How do I set an out-of-office reply in Outlook?",
        "expected_category":   "software",
        "expected_priority":   "low",
        "expected_escalated":  False,
    },
    {
        "ticket_id":           "TKT-006",
        "user_issue":          "I clicked a suspicious link and now my files look encrypted.",
        "expected_category":   "other",
        "expected_priority":   "critical",
        "expected_escalated":  True,
    },
    {
        "ticket_id":           "TKT-007",
        "user_issue":          "My Bluetooth mouse keeps disconnecting every few minutes.",
        "expected_category":   "hardware",
        "expected_priority":   "low",
        "expected_escalated":  False,
    },
    {
        "ticket_id":           "TKT-008",
        "user_issue":          "I can't connect to the VPN from home.",
        "expected_category":   "network",
        "expected_priority":   "medium",
        "expected_escalated":  False,
    },
    {
        "ticket_id":           "TKT-009",
        "user_issue":          "New employee Sarah Jones needs an account created by Monday.",
        "expected_category":   "account",
        "expected_priority":   "medium",
        "expected_escalated":  False,
        },
    {
        "ticket_id":           "TKT-010",
        "user_issue":          "Our ERP system is completely down, 200 users cannot process orders.",
        "expected_category":   "software",
        "expected_priority":   "critical",
        "expected_escalated":  True,
    },
]


def load_dataset(csv_path: str = "tickets.csv") -> list[dict]:
    """
    Load from tickets.csv if it exists, otherwise use the
    built-in fallback dataset.

    CSV format (header required):
    ticket_id,user_issue,expected_category,expected_priority,expected_escalated
    """
    if os.path.exists(csv_path):
        print(f"Loading dataset from {csv_path} ...")
        tickets = []
        with open(csv_path, newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                # Convert string "True"/"False" to bool
                row["expected_escalated"] = row["expected_escalated"].strip().lower() == "true"
                tickets.append(row)
        print(f"  Loaded {len(tickets)} tickets from CSV.")
        return tickets

    print("tickets.csv not found — using built-in fallback dataset.")
    return FALLBACK_TICKETS


# ─────────────────────────────────────────────────────────────
# 2. RUN EVALUATION
# ─────────────────────────────────────────────────────────────

def run_evaluation(sample_size: int = 5) -> dict:
    """
    Run agent pipeline on sample_size tickets and score accuracy.

    Args:
        sample_size: Number of tickets to evaluate.
                     Start small (3-5) to save API quota.
    """
    dataset = load_dataset()[:sample_size]

    results            = []
    category_correct   = 0
    priority_correct   = 0
    escalation_correct = 0

    print(f"\n{'='*60}")
    print(f"  EVALUATION STARTING  ({len(dataset)} tickets)")
    print(f"{'='*60}")

    for i, ticket in enumerate(dataset, 1):
        print(f"\n[{i}/{len(dataset)}] {ticket['ticket_id']}: {ticket['user_issue'][:55]}...")

        try:
            state = process_ticket(ticket["ticket_id"], ticket["user_issue"])
        except Exception as e:
            print(f"  ERROR: {e}")
            continue

        cat_ok  = state["category"] == ticket["expected_category"]
        pri_ok  = state["priority"]  == ticket["expected_priority"]
        esc_ok  = state["escalated"] == ticket["expected_escalated"]

        if cat_ok:  category_correct   += 1
        if pri_ok:  priority_correct    += 1
        if esc_ok:  escalation_correct  += 1

        results.append({
            "ticket_id":            ticket["ticket_id"],
            "issue_short":          ticket["user_issue"][:55],
            "expected_category":    ticket["expected_category"],
            "predicted_category":   state["category"],
            "category_ok":          cat_ok,
            "expected_priority":    ticket["expected_priority"],
            "predicted_priority":   state["priority"],
            "priority_ok":          pri_ok,
            "expected_escalated":   ticket["expected_escalated"],
            "predicted_escalated":  state["escalated"],
            "escalation_ok":        esc_ok,
        })

    total = len(results)

    metrics = {
        "total":               total,
        "category_accuracy":   round(category_correct   / total * 100, 1) if total else 0,
        "priority_accuracy":   round(priority_correct    / total * 100, 1) if total else 0,
        "escalation_accuracy": round(escalation_correct  / total * 100, 1) if total else 0,
        "overall_accuracy":    round(
            (category_correct + priority_correct + escalation_correct) / (total * 3) * 100, 1
        ) if total else 0,
        "results": results,
    }

    return metrics


# ─────────────────────────────────────────────────────────────
# 3. PRINT REPORT
# ─────────────────────────────────────────────────────────────

def print_report(metrics: dict):
    r = metrics
    print(f"\n{'='*60}")
    print(f"  EVALUATION REPORT")
    print(f"{'='*60}")
    print(f"  Tickets evaluated   : {r['total']}")
    print(f"  Category accuracy   : {r['category_accuracy']}%")
    print(f"  Priority accuracy   : {r['priority_accuracy']}%")
    print(f"  Escalation accuracy : {r['escalation_accuracy']}%")
    print(f"  Overall accuracy    : {r['overall_accuracy']}%")
    print(f"{'='*60}")

    print(f"\n  {'ID':<10} {'Cat':>3} {'Pri':>3} {'Esc':>3}  Issue")
    print(f"  {'-'*58}")
    for res in r["results"]:
        c = "Yes" if res["category_ok"]  else "No"
        p = "Yes" if res["priority_ok"]  else "No"
        e = "Yes" if res["escalation_ok"] else "No"
        print(f"  {res['ticket_id']:<10}  {c}   {p}   {e}  {res['issue_short']}")

    print(f"\n  Mismatches:")
    any_miss = False
    for res in r["results"]:
        if not res["category_ok"]:
            print(f"  ❌ {res['ticket_id']} Category: expected={res['expected_category']} got={res['predicted_category']}")
            any_miss = True
        if not res["priority_ok"]:
            print(f"  ❌ {res['ticket_id']} Priority: expected={res['expected_priority']} got={res['predicted_priority']}")
            any_miss = True
        if not res["escalation_ok"]:
            print(f"  ❌ {res['ticket_id']} Escalation: expected={res['expected_escalated']} got={res['predicted_escalated']}")
            any_miss = True
    if not any_miss:
        print("  None — perfect score!")


# ─────────────────────────────────────────────────────────────
# 4. SAVE RESULTS
# ─────────────────────────────────────────────────────────────

def save_results(metrics: dict):
    os.makedirs("results", exist_ok=True)

    # Save JSON
    with open("results/eval_results.json", "w") as f:
        json.dump(metrics, f, indent=2, default=str)

    # Save CSV
    with open("results/eval_results.csv", "w", newline="") as f:
        if metrics["results"]:
            writer = csv.DictWriter(f, fieldnames=metrics["results"][0].keys())
            writer.writeheader()
            writer.writerows(metrics["results"])

    print(f"\n  Results saved to results/eval_results.json and results/eval_results.csv")


# ─────────────────────────────────────────────────────────────
# 5. MAIN
# ─────────────────────────────────────────────────────────────

if __name__ == "__main__":
    # Change sample_size to evaluate more tickets (costs more API calls)
    metrics = run_evaluation(sample_size=5)
    print_report(metrics)
    save_results(metrics)