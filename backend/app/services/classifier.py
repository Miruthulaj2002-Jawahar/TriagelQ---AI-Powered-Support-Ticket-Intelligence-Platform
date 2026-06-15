from app.services.routing import resolve_assigned_queue

CATEGORY_RULES: list[tuple[str, list[str]]] = [
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
    ),
]

URGENT_KEYWORDS = [
    "urgent",
    "immediately",
    "critical",
    "down",
    "outage",
    "cannot access",
    "blocked",
    "production",
]
HIGH_KEYWORDS = [
    "failed",
    "error",
    "charged",
    "refund",
    "cannot login",
    "broken",
    "crash",
]
LOW_KEYWORDS = ["question", "suggestion", "feedback", "minor"]

NEGATIVE_KEYWORDS = [
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
POSITIVE_KEYWORDS = [
    "thanks",
    "thank you",
    "great",
    "good",
    "helpful",
    "appreciate",
]


def _compute_confidence(matched_keywords: list[str], category: str) -> float:
    if category == "General" or not matched_keywords:
        return 0.55
    score = 0.65 + min(len(matched_keywords) * 0.08, 0.3)
    return round(min(score, 0.97), 2)


def _build_explanation(
    category: str,
    priority: str,
    sentiment: str,
    matched_keywords: list[str],
    assigned_queue: str,
) -> str:
    keyword_text = ", ".join(matched_keywords) if matched_keywords else "general language"
    return (
        f"Classified as {category} with {priority} priority and {sentiment} sentiment "
        f"based on keywords: {keyword_text}. Routed to {assigned_queue}."
    )


def classify_ticket(title: str, description: str) -> dict:
    text = f"{title} {description}".lower()

    category = "General"
    matched_keywords: list[str] = []
    for rule_category, keywords in CATEGORY_RULES:
        hits = [keyword for keyword in keywords if keyword in text]
        if hits:
            category = rule_category
            matched_keywords = hits
            break

    if any(keyword in text for keyword in URGENT_KEYWORDS):
        priority = "URGENT"
    elif any(keyword in text for keyword in HIGH_KEYWORDS):
        priority = "HIGH"
    elif any(keyword in text for keyword in LOW_KEYWORDS):
        priority = "LOW"
    else:
        priority = "MEDIUM"

    if any(keyword in text for keyword in NEGATIVE_KEYWORDS):
        sentiment = "NEGATIVE"
    elif any(keyword in text for keyword in POSITIVE_KEYWORDS):
        sentiment = "POSITIVE"
    else:
        sentiment = "NEUTRAL"

    assigned_queue = resolve_assigned_queue(category, priority, sentiment)
    confidence = _compute_confidence(matched_keywords, category)
    explanation = _build_explanation(
        category, priority, sentiment, matched_keywords, assigned_queue
    )

    return {
        "category": category,
        "priority": priority,
        "sentiment": sentiment,
        "assigned_queue": assigned_queue,
        "confidence": confidence,
        "explanation": explanation,
    }
