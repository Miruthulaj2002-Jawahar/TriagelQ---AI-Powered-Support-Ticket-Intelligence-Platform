# TriageIQ Development Log

Day-by-day progress for the five-day build. Each entry reflects work completed in the repository.

---

## Day 1 — Setup, architecture, authentication

**Goals:** Project scaffold, database connection, JWT auth, user model

**Completed:**

- Initialized FastAPI backend with `app/main.py`, CORS, health endpoints (`/`, `/health`)
- MongoDB integration via Motor (`app/db/mongodb.py`) and pydantic-settings config
- User schema and auth router: register, login (OAuth2 form), `/auth/me`, change password
- JWT creation/validation and bcrypt password hashing (`app/services/security.py`)
- Role enum: `ADMIN`, `AGENT`
- Pydantic settings for `MONGODB_URI`, `MONGODB_DB`, `JWT_SECRET`, CORS
- Initial project layout: `routers/`, `schemas/`, `services/`
- Postman collection started under `docs/postman/`

**Outcome:** API accepts registration and login; protected routes validate JWT and role.

---

## Day 2 — Ticket CRUD, AI classification, routing

**Goals:** Ticket lifecycle, keyword classifier, queue routing

**Completed:**

- Ticket schemas: create, update, response with status/priority/sentiment enums
- Ticket router: create, list, get by id, update, delete (admin)
- Keyword-based classifier (`app/services/classifier.py`) — category, priority, sentiment, confidence, explanation
- Smart routing service (`app/services/routing.py`) — Escalations, Product Team, Customer Success, etc.
- Auto-classification on ticket create; AI fields stored on document
- Agent assignment on create when creator is an agent
- RBAC on tickets: agents limited to assigned tickets; agents can only update `status`
- Ticket mapping helpers for API responses

**Outcome:** Creating a ticket runs classification and routing; CRUD and access rules enforced.

---

## Day 3 — Frontend login, tickets, protected routes

**Goals:** React SPA wired to API with role-aware navigation

**Completed:**

- Vite + React app with React Router
- Login page — JWT stored in `localStorage`, role from `/auth/me`
- Axios API client with auth interceptor (`frontend/src/api/api.js`)
- App layout with role-based nav (admin vs agent)
- Pages: Dashboard, Tickets (list + filters), Ticket Detail, Create Ticket, Profile
- Ticket list badges for status, priority, sentiment
- Status update form on ticket detail
- Global CSS design system for consistent UI

**Outcome:** End-to-end flow from login to ticket list, detail, and create (agent).

---

## Day 4 — Analytics, seed data, tests

**Goals:** Admin analytics, manual override, seed script, automated tests

**Completed:**

- Manual override: `PATCH /tickets/{id}/override`, `DELETE /tickets/{id}/override` (reset to AI)
- Separate AI vs override fields; effective category/priority logic; `has_manual_override`
- Analytics summary endpoint with AI accuracy, override rate, breakdown charts data
- Analytics and Dashboard frontend pages with Recharts
- Admin user management: create user, deactivate user (soft delete)
- Seed script (`backend/scripts/seed_data.py`) — 55 tickets, demo users, 8 override samples
- pytest suite: auth, tickets, classifier, routing, RBAC, overrides, users, integration API
- Test database isolation (`triageiq_test`) and safety guard in `conftest.py`
- ~60 tests, ~92% backend coverage

**Outcome:** Admins can measure AI performance; demo data supports realistic analytics demos.

---

## Day 5 — Docker, Kubernetes, CI/CD, documentation

**Goals:** Containerization, deployment manifests, pipeline, final docs

**Completed:**

- `docker-compose.yml` — MongoDB 7.0, backend, frontend with health checks
- Backend and frontend Dockerfiles
- Kubernetes manifests in `k8s/` — ConfigMap, Deployments, Services, Secret example, PVC
- GitHub Actions CI (`.github/workflows/ci.yml`) — Ruff, pytest+coverage, ESLint, build
- Frontend ESLint Fast Refresh fix (split badge helpers from components)
- Final documentation: README, ARCHITECTURE, DEVLOG, AI_USAGE, `.env.example`

**Outcome:** Project is runnable via Compose, deployable to K8s with documented steps, and validated in CI on every push/PR.

---

## Current status

| Area | Status |
|------|--------|
| Auth & RBAC | Complete |
| Ticket CRUD + classification | Complete |
| Manual override + analytics | Complete |
| Admin user management | Complete |
| Seed data | Complete |
| Backend tests + CI | Complete |
| Docker Compose | Complete |
| Kubernetes (example) | Complete |
| Documentation | Complete |
