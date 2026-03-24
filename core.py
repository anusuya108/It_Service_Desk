# core.py

def classify_issue(issue: str):
    """
    Returns (category, priority, match_strength)
    match_strength: "strong" | "weak" | "none"  — internal only, never shown to user
    """
    t = issue.lower()

    network_kw  = ["internet","wifi","network","vpn","connection","shared drive",
                   "website","lan","sync","remote","firewall","ping","bandwidth","outage"]
    account_kw  = ["password","login","account","access","permission","admin",
                   "mfa","locked out","sign in","username","credentials","2fa","authenticate"]
    hardware_kw = ["laptop","keyboard","mouse","monitor","battery","disk","screen",
                   "fan","usb","printer","spilled","water","cable","charger","webcam",
                   "headset","docking","hardware","broken","physical","device"]
    software_kw = ["software","application","erp","teams","excel","crash","error",
                   "update","freeze","outlook","install","uninstall","app","browser",
                   "windows","office","adobe","opening","not opening","slow","bug"]

    scores = {
        "network":  sum(1 for k in network_kw  if k in t),
        "account":  sum(1 for k in account_kw  if k in t),
        "hardware": sum(1 for k in hardware_kw if k in t),
        "software": sum(1 for k in software_kw if k in t),
    }

    best_cat   = max(scores, key=scores.get)
    best_score = scores[best_cat]

    if best_score == 0:
        category      = "other"
        match_strength = "none"
    elif best_score == 1:
        category      = best_cat
        match_strength = "weak"
    else:
        category      = best_cat
        match_strength = "strong"

    priority = _get_priority(t)
    return category, priority, match_strength


def _get_priority(t: str) -> str:
    """Impact-based priority — checks scope and severity signals"""

    # ── CRITICAL: office-wide / security / data loss ──
    if any(x in t for x in ["entire office","whole office","everyone","all users",
                              "all staff","company-wide","organisation"]) and \
       any(x in t for x in ["down","offline","not working","unavailable","outage"]):
        return "critical"

    if any(x in t for x in ["ransomware","ransom","security breach","hacked",
                              "data loss","virus outbreak","malware","cyberattack"]):
        return "critical"

    if "erp" in t and any(x in t for x in ["down","offline","not working"]):
        return "critical"

    if "disk failure" in t or "complete outage" in t:
        return "critical"

    # ── HIGH: one person fully blocked ────────────────
    if any(x in t for x in ["ceo","cto","cfo","vp ","director","executive","vip"]):
        return "high"   # senior user always high minimum

    if any(x in t for x in ["won't turn on","not turning on","spilled","water damage",
                              "cracked","overheat","shuts down","cannot work",
                              "completely blocked","not starting","physical damage"]):
        return "high"

    # ── LOW: cosmetic / how-to ─────────────────────────
    if any(x in t for x in ["how to","how do i","setup","configure","slow",
                              "slightly","minor","feature request","cosmetic","tip"]):
        return "low"

    # ── MEDIUM: everything else ────────────────────────
    return "medium"


def get_team(category: str, issue: str) -> str:
    t = issue.lower()
    if any(x in t for x in ["ransom","breach","hacked","virus","malware","cyberattack"]):
        return "SOC — Security Operations Centre"
    return {
        "network":  "NOC — Network Operations Centre",
        "account":  "IAM — Identity & Access Management",
        "hardware": "Infrastructure Team",
        "software": "Tier-2 Software Support",
    }.get(category, "Tier-2 Support")


def get_sla(priority: str) -> str:
    return {
        "critical": "1 hour",
        "high":     "4 hours",
        "medium":   "1 business day",
        "low":      "3 business days",
    }.get(priority, "1 business day")