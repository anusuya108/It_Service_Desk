# core.py — rule-based triage logic
# No fake confidence scores. Returns only what rules can honestly determine.

def classify_issue(issue: str):
    """
    Returns (category, priority, reason, match_strength)
    match_strength: "strong" | "weak" | "none"
    Used by agent.py to decide whether to trust rules or call LLM
    """
    issue_lower = issue.lower()

    # ── KEYWORD BANKS ─────────────────────────────────
    network_kw  = ["internet","wifi","network","vpn","connection","shared drive",
                   "website","lan","sync","remote","firewall","ping","bandwidth"]
    account_kw  = ["password","login","account","access","permission","admin",
                   "mfa","locked out","sign in","username","credentials","2fa","authenticate"]
    hardware_kw = ["laptop","keyboard","mouse","monitor","battery","disk","screen",
                   "fan","usb","printer","spilled","water","cable","charger","webcam",
                   "headset","docking","hardware","broken","physical"]
    software_kw = ["software","application","erp","teams","excel","crash","error",
                   "update","freeze","outlook","install","uninstall","app","browser",
                   "windows","office","adobe","opening","not opening","slow"]

    scores = {
        "network":  sum(1 for k in network_kw  if k in issue_lower),
        "account":  sum(1 for k in account_kw  if k in issue_lower),
        "hardware": sum(1 for k in hardware_kw if k in issue_lower),
        "software": sum(1 for k in software_kw if k in issue_lower),
    }

    best_cat   = max(scores, key=scores.get)
    best_score = scores[best_cat]

    if best_score == 0:
        category      = "other"
        match_strength = "none"
        reason        = "no keyword match"
    elif best_score == 1:
        category      = best_cat
        match_strength = "weak"
        reason        = f"weak match ({best_cat})"
    else:
        category      = best_cat
        match_strength = "strong"
        reason        = f"rule match ({best_cat}, {best_score} keywords)"

    # ── PRIORITY (rule-based only for clear-cut cases) ─
    priority = _get_priority(issue_lower)

    return category, priority, reason, match_strength


def _get_priority(issue_lower: str) -> str:
    """Determine priority from clear signals only"""

    critical_signals = [
        "disk failure", "data loss", "ransomware", "entire office",
        "all users", "everyone", "complete outage", "hacked",
        "security breach", "virus", "malware", "ransom"
    ]
    if any(x in issue_lower for x in critical_signals):
        return "critical"

    if "erp" in issue_lower and "down" in issue_lower:
        return "critical"

    if any(x in issue_lower for x in ["all users","everyone","entire"]) \
       and "down" in issue_lower:
        return "critical"

    high_signals = [
        "won't turn on", "not turning on", "spilled", "water damage",
        "cracked screen", "overheat", "shuts down", "not starting",
        "completely down", "cannot work", "can't work"
    ]
    if any(x in issue_lower for x in high_signals):
        return "high"

    low_signals = [
        "how to", "setup", "configure", "slow", "flickering slightly",
        "feature request", "cosmetic"
    ]
    if any(x in issue_lower for x in low_signals):
        return "low"

    return "medium"


def get_team(category: str, issue: str) -> str:
    issue_lower = issue.lower()
    if any(x in issue_lower for x in ["ransom","breach","hacked","virus","malware"]):
        return "SOC — Security Operations Centre"
    teams = {
        "network":  "NOC — Network Operations Centre",
        "account":  "IAM — Identity & Access Management",
        "hardware": "Infrastructure Team",
        "software": "Tier-2 Software Support",
    }
    return teams.get(category, "Tier-2 Support")


def get_sla(priority: str) -> str:
    return {
        "critical": "1 hour",
        "high":     "4 hours",
        "medium":   "1 business day",
        "low":      "3 business days",
    }.get(priority, "1 business day")