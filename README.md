# TriageIQ

AI-assisted support ticket triage with manual override tracking and admin analytics.

## Quick start (Docker)

```bash
docker compose up --build -d
docker compose exec backend python scripts/seed_data.py
```

- Frontend: http://localhost:5173  
- Backend API: http://localhost:8000  
- API docs: http://localhost:8000/docs  

## Seed data

The seed script inserts **55 realistic support tickets** (prefix `SEED - `) plus demo users. It is **idempotent**: re-running skips tickets that already exist.

### Run locally

From the `backend` directory (requires MongoDB and `.env` with `JWT_SECRET`):

```bash
cd backend
python scripts/seed_data.py
```

Recreate seed tickets from scratch:

```bash
python scripts/seed_data.py --reset-seed
```

### Run in Docker

```bash
docker compose exec backend python scripts/seed_data.py
docker compose exec backend python scripts/seed_data.py --reset-seed
```

### Demo accounts

| Role  | Email               | Password   |
|-------|---------------------|------------|
| Admin | admin@triageiq.com  | Admin@123  |
| Agent | agent@triageiq.com  | Agent@123  |

Seed tickets vary across categories, priorities, sentiments, statuses, and support queues. Several tickets include **manual overrides** so AI accuracy and override-rate analytics can be tested in the admin dashboard.

## Backend tests

```bash
cd backend
python -m pytest tests -v
```
