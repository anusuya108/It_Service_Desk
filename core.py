# core.py

def classify_issue(issue: str):
    issue_lower = issue.lower()

    # CATEGORY + REASON
    if any(x in issue_lower for x in ["laptop", "monitor", "keyboard", "mouse", "water", "flicker"]):
        category = "hardware"
        cat_reason = "Detected physical device keywords → hardware issue"
        confidence = 0.9

    elif any(x in issue_lower for x in ["internet", "vpn", "wifi", "network"]):
        category = "network"
        cat_reason = "Detected connectivity-related keywords → network issue"
        confidence = 0.88

    elif any(x in issue_lower for x in ["password", "login", "account", "access"]):
        category = "account"
        cat_reason = "Detected authentication-related keywords → account issue"
        confidence = 0.85

    elif any(x in issue_lower for x in ["crash", "erp", "software", "application", "teams"]):
        category = "software"
        cat_reason = "Detected application-related keywords → software issue"
        confidence = 0.87

    else:
        category = "other"
        cat_reason = "No clear keywords → fallback category"
        confidence = 0.6

    # PRIORITY + REASON
    if any(x in issue_lower for x in ["entire office", "everyone", "all users", "system down", "erp"]):
        priority = "critical"
        pri_reason = "Multiple users/system outage → critical priority"
        confidence += 0.05

    elif any(x in issue_lower for x in ["water", "not turn on", "down", "can't work"]):
        priority = "high"
        pri_reason = "Device failure or blocking issue → high priority"

    elif any(x in issue_lower for x in ["vpn", "password", "login"]):
        priority = "medium"
        pri_reason = "Single user access issue → medium priority"

    else:
        priority = "low"
        pri_reason = "Minor issue → low priority"
        confidence -= 0.1

    reason = f"{cat_reason}. {pri_reason}."

    return category, priority, reason, round(confidence, 2)


def should_escalate(category, priority, issue):
    issue_lower = issue.lower()

    if priority == "critical":
        return True, "Critical system outage requires immediate escalation"

    if category == "hardware" and "water" in issue_lower:
        return True, "Water damage requires physical inspection"

    if "ransomware" in issue_lower or "security" in issue_lower:
        return True, "Security incident requires specialized team"

    return False, "Issue can be resolved at Level 1"


def get_resolution(category):
    if category == "account":
        return "Reset password via SSO portal. If unsuccessful, contact IT admin."

    if category == "hardware":
        return "Do NOT power on device. Disconnect power and submit hardware repair request."

    if category == "network":
        return "Check Wi-Fi/VPN connection. Restart router. Contact IT if issue persists."

    if category == "software":
        return "Restart application. Reinstall if issue continues."

    return "Contact IT support for further assistance."