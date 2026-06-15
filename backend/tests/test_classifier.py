"""Unit tests for offline keyword-based ticket classification."""

from app.services.classifier import classify_ticket


def test_classifier_billing_category() -> None:
    result = classify_ticket(
        "Refund request",
        "I was charged twice on my invoice and need a refund for billing.",
    )

    assert result["category"] == "Billing"
    assert result["assigned_queue"] == "Billing Support"
    assert result["priority"] in {"LOW", "MEDIUM", "HIGH", "URGENT"}
    assert result["sentiment"] in {"POSITIVE", "NEUTRAL", "NEGATIVE"}


def test_classifier_technical_urgent_negative() -> None:
    result = classify_ticket(
        "Production outage",
        "Critical server error — production is down and users cannot access the app. Serious problem.",
    )

    assert result["category"] == "Technical"
    assert result["assigned_queue"] == "Technical Support"
    assert result["priority"] == "URGENT"
    assert result["sentiment"] == "NEGATIVE"


def test_classifier_account_category() -> None:
    result = classify_ticket(
        "Password reset issue",
        "Customer cannot reset password and account access is locked after failed login.",
    )

    assert result["category"] == "Account"
    assert result["assigned_queue"] == "Account Support"
    assert result["priority"] in {"HIGH", "MEDIUM", "URGENT"}


def test_classifier_feature_request_low_neutral() -> None:
    result = classify_ticket(
        "Feature suggestion",
        "Minor feedback: please add a dark mode enhancement suggestion.",
    )

    assert result["category"] == "Feature Request"
    assert result["assigned_queue"] == "Product Team"
    assert result["priority"] == "LOW"
    assert result["sentiment"] == "NEUTRAL"


def test_classifier_complaint_negative_sentiment() -> None:
    result = classify_ticket(
        "Terrible support experience",
        "Customer is angry and frustrated filing a complaint about bad service.",
    )

    assert result["category"] == "Complaint"
    assert result["sentiment"] == "NEGATIVE"
    assert result["assigned_queue"] == "Escalations"


def test_classifier_returns_confidence_and_explanation() -> None:
    result = classify_ticket(
        "Billing invoice error",
        "Customer was charged twice on invoice and needs urgent billing help.",
    )

    assert isinstance(result["confidence"], float)
    assert 0.0 < result["confidence"] <= 1.0
    assert isinstance(result["explanation"], str)
    assert "Billing" in result["explanation"]
    assert "Classified as" in result["explanation"]


def test_classifier_positive_sentiment() -> None:
    result = classify_ticket(
        "Thanks for the help",
        "Thank you — the support team was great and very helpful.",
    )

    assert result["sentiment"] == "POSITIVE"
    assert result["category"] == "General"
    assert result["assigned_queue"] == "General Support"
