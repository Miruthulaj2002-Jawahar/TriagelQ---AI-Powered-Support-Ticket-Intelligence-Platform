"""
Seed demo users and tickets for local testing.

Run from the backend directory:
    python scripts/seed_demo_data.py
"""

from __future__ import annotations

import asyncio
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_ROOT))

from motor.motor_asyncio import AsyncIOMotorClient

from app.core.config import settings
from app.services.security import hash_password

DEMO_USERS = [
    {
        "full_name": "Admin User",
        "email": "admin@triageiq.com",
        "password": "FinalAdmin",
        "role": "ADMIN",
    },
    {
        "full_name": "Agent User",
        "email": "agent@triageiq.com",
        "password": "FinalAgent@123",
        "role": "AGENT",
    },
]

DEMO_TICKETS = [
    {
        "title": "DEMO - Double charge on subscription",
        "description": "Customer was charged twice for the monthly subscription and needs an urgent refund.",
        "customer_email": "customer1@example.com",
        "status": "OPEN",
        "category": "Billing",
        "priority": "URGENT",
        "sentiment": "NEGATIVE",
        "assigned_queue": "Billing Support",
        "confidence": 0.94,
        "explanation": "Billing keywords and urgent refund language detected.",
        "assign_to_agent": True,
        "created_by_admin": True,
    },
    {
        "title": "DEMO - Refund request for invoice #8821",
        "description": "Customer requested a refund after being charged for an invoice they already paid.",
        "customer_email": "customer2@example.com",
        "status": "IN_PROGRESS",
        "category": "Billing",
        "priority": "HIGH",
        "sentiment": "NEGATIVE",
        "assigned_queue": "Billing Support",
        "confidence": 0.91,
        "explanation": "Invoice and refund terms indicate a billing issue.",
        "assign_to_agent": True,
        "created_by_admin": True,
    },
    {
        "title": "DEMO - Server timeout during checkout",
        "description": "Checkout fails with a timeout error and the customer cannot complete payment.",
        "customer_email": "customer3@example.com",
        "status": "OPEN",
        "category": "Technical Support",
        "priority": "HIGH",
        "sentiment": "NEGATIVE",
        "assigned_queue": "Technical Support",
        "confidence": 0.89,
        "explanation": "Timeout and error language suggest a technical issue.",
        "assign_to_agent": True,
        "created_by_admin": True,
    },
    {
        "title": "DEMO - App crash on dashboard load",
        "description": "The application crashes immediately when loading the dashboard after login.",
        "customer_email": "customer4@example.com",
        "status": "IN_PROGRESS",
        "category": "Technical Support",
        "priority": "URGENT",
        "sentiment": "NEGATIVE",
        "assigned_queue": "Technical Support",
        "confidence": 0.96,
        "explanation": "Crash and login failure keywords indicate urgent technical support.",
        "assign_to_agent": True,
        "created_by_admin": True,
    },
    {
        "title": "DEMO - Cannot reset password",
        "description": "Customer cannot reset their password and is blocked from account access.",
        "customer_email": "customer5@example.com",
        "status": "OPEN",
        "category": "Account Access",
        "priority": "HIGH",
        "sentiment": "NEUTRAL",
        "assigned_queue": "Account Support",
        "confidence": 0.88,
        "explanation": "Password reset and account access terms detected.",
        "assign_to_agent": True,
        "created_by_admin": True,
    },
    {
        "title": "DEMO - Account locked after failed login",
        "description": "Customer account was locked after multiple failed login attempts.",
        "customer_email": "customer6@example.com",
        "status": "RESOLVED",
        "category": "Account Access",
        "priority": "MEDIUM",
        "sentiment": "NEGATIVE",
        "assigned_queue": "Account Support",
        "confidence": 0.87,
        "explanation": "Locked account and login failure indicate account support.",
        "assign_to_agent": True,
        "created_by_admin": True,
    },
    {
        "title": "DEMO - Feature request for export report",
        "description": "Customer suggested adding an export report feature to improve workflow.",
        "customer_email": "customer7@example.com",
        "status": "OPEN",
        "category": "Product Issue",
        "priority": "LOW",
        "sentiment": "POSITIVE",
        "assigned_queue": "Product Team",
        "confidence": 0.82,
        "explanation": "Feature request language detected with positive feedback tone.",
        "assign_to_agent": False,
        "created_by_admin": True,
    },
    {
        "title": "DEMO - UI bug on mobile view",
        "description": "Navigation menu is broken on mobile and the layout is not working correctly.",
        "customer_email": "customer8@example.com",
        "status": "IN_PROGRESS",
        "category": "Product Issue",
        "priority": "MEDIUM",
        "sentiment": "NEUTRAL",
        "assigned_queue": "Product Team",
        "confidence": 0.85,
        "explanation": "Bug and broken UI terms suggest a product issue.",
        "assign_to_agent": True,
        "created_by_admin": True,
    },
    {
        "title": "DEMO - Question about pricing tiers",
        "description": "Customer has a minor question about pricing tiers and plan differences.",
        "customer_email": "customer9@example.com",
        "status": "OPEN",
        "category": "General Inquiry",
        "priority": "LOW",
        "sentiment": "NEUTRAL",
        "assigned_queue": "General Support",
        "confidence": 0.79,
        "explanation": "General question with low urgency detected.",
        "assign_to_agent": False,
        "created_by_admin": True,
    },
    {
        "title": "DEMO - Thanks for helpful support call",
        "description": "Customer said thanks for the helpful support call and great service experience.",
        "customer_email": "customer10@example.com",
        "status": "CLOSED",
        "category": "General Inquiry",
        "priority": "LOW",
        "sentiment": "POSITIVE",
        "assigned_queue": "General Support",
        "confidence": 0.84,
        "explanation": "Positive feedback and thanks detected.",
        "assign_to_agent": True,
        "created_by_admin": True,
    },
    {
        "title": "DEMO - Payment method update failed",
        "description": "Customer payment method update failed and billing profile could not be saved.",
        "customer_email": "customer11@example.com",
        "status": "RESOLVED",
        "category": "Billing",
        "priority": "MEDIUM",
        "sentiment": "NEGATIVE",
        "assigned_queue": "Billing Support",
        "confidence": 0.9,
        "explanation": "Payment and billing failure terms detected.",
        "assign_to_agent": True,
        "created_by_admin": True,
    },
    {
        "title": "DEMO - Slow API response times",
        "description": "Customer reports slow server response and degraded performance during peak hours.",
        "customer_email": "customer12@example.com",
        "status": "CLOSED",
        "category": "Technical Support",
        "priority": "HIGH",
        "sentiment": "NEUTRAL",
        "assigned_queue": "Technical Support",
        "confidence": 0.86,
        "explanation": "Slow performance and server terms indicate technical support.",
        "assign_to_agent": False,
        "created_by_admin": True,
    },
    {
        "title": "DEMO - Need access to admin panel",
        "description": "Customer needs access restored to the admin panel after a profile update.",
        "customer_email": "customer13@example.com",
        "status": "CLOSED",
        "category": "Account Access",
        "priority": "MEDIUM",
        "sentiment": "NEUTRAL",
        "assigned_queue": "Account Support",
        "confidence": 0.83,
        "explanation": "Account access request detected.",
        "assign_to_agent": True,
        "created_by_admin": True,
    },
    {
        "title": "DEMO - Suggestion for dark mode toggle",
        "description": "Customer submitted a suggestion to add a dark mode toggle and improve the UI.",
        "customer_email": "customer14@example.com",
        "status": "RESOLVED",
        "category": "Product Issue",
        "priority": "LOW",
        "sentiment": "POSITIVE",
        "assigned_queue": "Product Team",
        "confidence": 0.81,
        "explanation": "Enhancement suggestion with positive feedback detected.",
        "assign_to_agent": False,
        "created_by_admin": True,
    },
    {
        "title": "DEMO - Angry complaint about outage",
        "description": "Customer is angry and frustrated because production service is down and they cannot access the platform.",
        "customer_email": "customer15@example.com",
        "status": "OPEN",
        "category": "Technical Support",
        "priority": "URGENT",
        "sentiment": "NEGATIVE",
        "assigned_queue": "Escalation Team",
        "confidence": 0.97,
        "explanation": "Outage, angry complaint, and blocked access indicate urgent escalation.",
        "assign_to_agent": True,
        "created_by_admin": True,
    },
]


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


async def seed_demo_tickets(db, user_ids: dict[str, str]) -> tuple[int, int]:
    admin_id = user_ids["ADMIN"]
    agent_id = user_ids["AGENT"]
    created_count = 0
    skipped_count = 0
    base_time = datetime.now(UTC) - timedelta(days=14)

    for index, ticket in enumerate(DEMO_TICKETS):
        existing = await db.tickets.find_one({"title": ticket["title"]})
        if existing:
            skipped_count += 1
            print(f"Ticket already exists: {ticket['title']}")
            continue

        created_at = base_time + timedelta(hours=index * 8)
        updated_at = created_at + timedelta(hours=2)

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
        print(f"Created ticket: {ticket['title']}")

    return created_count, skipped_count


async def main() -> None:
    client = AsyncIOMotorClient(settings.mongodb_uri)
    db = client[settings.mongodb_db]

    try:
        await db.users.create_index("email", unique=True)

        print("Seeding demo users...")
        user_ids = await ensure_demo_users(db)

        if "ADMIN" not in user_ids or "AGENT" not in user_ids:
            raise RuntimeError("Failed to resolve demo user IDs.")

        print("Seeding demo tickets...")
        created_count, skipped_count = await seed_demo_tickets(db, user_ids)

        assigned_count = sum(1 for ticket in DEMO_TICKETS if ticket["assign_to_agent"])

        print()
        print("Demo data seeded successfully.")
        print()
        print("Demo login credentials:")
        print("  Admin -> admin@triageiq.com / FinalAdmin")
        print("  Agent -> agent@triageiq.com / FinalAgent@123")
        print()
        print(f"Tickets created: {created_count}")
        print(f"Tickets skipped (already existed): {skipped_count}")
        print(f"Total demo tickets defined: {len(DEMO_TICKETS)}")
        print(f"Tickets assigned to agent: {assigned_count}")
        print(f"Tickets visible to agent via assigned_agent_id: {assigned_count}")
    finally:
        client.close()


if __name__ == "__main__":
    asyncio.run(main())
