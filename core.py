# core.py

def classify_category(text):
    t = text.lower()

    if any(x in t for x in ["password","login","account","username","access"]):
        return "access"

    elif any(x in t for x in ["vpn","network","internet","wifi","connection","latency","slow","lag","delay","disconnect","outage"]):
        return "network"

    elif any(x in t for x in ["email","mail","outlook","attachment","inbox","send","receive"]):
        return "email"

    elif any(x in t for x in ["keyboard","mouse","laptop","printer","screen","audio","device"]):
        return "hardware"

    elif any(x in t for x in ["software","application","install","error","crash","update","bug","upload","download","database"]):
        return "software"

    return "general"


def rule_priority(text):
    t = text.lower()

    # 🔴 HIGH
    if any(x in t for x in [
        "down","not working","not working at all",
        "failed completely","crashed","cannot login",
        "cannot access","account locked","blocked",
        "not turning on"
    ]):
        return "high"

    # 🟡 MEDIUM
    if any(x in t for x in [
        "slow","delay","latency","takes long",
        "occasionally","sometimes","disconnects",
        "drops","freezing","not responding"
    ]):
        return "medium"

    # 🟢 LOW
    if any(x in t for x in [
        "how to","request","setup","need help",
        "forgot password","general help","install new"
    ]):
        return "low"

    return "medium"  # default safe


def should_escalate(priority):
    return priority == "high"