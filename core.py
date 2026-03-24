# core.py — context-aware classification with visible reasoning

def classify_issue(issue: str):
    """
    Returns (category, priority, reasoning, match_strength)
    reasoning: human-readable explanation of the priority decision
    match_strength: internal only — "strong" | "weak" | "none"
    """
    t = issue.lower()

    # ── CATEGORY SCORING ──────────────────────────────
    network_kw  = ["internet","wifi","network","vpn","connection","shared drive",
                   "website","lan","remote","firewall","ping","bandwidth","outage","offline"]
    account_kw  = ["password","login","account","access","permission","admin",
                   "mfa","locked out","sign in","username","credentials","2fa","authenticate"]
    hardware_kw = ["laptop","keyboard","mouse","monitor","battery","disk","screen",
                   "fan","usb","printer","spilled","water","cable","charger","webcam",
                   "headset","docking","broken","physical","device","hardware"]
    software_kw = ["software","application","erp","teams","excel","crash","error",
                   "update","freeze","outlook","install","app","browser","windows",
                   "office","adobe","not opening","slow","bug","not responding"]

    scores = {
        "network":  sum(1 for k in network_kw  if k in t),
        "account":  sum(1 for k in account_kw  if k in t),
        "hardware": sum(1 for k in hardware_kw if k in t),
        "software": sum(1 for k in software_kw if k in t),
    }
    best_cat   = max(scores, key=scores.get)
    best_score = scores[best_cat]

    if best_score == 0:
        category       = "other"
        match_strength = "none"
    elif best_score == 1:
        category       = best_cat
        match_strength = "weak"
    else:
        category       = best_cat
        match_strength = "strong"

    # ── CONTEXT-AWARE PRIORITY + REASONING ────────────
    priority, reasoning = _get_priority_with_reason(t)

    return category, priority, reasoning, match_strength


def _get_priority_with_reason(t: str):
    """
    Returns (priority, reasoning) — reasoning shown to user.
    Checks CONTEXT signals, not just keywords.
    """

    # ── CRITICAL ──────────────────────────────────────
    if any(x in t for x in ["ransomware","ransom","security breach",
                              "hacked","cyberattack","virus outbreak","malware spreading"]):
        return "critical", "Active security incident detected — immediate escalation required with no delay."

    if any(x in t for x in ["entire office","whole office","everyone","all users",
                              "all staff","company-wide","entire building","whole company"]) \
       and any(x in t for x in ["down","offline","not working","unavailable","outage","cannot access"]):
        return "critical", "Office-wide outage affecting all users — business operations are halted."

    if "erp" in t and any(x in t for x in ["down","offline","not working","unavailable"]):
        return "critical", "Core business system (ERP) is down — critical business impact."

    if any(x in t for x in ["data loss","disk failure","complete outage","production down"]):
        return "critical", "Critical data or system failure — immediate senior intervention required."

    # ── HIGH ──────────────────────────────────────────
    if any(x in t for x in ["ceo","cto","cfo","coo","vp ","vice president",
                              "director","executive","vip","c-suite","board"]):
        return "high", "Senior executive affected — elevated priority per escalation policy."

    if any(x in t for x in ["admin of production","production system","live system",
                              "customer-facing","client demo","before the meeting","urgent deadline"]):
        return "high", "Issue impacts a production or time-sensitive system — elevated priority."

    if any(x in t for x in ["won't turn on","not turning on","spilled","water damage",
                              "cracked","overheat","shuts down","cannot work","completely blocked",
                              "physical damage","not starting"]):
        return "high", "User is completely unable to work due to hardware failure — high impact."

    if "multiple users" in t or "several users" in t or "my team" in t:
        return "high", "Issue affects multiple users — broader business impact than a single-user problem."

    # ── LOW ───────────────────────────────────────────
    if any(x in t for x in ["how to","how do i","setup","configure","slightly slow",
                              "minor","cosmetic","feature request","tip","advice","best way"]):
        return "low", "Non-urgent enquiry or minor inconvenience with no significant business impact."

    # ── MEDIUM ────────────────────────────────────────
    return "medium", "Single-user issue with workaround likely available — standard response time applies."


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