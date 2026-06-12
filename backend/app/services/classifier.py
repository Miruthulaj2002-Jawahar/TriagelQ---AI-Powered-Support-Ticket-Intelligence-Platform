def classify_ticket(title: str, description: str) -> dict:
    text = f"{title} {description}".lower()

    category_rules = [
        (
            "Billing",
            [
                "payment",
                "billing",
                "invoice",
                "refund",
                "charged",
                "card",
                "subscription",
                "price",
            ],
            "Billing Support",
        ),
        (
            "Technical",
            [
                "error",
                "bug",
                "crash",
                "server",
                "login failed",
                "not working",
                "slow",
                "timeout",
                "broken",
            ],
            "Technical Support",
        ),
        (
            "Account",
            [
                "login",
                "password",
                "reset",
                "account",
                "access",
                "locked",
                "profile",
            ],
            "Account Support",
        ),
        (
            "Feature Request",
            [
                "feature",
                "request",
                "add",
                "improve",
                "enhancement",
                "suggestion",
            ],
            "Product Team",
        ),
        (
            "Complaint",
            [
                "angry",
                "disappointed",
                "bad service",
                "terrible",
                "frustrated",
                "complaint",
                "unhappy",
            ],
            "Escalation Team",
        ),
    ]

    category = "General"
    assigned_queue = "General Support"
    for rule_category, keywords, queue in category_rules:
        if any(keyword in text for keyword in keywords):
            category = rule_category
            assigned_queue = queue
            break

    urgent_keywords = [
        "urgent",
        "immediately",
        "critical",
        "down",
        "outage",
        "cannot access",
        "blocked",
        "production",
    ]
    high_keywords = [
        "failed",
        "error",
        "charged",
        "refund",
        "cannot login",
        "broken",
        "crash",
    ]
    low_keywords = ["question", "suggestion", "feedback", "minor"]

    if any(keyword in text for keyword in urgent_keywords):
        priority = "URGENT"
    elif any(keyword in text for keyword in high_keywords):
        priority = "HIGH"
    elif any(keyword in text for keyword in low_keywords):
        priority = "LOW"
    else:
        priority = "MEDIUM"

    negative_keywords = [
        "angry",
        "disappointed",
        "frustrated",
        "terrible",
        "bad",
        "not working",
        "failed",
        "issue",
        "problem",
        "complaint",
    ]
    positive_keywords = [
        "thanks",
        "thank you",
        "great",
        "good",
        "helpful",
        "appreciate",
    ]

    if any(keyword in text for keyword in negative_keywords):
        sentiment = "NEGATIVE"
    elif any(keyword in text for keyword in positive_keywords):
        sentiment = "POSITIVE"
    else:
        sentiment = "NEUTRAL"

    return {
        "category": category,
        "priority": priority,
        "sentiment": sentiment,
        "assigned_queue": assigned_queue,
    }
