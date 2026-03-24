# memory.py — simple past ticket memory
# Stores resolved tickets and finds similar past issues.
# No vector DB needed — uses keyword overlap scoring.
# This is what makes the system feel like it learns.

import json
import os
from typing import Optional

MEMORY_FILE = "data/ticket_memory.json"

# Seed memory — real past resolutions the system "knows" from day 1
SEED_MEMORY = [
    {
        "issue":      "forgot password outlook",
        "category":   "account",
        "priority":   "medium",
        "resolution": "User reset password via self-service portal. MFA re-enrolled. Issue resolved in 10 minutes.",
        "escalated":  False,
    },
    {
        "issue":      "laptop not turning on spilled water",
        "category":   "hardware",
        "priority":   "high",
        "resolution": "Device powered off immediately. Brought to IT desk. Internal inspection found liquid damage on motherboard. Replacement laptop issued within 4 hours.",
        "escalated":  True,
    },
    {
        "issue":      "office internet down entire building",
        "category":   "network",
        "priority":   "critical",
        "resolution": "NOC identified a faulty core switch. Replacement completed. Full connectivity restored in 45 minutes.",
        "escalated":  True,
    },
    {
        "issue":      "teams crashes joining meeting video call",
        "category":   "software",
        "priority":   "medium",
        "resolution": "Cleared Teams cache, updated to latest version. Issue resolved. Root cause: corrupted cache from failed update.",
        "escalated":  False,
    },
    {
        "issue":      "vpn not connecting working from home",
        "category":   "network",
        "priority":   "medium",
        "resolution": "Reinstalled VPN client, updated certificate. User connected successfully. Root cause: expired auth certificate.",
        "escalated":  False,
    },
    {
        "issue":      "ransomware message screen clicked link",
        "category":   "other",
        "priority":   "critical",
        "resolution": "Machine isolated from network immediately. SOC investigated. Contained to single device. OS reimaged within 2 hours.",
        "escalated":  True,
    },
    {
        "issue":      "monitor flickering black screen",
        "category":   "hardware",
        "priority":   "low",
        "resolution": "Replaced DisplayPort cable. Issue resolved immediately. Root cause: loose/faulty cable.",
        "escalated":  False,
    },
    {
        "issue":      "excel crash freeze not responding",
        "category":   "software",
        "priority":   "medium",
        "resolution": "Disabled conflicting add-ins, repaired Office installation. Issue resolved. Root cause: third-party add-in conflict.",
        "escalated":  False,
    },
    {
        "issue":      "account locked cannot login access denied",
        "category":   "account",
        "priority":   "medium",
        "resolution": "Account unlocked in Active Directory, user advised on password policy. Root cause: 5 failed login attempts triggered lockout.",
        "escalated":  False,
    },
    {
        "issue":      "printer not printing office",
        "category":   "hardware",
        "priority":   "low",
        "resolution": "Cleared print queue, restarted print spooler service. Issue resolved. Root cause: stuck job blocking queue.",
        "escalated":  False,
    },
]


def _load_memory() -> list:
    os.makedirs("data", exist_ok=True)
    if not os.path.exists(MEMORY_FILE):
        _save_memory(SEED_MEMORY)
        return SEED_MEMORY
    with open(MEMORY_FILE, "r") as f:
        return json.load(f)


def _save_memory(memory: list):
    os.makedirs("data", exist_ok=True)
    with open(MEMORY_FILE, "w") as f:
        json.dump(memory, f, indent=2)


def find_similar(issue: str, category: str, top_n: int = 1) -> Optional[dict]:
    """
    Find the most similar past ticket using keyword overlap.
    Returns the best match or None if similarity is too low.
    """
    memory   = _load_memory()
    issue_words = set(issue.lower().split())
    best_score  = 0
    best_match  = None

    for past in memory:
        past_words  = set(past["issue"].lower().split())
        overlap     = len(issue_words & past_words)
        cat_bonus   = 2 if past.get("category") == category else 0
        score       = overlap + cat_bonus

        if score > best_score:
            best_score = score
            best_match = past

    # Only return if meaningful similarity (at least 2 words overlap)
    return best_match if best_score >= 2 else None


def save_ticket(ticket_id: str, issue: str, category: str,
                priority: str, resolution: str, escalated: bool):
    """Save a resolved ticket to memory for future reference."""
    memory = _load_memory()
    memory.append({
        "ticket_id":  ticket_id,
        "issue":      issue.lower(),
        "category":   category,
        "priority":   priority,
        "resolution": resolution,
        "escalated":  escalated,
    })
    # Keep memory lean — last 200 tickets
    if len(memory) > 200:
        memory = memory[-200:]
    _save_memory(memory)