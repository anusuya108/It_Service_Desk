# core.py — rule-based logic + honest confidence scoring

def classify_issue(issue: str):
    """
    Returns (category, priority, reason, confidence)
    confidence is REAL — calculated from keyword match strength
    """
    issue_lower = issue.lower()

    # ── KEYWORD BANKS ─────────────────────────────────
    network_kw  = ["internet","wifi","network","vpn","server","connection",
                   "shared drive","website","lan","sync","remote","firewall","ping"]
    account_kw  = ["password","login","account","access","permission","admin",
                   "mfa","locked out","sign in","username","credentials","2fa"]
    hardware_kw = ["laptop","keyboard","mouse","monitor","battery","disk",
                   "screen","fan","usb","printer","spilled","water","cable",
                   "charger","hardware","headset","webcam","docking"]
    software_kw = ["software","application","erp","teams","excel","crash",
                   "error","update","freeze","opening","outlook","install",
                   "uninstall","app","browser","windows","office","adobe"]

    scores = {
        "network":  sum(1 for k in network_kw  if k in issue_lower),
        "account":  sum(1 for k in account_kw  if k in issue_lower),
        "hardware": sum(1 for k in hardware_kw if k in issue_lower),
        "software": sum(1 for k in software_kw if k in issue_lower),
    }

    best_cat   = max(scores, key=scores.get)
    best_score = scores[best_cat]

    # Real confidence based on match strength
    if best_score == 0:
        category   = "other"
        confidence = 0.4
        reason     = "no keyword match — LLM will classify"
    elif best_score == 1:
        category   = best_cat
        confidence = 0.65
        reason     = f"weak rule match ({best_cat}, 1 keyword)"
    elif best_score == 2:
        category   = best_cat
        confidence = 0.80
        reason     = f"rule-based ({best_cat}, {best_score} keywords)"
    else:
        category   = best_cat
        confidence = 0.95
        reason     = f"strong rule match ({best_cat}, {best_score} keywords)"

    # ── PRIORITY ──────────────────────────────────────
    if any(x in issue_lower for x in ["disk failure","complete outage","data loss","ransomware"]):
        priority = "critical"

    elif any(x in issue_lower for x in ["all users","everyone","entire","whole office"]) \
         and "down" in issue_lower:
        priority = "critical"

    elif "erp" in issue_lower and "down" in issue_lower:
        priority = "critical"

    elif any(x in issue_lower for x in ["ransom","breach","hacked","virus","malware"]):
        priority = "critical"

    elif any(x in issue_lower for x in [
        "won't turn on","not turning on","overheat","shuts down",
        "cracked","spilled","water","not starting","physical damage"
    ]):
        priority = "high"

    elif any(x in issue_lower for x in [
        "crash","crashes","not working","not responding","can't connect",
        "mfa","remote desktop","forgot","locked out","multiple users"
    ]):
        priority = "medium"

    elif any(x in issue_lower for x in [
        "slow","flickering","how to","setup","configure","feature"
    ]):
        priority = "low"

    else:
        priority = "medium"

    return category, priority, reason, confidence


def should_escalate(category: str, priority: str, issue: str):
    """Rule-based pre-check. Final escalation decision is made by LLM in agent.py"""
    issue_lower = issue.lower()

    if priority == "critical":
        return True, "Critical priority — immediate senior attention required"

    if any(x in issue_lower for x in ["ransom","breach","hacked","virus","malware","data loss"]):
        return True, "Security incident — escalate to SOC immediately"

    if priority == "high":
        return True, "High priority — escalated to Level 2 support"

    return False, ""