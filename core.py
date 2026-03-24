# core.py

def classify_issue(issue: str):
    """
    Returns (category, priority, priority_reason, match_strength)
    match_strength: "strong" | "weak" | "none"
    """
    t = issue.lower()

    # ── SECURITY OVERRIDE (ADDED) ─────────────────────
    if any(x in t for x in ["ransom","suspicious link","phishing","security breach","hacked"]):
        priority, priority_reason = _get_priority(t)
        return "other", priority, priority_reason, "strong"

    # ── FILE TRANSFER OVERRIDE (ADDED) ────────────────
    if "transfer" in t and any(x in t for x in ["files","data","documents"]):
        priority, priority_reason = _get_priority(t)
        return "other", priority, priority_reason, "strong"

    # ── CATEGORY KEYWORD BANKS ────────────────────────
    network_kw = [
        "internet","wifi","wi-fi","network","vpn","connection","shared drive",
        "file share","drive","lan","remote","bandwidth","outage","offline",
        "inaccessible","cannot access drive","slow network"
    ]

    account_kw = [
        "password","login","account","access","permission","admin rights",
        "mfa","locked out","sign in","username","credentials","2fa",
        "admin"
        # ❌ removed onboarding-related from here
    ]

    hardware_kw = [
        "laptop","keyboard","mouse","monitor","battery","disk","screen",
        "fan","usb","printer","spilled","water","cable","charger","webcam",
        "headset","docking","broken","physical","device","bluetooth","flickering",
        "sticky keys","coffee","offline printer","not detected",
        "printer offline","shows offline"   # ✅ ADDED
    ]

    software_kw = [
        "software","application","erp","teams","excel","crash","error",
        "update","freeze","outlook","install","app","browser","windows",
        "office","adobe","not opening","slow","bug","not responding",
        "out-of-office","formula","database","production"
    ]

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

    priority, priority_reason = _get_priority(t)
    return category, priority, priority_reason, match_strength


def _get_priority(t: str):

    # ── CRITICAL ──────────────────────────────────────
    if any(x in t for x in ["ransom","security breach","hacked","cyberattack",
                              "virus outbreak","malware spreading","data loss"]):
        return "critical", "Active security incident — immediate escalation with no delay."

    if any(x in t for x in ["entire office","whole office","everyone","all staff",
                              "all users","company-wide","entire building"]) \
       and any(x in t for x in ["down","offline","not working","unavailable","cannot work"]):
        return "critical", "Office-wide outage — all users affected."

    if any(x in t for x in ["erp","production database","production server","200 users"]) \
       and any(x in t for x in ["down","offline","not working","cannot work"]):
        return "critical", "Critical business system down."

    if "someone is logged" in t or "logged into my account" in t or "don't recognise" in t:
        return "critical", "Possible account compromise."

    # ── LOW OVERRIDE (MOVED ABOVE HIGH) ───────────────
    if "sticky keys" in t or ("coffee" in t and "keyboard" in t):
        return "low", "Minor peripheral damage — low impact, workaround available."

    # ── HIGH ──────────────────────────────────────────
    if any(x in t for x in ["ceo","cto","cfo","coo","vp ","vice president",
                              "director","executive","vip","c-suite","board member"]):
        return "high", "Executive impact."

    if any(x in t for x in ["won't turn on","not turning on","spilled","water damage",
                              "coffee","cracked","overheat","shuts down","cannot work",
                              "completely blocked","not starting","physical damage"]):
        return "high", "User unable to work."

    if any(x in t for x in ["entire finance department","entire department",
                              "whole team","multiple users","all of us"]):
        return "high", "Multiple users affected."

    if "antivirus" in t and any(x in t for x in ["flagged","detected","threat","virus","malware"]):
        return "high", "Security threat detected."

    # ── LOW ───────────────────────────────────────────
    if any(x in t for x in ["how do i","how to","setup","configure","out-of-office",
                              "feature request","tip","advice","best way","formula","ref error"]):
        return "low", "Informational request."

    if any(x in t for x in ["slow","flickering","battery drains","fan is loud",
                              "bluetooth","disconnecting","keeps disconnecting",
                              "sticky","minor","cosmetic"]):
        return "low", "Minor issue."

    # ❌ REMOVED onboarding from LOW

    # ── MEDIUM (UPDATED) ──────────────────────────────
    if any(x in t for x in ["new employee","set up account","onboarding"]):
        return "medium", "Standard onboarding request."

    return "medium", "Single-user issue."


def should_escalate_rules(category: str, priority: str, issue: str):
    t = issue.lower()

    if priority == "critical":
        return True, "Critical — immediate escalation."

    if any(x in t for x in ["ransom","breach","hacked","virus","malware",
                              "suspicious link","someone logged"]):
        return True, "Security incident."

    return False, ""


def get_team(category: str, issue: str) -> str:
    t = issue.lower()
    if any(x in t for x in ["ransom","breach","hacked","virus","malware","suspicious"]):
        return "SOC"

    return {
        "network":  "NOC",
        "account":  "IAM",
        "hardware": "Infrastructure",
        "software": "Software Support",
    }.get(category, "Support")


def get_sla(priority: str) -> str:
    return {
        "critical": "1 hour",
        "high":     "4 hours",
        "medium":   "1 business day",
        "low":      "3 business days",
    }.get(priority, "1 business day")