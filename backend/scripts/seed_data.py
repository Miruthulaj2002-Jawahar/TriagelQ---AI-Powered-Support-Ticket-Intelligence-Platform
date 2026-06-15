"""
Seed demo users and support tickets for TriageIQ.

Run from the backend directory (local):
    python scripts/seed_data.py

With Docker Compose (from repo root):
    docker compose exec backend python scripts/seed_data.py

Recreate seed tickets (removes existing SEED tickets first):
    python scripts/seed_data.py --reset-seed
    docker compose exec backend python scripts/seed_data.py --reset-seed

Idempotent by default: existing demo users and tickets whose titles start with
"SEED - " are skipped, so re-running does not create duplicates.

Requires MONGODB_URI and JWT_SECRET (see .env.example). Demo logins:
  Admin -> admin@triageiq.com / Admin@123
  Agent -> agent@triageiq.com / Agent@123
"""

from __future__ import annotations

import argparse
import asyncio
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_ROOT))

from motor.motor_asyncio import AsyncIOMotorClient

from app.core.config import settings
from app.services.security import hash_password
from app.services.ticket_mapping import compute_effective_category, compute_effective_priority

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
    "Complaint": "Escalations",
}

ASSIGNED_QUEUES = [
    "Billing Support",
    "Technical Support",
    "Account Support",
    "Product Team",
    "Escalations",
    "Customer Success",
    "General Support",
]

# ticket_index -> override spec (only applied when values differ from AI classification)
MANUAL_OVERRIDE_SPECS: dict[int, dict[str, str]] = {
    0: {
        "category": "Technical",
        "reason": "Customer confirmed this is a checkout API failure, not billing.",
    },
    4: {
        "priority": "URGENT",
        "reason": "Enterprise customer; billing block is revenue-critical.",
    },
    11: {
        "category": "Complaint",
        "reason": "Repeated outage reports escalated as a service complaint.",
    },
    18: {
        "priority": "HIGH",
        "reason": "Account lock is blocking an entire team from SSO login.",
    },
    27: {
        "category": "Technical",
        "reason": "Export feature request depends on a broken reports API.",
    },
    36: {
        "priority": "MEDIUM",
        "reason": "Customer agreed to lower urgency after workaround was shared.",
    },
    44: {
        "category": "Billing",
        "reason": "Complaint is specifically about incorrect invoice totals.",
    },
    52: {
        "category": "Technical",
        "priority": "URGENT",
        "reason": "Production outage misclassified; both category and priority corrected.",
    },
}

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


def resolve_assigned_queue(
    category: str,
    priority: str,
    sentiment: str,
    ticket_index: int,
) -> str:
    """Pick a realistic queue with category defaults and cross-team variety."""
    default = QUEUE_BY_CATEGORY.get(category, "General Support")

    if category == "Complaint" or (category == "Technical" and priority == "URGENT"):
        return "Escalations"
    if sentiment == "POSITIVE" and ticket_index % 4 == 0:
        return "Customer Success"
    if category == "Feature Request" and ticket_index % 3 == 1:
        return "Product Team"
    if priority == "LOW" and sentiment == "NEUTRAL" and ticket_index % 5 == 2:
        return "General Support"

    return default if ticket_index % 7 != 3 else ASSIGNED_QUEUES[ticket_index % len(ASSIGNED_QUEUES)]


def build_ai_explanation(category: str, priority: str, sentiment: str, confidence: float) -> str:
    return (
        f"AI classified as {category} with {priority} priority and {sentiment} sentiment "
        f"(confidence {confidence:.2f}). Keyword and routing rules matched support queue patterns."
    )


def apply_manual_override(
    ai_category: str,
    ai_priority: str,
    override_spec: dict[str, str],
    *,
    overridden_by: str,
    overridden_at: datetime,
) -> dict:
    category_override = override_spec.get("category")
    priority_override = override_spec.get("priority")

    if category_override == ai_category:
        category_override = None
    if priority_override == ai_priority:
        priority_override = None

    preview = {
        "ai_category": ai_category,
        "ai_priority": ai_priority,
        "category_override": category_override,
        "priority_override": priority_override,
    }
    ai_fields = {"ai_category": ai_category, "ai_priority": ai_priority}

    effective_category = compute_effective_category(preview, ai_fields)
    effective_priority = compute_effective_priority(preview, ai_fields)

    has_real_override = (
        category_override is not None and category_override != ai_category
    ) or (priority_override is not None and priority_override != ai_priority)

    if not has_real_override:
        return {}

    return {
        "category_override": category_override,
        "priority_override": priority_override,
        "override_reason": override_spec.get("reason"),
        "overridden_by": overridden_by,
        "overridden_at": overridden_at,
        "category": effective_category,
        "priority": effective_priority,
    }


def build_seed_tickets() -> list[dict]:
    """Build 55 varied seed tickets (11 per category)."""
    tickets: list[dict] = []
    ticket_index = 0

    for category, templates in TICKET_TEMPLATES.items():
        for local_index, (subject, description) in enumerate(templates):
            status = STATUS_CYCLE[ticket_index % len(STATUS_CYCLE)]
            priority = PRIORITY_CYCLE[(ticket_index + local_index) % len(PRIORITY_CYCLE)]
            sentiment = SENTIMENT_CYCLE[(ticket_index + local_index * 2) % len(SENTIMENT_CYCLE)]
            assigned_queue = resolve_assigned_queue(category, priority, sentiment, ticket_index)
            confidence = round(0.78 + ((ticket_index * 7) % 18) / 100, 2)

            title = f"{SEED_TICKET_PREFIX}{category} #{local_index + 1:02d}: {subject}"
            ai_explanation = build_ai_explanation(category, priority, sentiment, confidence)

            tickets.append(
                {
                    "title": title,
                    "description": description,
                    "customer_email": f"seed.customer{ticket_index + 1:02d}@example.com",
                    "status": status,
                    "ai_category": category,
                    "ai_priority": priority,
                    "ai_sentiment": sentiment,
                    "ai_confidence": confidence,
                    "ai_explanation": ai_explanation,
                    "category": category,
                    "priority": priority,
                    "sentiment": sentiment,
                    "assigned_queue": assigned_queue,
                    "assign_to_agent": ticket_index % 3 != 0,
                    "created_by_admin": ticket_index % 5 != 4,
                    "override_spec": MANUAL_OVERRIDE_SPECS.get(ticket_index),
                    "override_by_admin": ticket_index % 2 == 0,
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


async def seed_tickets(db, user_ids: dict[str, str], tickets: list[dict]) -> tuple[int, int, int]:
    admin_id = user_ids["ADMIN"]
    agent_id = user_ids["AGENT"]
    created_count = 0
    skipped_count = 0
    override_count = 0
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
            "sentiment": ticket["ai_sentiment"],
            "assigned_queue": ticket["assigned_queue"],
            "ai_category": ticket["ai_category"],
            "ai_priority": ticket["ai_priority"],
            "ai_sentiment": ticket["ai_sentiment"],
            "ai_confidence": ticket["ai_confidence"],
            "ai_explanation": ticket["ai_explanation"],
            "assigned_agent_id": assigned_agent_id,
            "created_by": created_by,
            "created_at": created_at,
            "updated_at": updated_at,
        }

        override_spec = ticket.get("override_spec")
        if override_spec:
            overrider_id = admin_id if ticket["override_by_admin"] else agent_id
            override_fields = apply_manual_override(
                ticket["ai_category"],
                ticket["ai_priority"],
                override_spec,
                overridden_by=overrider_id,
                overridden_at=updated_at + timedelta(hours=1),
            )
            if override_fields:
                ticket_doc.update(override_fields)
                override_count += 1

        await db.tickets.insert_one(ticket_doc)
        created_count += 1

    return created_count, skipped_count, override_count


def print_summary(
    created_count: int,
    skipped_count: int,
    override_count: int,
    total_defined: int,
    reset_count: int,
) -> None:
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
    print(f"Tickets with manual overrides: {override_count}")
    print(f"Tickets skipped (already existed): {skipped_count}")
    print(f"Total seed tickets defined: {total_defined}")
    print()
    print("Re-running is safe: existing SEED tickets are skipped.")
    print("Use --reset-seed to delete and recreate seed tickets.")
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
        created_count, skipped_count, override_count = await seed_tickets(db, user_ids, tickets)
        print_summary(created_count, skipped_count, override_count, len(tickets), reset_count)
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
