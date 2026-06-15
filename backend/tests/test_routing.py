"""Unit tests for smart queue routing."""

from app.services.routing import DEFAULT_QUEUE, resolve_assigned_queue


def test_urgent_billing_routes_to_escalations() -> None:
    queue = resolve_assigned_queue("Billing", "URGENT", "NEGATIVE")

    assert queue == "Escalations"


def test_technical_routes_to_technical_support() -> None:
    queue = resolve_assigned_queue("Technical", "HIGH", "NEGATIVE")

    assert queue == "Technical Support"


def test_feature_request_routes_to_product_team() -> None:
    queue = resolve_assigned_queue("Feature Request", "LOW", "NEUTRAL")

    assert queue == "Product Team"


def test_complaint_routes_to_escalations() -> None:
    queue = resolve_assigned_queue("Complaint", "HIGH", "NEGATIVE")

    assert queue == "Escalations"


def test_negative_general_routes_to_customer_success() -> None:
    queue = resolve_assigned_queue("General", "MEDIUM", "NEGATIVE")

    assert queue == "Customer Success"


def test_default_fallback_routes_to_general_support() -> None:
    queue = resolve_assigned_queue("Unknown Category", "MEDIUM", "NEUTRAL")

    assert queue == DEFAULT_QUEUE
