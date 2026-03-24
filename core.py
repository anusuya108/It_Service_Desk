# core.py — rule-based logic used by agent.py

def classify_issue(issue: str):
    """Returns (category, priority, reason, confidence)"""
    issue_lower = issue.lower()
    reason = "rule-based"
    confidence = 0.9

    # ── CATEGORY ──────────────────────────────────────
    if any(x in issue_lower for x in [
        "internet", "wifi", "network", "vpn", "server", "connection",
        "shared drive", "website", "lan", "sync", "remote"
    ]):
        category = "network"

    elif any(x in issue_lower for x in [
        "password", "login", "account", "access", "permission", "admin", "mfa"
    ]):
        category = "account"

    elif any(x in issue_lower for x in [
        "laptop", "keyboard", "mouse", "monitor", "battery",
        "disk", "screen", "fan", "usb", "printer", "spilled", "water"
    ]):
        category = "hardware"

    elif any(x in issue_lower for x in [
        "software", "application", "erp", "teams", "excel",
        "crash", "error", "update", "freeze", "opening", "outlook"
    ]):
        category = "software"

    else:
        category = "other"
        confidence = 0.5

    # ── PRIORITY ──────────────────────────────────────
    if "disk failure" in issue_lower:
        priority = "critical"

    elif any(x in issue_lower for x in ["all users", "everyone", "entire"]) and "down" in issue_lower:
        priority = "critical"

    elif "erp" in issue_lower and "down" in issue_lower:
        priority = "critical"

    elif "ransom" in issue_lower or "breach" in issue_lower or "data loss" in issue_lower:
        priority = "critical"

    elif any(x in issue_lower for x in [
        "won't turn on", "not turning on", "overheat", "shuts down", "cracked",
        "spilled", "water"
    ]):
        priority = "high"

    elif any(x in issue_lower for x in [
        "keyboard", "mouse", "battery", "slow", "logs out", "flickering"
    ]):
        priority = "low"

    elif any(x in issue_lower for x in [
        "crash", "crashes", "not working", "not responding",
        "remote desktop", "mfa", "connect", "forgot", "password"
    ]):
        priority = "medium"

    else:
        priority = "medium"

    return category, priority, reason, confidence


def should_escalate(category: str, priority: str, issue: str):
    """Returns (escalated: bool, reason: str)"""
    issue_lower = issue.lower()

    if priority == "critical":
        return True, "Critical priority — requires immediate senior attention"

    if any(x in issue_lower for x in ["data loss", "security breach", "ransom"]):
        return True, "Security or data loss incident — escalate to SOC"

    if priority == "high":
        return True, "High priority — escalated to Level 2 support"

    return False, ""


def get_resolution(category: str, issue: str):
    """Returns a resolution string based on category"""
    resolutions = {
        "network":  "Restart router or VPN client. Check network cables. If the issue affects multiple users, contact the Network Operations Centre.",
        "account":  "Reset your password via the self-service portal or contact the helpdesk. If MFA is failing, contact the IAM team.",
        "hardware": "Check all physical connections. If the device is damaged (e.g. liquid spill), do not power on — bring it to the IT desk for inspection.",
        "software": "Restart the application. If it persists, try reinstalling or updating the software. Clear the application cache if available.",
        "other":    "Please provide more details so we can assist. Basic troubleshooting: restart your device and try again.",
    }
    return resolutions.get(category, "No resolution available. Please contact the helpdesk.")