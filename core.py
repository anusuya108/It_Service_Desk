# core.py

def classify_issue(issue: str):
    issue = issue.lower()

    # CATEGORY
    if any(x in issue for x in ["laptop", "monitor", "keyboard", "mouse", "water", "flicker"]):
        category = "hardware"
    elif any(x in issue for x in ["internet", "vpn", "wifi", "network"]):
        category = "network"
    elif any(x in issue for x in ["password", "login", "account", "access"]):
        category = "account"
    elif any(x in issue for x in ["crash", "erp", "software", "application", "teams"]):
        category = "software"
    else:
        category = "other"

    # PRIORITY
    if any(x in issue for x in ["entire office", "everyone", "all users", "system down", "erp"]):
        priority = "critical"
    elif any(x in issue for x in ["water", "not turn on", "down", "can't work"]):
        priority = "high"
    elif any(x in issue for x in ["vpn", "password", "login"]):
        priority = "medium"
    else:
        priority = "low"

    reason = f"Keyword-based detection → category={category}, priority={priority}"
    return category, priority, reason


def should_escalate(category, priority, issue):
    issue = issue.lower()

    if priority == "critical":
        return True, "Critical system failure"

    if category == "hardware" and "water" in issue:
        return True, "Physical hardware damage"

    if "ransomware" in issue or "security" in issue:
        return True, "Security incident"

    return False, "Handled at Level 1"


def get_resolution(category):
    if category == "account":
        return "Reset password via SSO portal or contact IT admin."

    if category == "hardware":
        return "Do not power on device. Submit hardware repair request."

    if category == "network":
        return "Check router or VPN connection. Contact IT if persists."

    if category == "software":
        return "Restart or reinstall the application."

    return "Contact IT support."