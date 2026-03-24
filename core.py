# core.py

def classify_category(text):
    t = text.lower()

    if any(x in t for x in ["password","login","account","access","username"]):
        return "access"

    elif any(x in t for x in ["vpn","network","internet","wifi","connection","latency"]):
        return "network"

    elif any(x in t for x in ["email","mail","outlook","attachment"]):
        return "email"

    elif any(x in t for x in ["keyboard","mouse","laptop","printer","screen","audio"]):
        return "hardware"

    elif any(x in t for x in ["software","application","install","error","crash","update"]):
        return "software"

    return "general"


def rule_priority(text):
    t = text.lower()

    # critical
    if any(x in t for x in ["ransom","hacked","breach","malware"]):
        return "critical", 0.95

    # high signals
    if any(x in t for x in ["down","crash","failed","not working"]):
        return "high", 0.9

    if any(x in t for x in ["every hour","frequently","keeps happening"]):
        return "high", 0.85

    # low signals
    if any(x in t for x in ["how to","request","need help","setup"]):
        return "low", 0.8
    
    if any(x in t for x in ["completely","not at all","unable to"]):
        return "high", 0.9

    return None, None


def should_escalate(priority, confidence):
    # STRICT alignment with dataset
    if priority in ["high", "critical"]:
        return True

    return False