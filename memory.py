# memory.py — past ticket memory
# Stores resolved tickets and finds similar past cases.
# No vector DB needed — uses keyword overlap scoring.

import json, os
from typing import Optional

MEMORY_FILE = "data/ticket_memory.json"

SEED_MEMORY = [
    {"issue": "forgot password outlook login",         "category": "account",  "priority": "medium", "resolution": "Password reset via self-service portal. MFA re-enrolled. Resolved in 10 minutes.", "escalated": False},
    {"issue": "laptop spilled water not turning on",   "category": "hardware", "priority": "high",   "resolution": "Device powered off. Brought to IT desk. Liquid damage on motherboard. Replacement laptop issued in 4 hours.", "escalated": True},
    {"issue": "entire office internet down outage",    "category": "network",  "priority": "critical","resolution": "NOC identified faulty core switch. Replacement completed. Connectivity restored in 45 minutes.", "escalated": True},
    {"issue": "teams crashes joining meeting call",    "category": "software", "priority": "medium", "resolution": "Cleared Teams cache, updated client. Root cause: corrupted cache from failed update.", "escalated": False},
    {"issue": "vpn not connecting working from home",  "category": "network",  "priority": "medium", "resolution": "Reinstalled VPN client, updated certificate. Root cause: expired auth certificate.", "escalated": False},
    {"issue": "ransomware message screen clicked link","category": "other",    "priority": "critical","resolution": "Machine isolated immediately. SOC investigated. Contained to single device. OS reimaged in 2 hours.", "escalated": True},
    {"issue": "monitor flickering black screen",       "category": "hardware", "priority": "low",    "resolution": "Replaced DisplayPort cable. Resolved immediately. Root cause: faulty cable.", "escalated": False},
    {"issue": "excel crash freeze not responding",     "category": "software", "priority": "medium", "resolution": "Disabled conflicting add-ins, repaired Office. Root cause: third-party add-in conflict.", "escalated": False},
    {"issue": "account locked cannot login access",    "category": "account",  "priority": "medium", "resolution": "Account unlocked in AD. Root cause: 5 failed login attempts triggered lockout.", "escalated": False},
    {"issue": "printer not printing offline",          "category": "hardware", "priority": "medium", "resolution": "Cleared print queue, restarted print spooler. Root cause: stuck job blocking queue.", "escalated": False},
    {"issue": "erp system down all staff",             "category": "software", "priority": "critical","resolution": "Escalated to Tier-2. Database service restarted. Full recovery in 90 minutes.", "escalated": True},
    {"issue": "file share drive inaccessible department","category": "network","priority": "high",   "resolution": "Permissions group membership corrected by IAM. Access restored in 2 hours.", "escalated": True},
    {"issue": "ceo email not working access",          "category": "account",  "priority": "high",   "resolution": "Exchange mailbox issue resolved by Tier-2. Root cause: mailbox quota exceeded.", "escalated": True},
]


def _load():
    os.makedirs("data", exist_ok=True)
    if not os.path.exists(MEMORY_FILE):
        _save(SEED_MEMORY)
        return SEED_MEMORY
    with open(MEMORY_FILE) as f:
        return json.load(f)


def _save(mem):
    os.makedirs("data", exist_ok=True)
    with open(MEMORY_FILE, "w") as f:
        json.dump(mem, f, indent=2)


def find_similar(issue: str, category: str) -> Optional[dict]:
    mem         = _load()
    issue_words = set(issue.lower().split())
    best_score  = 0
    best_match  = None
    for past in mem:
        past_words = set(past["issue"].lower().split())
        overlap    = len(issue_words & past_words)
        cat_bonus  = 2 if past.get("category") == category else 0
        score      = overlap + cat_bonus
        if score > best_score:
            best_score = score
            best_match = past
    return best_match if best_score >= 2 else None


def save_ticket(ticket_id, issue, category, priority, resolution, escalated):
    mem = _load()
    mem.append({
        "ticket_id": ticket_id,
        "issue":     issue.lower(),
        "category":  category,
        "priority":  priority,
        "resolution":resolution,
        "escalated": escalated,
    })
    if len(mem) > 300:
        mem = mem[-300:]
    _save(mem)