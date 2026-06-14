"""
Seed demo users and support tickets for TriageIQ.

Run from the backend directory:
    python scripts/seed_data.py

Optional flags:
    python scripts/seed_data.py --reset-seed   # delete existing SEED tickets, then re-seed
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_ROOT))

from motor.motor_asyncio import AsyncIOMotorClient

from app.core.config import settings
from app.services.classifier import classify_ticket
from app.services.security import hash_password

SEED_TICKET_PREFIX = "SEED - "

DEMO_USERS = [
    {
        "full_name": "Demo Admin",
        "email": "admin@triageiq.com",
        "password": "Admin@123",
        "role": "ADMIN",
    },
    {
        "full_name": "Demo Agent",
        "email": "agent@triageiq.com",
        "password": "Agent@123",
        "role": "AGENT",
    },
]

QUEUE_BY_CATEGORY = {
    "Billing": "Billing Support",
    "Technical": "Technical Support",
    "Account": "Account Support",
    "Feature Request": "Product Team",
    "Complaint": "Escalation Team",
}

# Realistic ticket templates: 11 per category -> 55 seed tickets total.
TICKET_TEMPLATES: dict[str, list[tuple[str, str]]] = {
    "Billing": [
        ("Duplicate subscription charge", "Customer was charged twice for the monthly subscription and needs an urgent refund."),
        ("Refund request for invoice #8821", "Customer requested a refund after being charged for an invoice they already paid."),
        ("Payment method update failed", "Customer payment method update failed and the billing profile could not be saved."),
        ("Unexpected price increase on renewal", "Customer noticed a price increase on renewal and wants billing clarification."),
        ("Card declined during checkout", "Customer card was declined during checkout even though the card should be valid."),
        ("Invoice PDF not received", "Customer did not receive the invoice PDF for last month's payment."),
        ("Subscription cancellation billing question", "Customer cancelled but was billed again and needs billing support."),
        ("Tax amount looks incorrect", "Customer says the tax amount on the invoice appears incorrect for their region."),
        ("Annual plan upgrade charge", "Customer upgraded to annual plan and wants confirmation of the prorated charge."),
        ("Refund still not processed", "Customer is frustrated because refund for billing error has not been processed yet."),
        ("Billing address update issue", "Customer cannot update billing address and payment keeps failing."),
    ],
    "Technical": [
        ("Server timeout during checkout", "Checkout fails with a timeout error and the customer cannot complete payment."),
        ("App crash on dashboard load", "The application crashes immediately when loading the dashboard after login."),
        ("Slow API response times", "Customer reports slow server response and degraded performance during peak hours."),
        ("Production outage reported", "Critical production service is down and users cannot access the platform."),
        ("Login failed with valid credentials", "Customer receives login failed error even with valid credentials."),
        ("File upload returns 500 error", "Customer cannot upload attachments because the server returns a 500 error."),
        ("Mobile app keeps crashing", "Customer mobile app crashes on launch after the latest update."),
        ("Webhook delivery failures", "Customer integration webhooks are failing with timeout errors."),
        ("Database connection error in reports", "Reports page shows database connection error for multiple users."),
        ("SSL certificate warning in browser", "Customer sees SSL certificate warning when accessing the admin portal."),
        ("Search feature not working", "Customer says search is broken and returns no results for known records."),
    ],
    "Account": [
        ("Cannot reset password", "Customer cannot reset password and is blocked from account access."),
        ("Account locked after failed login", "Customer account was locked after multiple failed login attempts."),
        ("Need access to admin panel", "Customer needs access restored to the admin panel after a profile update."),
        ("Two-factor authentication not working", "Customer cannot complete login because two-factor codes are not accepted."),
        ("Email change request", "Customer needs help changing the email address on their account."),
        ("Profile photo will not save", "Customer profile updates fail when trying to save a new profile photo."),
        ("Unable to invite team member", "Customer cannot invite a new team member due to account permission issue."),
        ("Session expires too quickly", "Customer keeps getting logged out and wants session timeout reviewed."),
        ("Deactivate old user account", "Customer needs an old employee account deactivated for security."),
        ("Merge duplicate accounts", "Customer has duplicate accounts and needs them merged into one login."),
        ("SSO login configuration help", "Customer needs assistance configuring SSO login for their organization."),
    ],
    "Feature Request": [
        ("Export report to CSV", "Customer suggested adding an export report feature to improve workflow."),
        ("Dark mode toggle request", "Customer submitted a suggestion to add a dark mode toggle and improve the UI."),
        ("Bulk ticket import feature", "Customer requested a feature to import support tickets in bulk from CSV."),
        ("Custom dashboard widgets", "Customer asked for customizable dashboard widgets for their support team."),
        ("Slack integration enhancement", "Customer wants improved Slack integration with richer notification options."),
        ("Advanced filtering on tickets", "Customer requested advanced filtering options on the tickets page."),
        ("Scheduled report emails", "Customer suggested scheduled report emails for weekly ticket summaries."),
        ("Role-based dashboard views", "Customer requested role-based dashboard views for managers and agents."),
        ("API rate limit configuration", "Customer asked for configurable API rate limits per integration key."),
        ("Multi-language support request", "Customer requested multi-language support for the customer portal."),
        ("Audit log export feature", "Customer wants an audit log export feature for compliance reviews."),
    ],
    "Complaint": [
        ("Angry complaint about outage", "Customer is angry and frustrated because production service is down."),
        ("Disappointed with support response time", "Customer is disappointed with slow support response and bad service."),
        ("Terrible experience during onboarding", "Customer had a terrible onboarding experience and wants escalation."),
        ("Unhappy with refund delay", "Customer is unhappy and filing a complaint about the delayed refund process."),
        ("Frustrated by repeated billing errors", "Customer is frustrated by repeated billing errors and poor communication."),
        ("Complaint about rude support agent", "Customer complaint about unhelpful and rude support interaction yesterday."),
        ("Bad service during critical incident", "Customer says they received bad service during a critical incident."),
        ("Escalation: unresolved for two weeks", "Customer demands escalation because their issue remains unresolved for two weeks."),
        ("Threatening to cancel enterprise plan", "Customer is angry and threatening to cancel the enterprise plan."),
        ("Complaint about misleading pricing", "Customer complaint that pricing on the website was misleading."),
        ("Unhappy with product quality decline", "Customer is disappointed and unhappy with recent product quality decline."),
    ],
}

STATUS_CYCLE = ["OPEN", "IN_PROGRESS", "RESOLVED", "CLOSED"]
PRIORITY_CYCLE = ["LOW", "MEDIUM", "HIGH", "URGENT"]
SENTIMENT_CYCLE = ["POSITIVE", "NEUTRAL", "NEGATIVE"]


def load_routing_rules() -> dict[str, str]:
    """Load queue routing rules from config when available."""
    rules_path = BACKEND_ROOT / "app" / "config" / "routing_rules.json"
    if not rules_path.is_file() or rules_path.stat().st_size == 0:
        return {}

    try:
        data = json.loads(rules_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}

    if isinstance(data, dict):
        return {str(key): str(value) for key, value in data.items()}
    return {}


def resolve_assigned_queue(category: str, routing_rules: dict[str, str]) -> str:
    return routing_rules.get(category) or QUEUE_BY_CATEGORY.get(category, "General Support")


def build_seed_tickets() -> list[dict]:
    """Build 55 varied seed tickets (11 per category)."""
    tickets: list[dict] = []
    routing_rules = load_routing_rules()
    ticket_index = 0

    for category, templates in TICKET_TEMPLATES.items():
        for local_index, (subject, description) in enumerate(templates):
            status = STATUS_CYCLE[ticket_index % len(STATUS_CYCLE)]
            priority = PRIORITY_CYCLE[(ticket_index + local_index) % len(PRIORITY_CYCLE)]
            sentiment = SENTIMENT_CYCLE[(ticket_index + local_index * 2) % len(SENTIMENT_CYCLE)]
            assigned_queue = resolve_assigned_queue(category, routing_rules)

            title = f"{SEED_TICKET_PREFIX}{category} #{local_index + 1:02d}: {subject}"
            classification = classify_ticket(title, description)

            confidence = round(0.78 + ((ticket_index * 7) % 18) / 100, 2)
            explanation = (
                f"Seed classification: category={category}, priority={priority}, "
                f"sentiment={sentiment}. Keyword engine also suggests "
                f"{classification['category']} / {classification['priority']} / "
                f"{classification['sentiment']} -> queue {classification['assigned_queue']}."
            )

            tickets.append(
                {
                    "title": title,
                    "description": description,
                    "customer_email": f"seed.customer{ticket_index + 1:02d}@example.com",
                    "status": status,
                    "category": category,
                    "priority": priority,
                    "sentiment": sentiment,
                    "assigned_queue": assigned_queue,
                    "confidence": confidence,
                    "explanation": explanation,
                    "assign_to_agent": ticket_index % 3 != 0,
                    "created_by_admin": ticket_index % 5 != 4,
                    "day_offset": 45 - (ticket_index % 45),
                    "hour_offset": (ticket_index * 5) % 24,
                }
            )
            ticket_index += 1

    return tickets


async def ensure_demo_users(db) -> dict[str, str]:
    user_ids: dict[str, str] = {}

    for demo_user in DEMO_USERS:
        email = demo_user["email"].lower()
        existing = await db.users.find_one({"email": email})

        if existing:
            user_ids[demo_user["role"]] = str(existing["_id"])
            print(f"User already exists: {email}")
            continue

        now = datetime.now(UTC)
        user_doc = {
            "full_name": demo_user["full_name"],
            "email": email,
            "role": demo_user["role"],
            "hashed_password": hash_password(demo_user["password"]),
            "is_active": True,
            "created_at": now,
        }
        result = await db.users.insert_one(user_doc)
        user_ids[demo_user["role"]] = str(result.inserted_id)
        print(f"Created user: {email}")

    return user_ids


async def delete_seed_tickets(db) -> int:
    result = await db.tickets.delete_many({"title": {"$regex": f"^{SEED_TICKET_PREFIX}"}})
    return result.deleted_count


async def seed_tickets(db, user_ids: dict[str, str], tickets: list[dict]) -> tuple[int, int]:
    admin_id = user_ids["ADMIN"]
    agent_id = user_ids["AGENT"]
    created_count = 0
    skipped_count = 0
    now = datetime.now(UTC)

    for ticket in tickets:
        existing = await db.tickets.find_one({"title": ticket["title"]})
        if existing:
            skipped_count += 1
            continue

        created_at = now - timedelta(days=ticket["day_offset"], hours=ticket["hour_offset"])
        updated_at = created_at + timedelta(hours=4 + (created_count % 12))

        assigned_agent_id = agent_id if ticket["assign_to_agent"] else None
        created_by = admin_id if ticket["created_by_admin"] else agent_id

        ticket_doc = {
            "title": ticket["title"],
            "description": ticket["description"],
            "customer_email": ticket["customer_email"].lower(),
            "status": ticket["status"],
            "category": ticket["category"],
            "priority": ticket["priority"],
            "sentiment": ticket["sentiment"],
            "assigned_queue": ticket["assigned_queue"],
            "confidence": ticket["confidence"],
            "classification_confidence": ticket["confidence"],
            "explanation": ticket["explanation"],
            "classification_explanation": ticket["explanation"],
            "assigned_agent_id": assigned_agent_id,
            "created_by": created_by,
            "created_at": created_at,
            "updated_at": updated_at,
        }

        await db.tickets.insert_one(ticket_doc)
        created_count += 1

    return created_count, skipped_count


def print_summary(created_count: int, skipped_count: int, total_defined: int, reset_count: int) -> None:
    print()
    print("=" * 60)
    print("TriageIQ seed data complete")
    print("=" * 60)
    print()
    print("Demo login credentials:")
    print("  Admin -> admin@triageiq.com / Admin@123")
    print("  Agent -> agent@triageiq.com / Agent@123")
    print()
    if reset_count:
        print(f"Seed tickets removed (--reset-seed): {reset_count}")
    print(f"Tickets created: {created_count}")
    print(f"Tickets skipped (already existed): {skipped_count}")
    print(f"Total seed tickets defined: {total_defined}")
    print()
    print("Note: Re-running this script is safe. Existing demo users and")
    print("SEED tickets are not duplicated. Use --reset-seed to recreate")
    print("seed tickets only.")
    print("=" * 60)


async def run_seed(reset_seed: bool) -> None:
    client = AsyncIOMotorClient(settings.mongodb_uri)
    db = client[settings.mongodb_db]
    tickets = build_seed_tickets()
    reset_count = 0

    try:
        await db.users.create_index("email", unique=True)

        if reset_seed:
            reset_count = await delete_seed_tickets(db)
            print(f"Removed {reset_count} existing seed ticket(s).")

        print("Seeding demo users...")
        user_ids = await ensure_demo_users(db)

        if "ADMIN" not in user_ids or "AGENT" not in user_ids:
            raise RuntimeError("Failed to resolve demo user IDs.")

        print("Seeding support tickets...")
        created_count, skipped_count = await seed_tickets(db, user_ids, tickets)
        print_summary(created_count, skipped_count, len(tickets), reset_count)
    finally:
        client.close()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Seed TriageIQ demo users and tickets.")
    parser.add_argument(
        "--reset-seed",
        action="store_true",
        help="Delete existing SEED tickets (title prefix 'SEED - ') before seeding.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    asyncio.run(run_seed(reset_seed=args.reset_seed))


if __name__ == "__main__":
    main()
