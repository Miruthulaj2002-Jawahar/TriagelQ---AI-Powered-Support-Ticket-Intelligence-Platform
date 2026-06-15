"""Smart queue routing based on classification results."""

DEFAULT_QUEUE = "General Support"

CATEGORY_QUEUES = {
    "Billing": "Billing Support",
    "Technical": "Technical Support",
    "Account": "Account Support",
    "Feature Request": "Product Team",
    "Complaint": "Escalations",
    "General": "General Support",
}


def resolve_assigned_queue(category: str, priority: str, sentiment: str) -> str:
    """
    Route a ticket to a support queue using category, priority, and sentiment.

    Rules (in order):
    - Urgent billing issues escalate immediately
    - Complaint category goes to Escalations
    - Negative general feedback goes to Customer Success
    - Otherwise use the default queue for the category
    """
    if category == "Billing" and priority == "URGENT":
        return "Escalations"

    if category == "Complaint":
        return "Escalations"

    if sentiment == "NEGATIVE" and category == "General":
        return "Customer Success"

    return CATEGORY_QUEUES.get(category, DEFAULT_QUEUE)
