# TriageIQ Architecture

## System overview

TriageIQ is a three-tier web application:

```text
┌─────────────┐     HTTPS/JSON      ┌─────────────┐     Motor (async)    ┌─────────────┐
│   React     │ ◄─────────────────► │   FastAPI   │ ◄────────────────► │   MongoDB   │
│   (Vite)    │   JWT Bearer auth   │   Backend   │                    │   7.0       │
└─────────────┘                     └─────────────┘                    └─────────────┘
```

- **Frontend** — SPA served by Vite; calls REST API with Axios; stores JWT in `localStorage`
- **Backend** — FastAPI routers, Pydantic schemas, service layer for classification/routing/mapping
- **Database** — MongoDB collections: `users`, `tickets`

## Frontend / backend / database flow

### Ticket creation

1. Agent submits title, description, and customer email from the Create Ticket page
2. Frontend `POST /tickets` with JWT
3. Backend runs `classify_ticket()` → category, priority, sentiment, confidence, explanation
4. Backend runs `resolve_assigned_queue()` → assigned queue
5. AI fields stored separately; effective `category`/`priority` set from classification
6. Document inserted into MongoDB `tickets` collection
7. `TicketResponse` returned to frontend with AI and effective values

### Ticket read / update

1. Frontend `GET /tickets` or `GET /tickets/{id}` with JWT
2. Backend applies **list filter** by role (admin: all; agent: `assigned_agent_id == user.id`)
3. `ticket_doc_to_response()` maps MongoDB document to API schema, computing effective values and `has_manual_override`
4. Agent status updates via `PUT /tickets/{id}` with `{ "status": "..." }` only

### Analytics

1. Admin opens Analytics page
2. Frontend `GET /analytics/summary` (admin-only)
3. Backend aggregates ticket counts and runs `compute_ai_accuracy_metrics()` over all tickets
4. JSON summary drives metric cards and Recharts bar charts

## Authentication and RBAC

### Authentication

- **Register:** `POST /auth/register` — creates user with bcrypt-hashed password (API/Postman/admin workflow; no public UI)
- **Login:** `POST /auth/login` — OAuth2 password form returns JWT access token
- **Current user:** `GET /auth/me` — validates token, rejects inactive users
- **Change password:** `POST /auth/change-password` — authenticated

JWT payload includes `sub` (user id), `email`, `role`, and `exp`. All protected routes use `get_current_user` dependency.

### Roles

| Role | Capabilities |
|------|----------------|
| **ADMIN** | Full ticket access; delete tickets; analytics; user CRUD (create/deactivate); manual override on any ticket |
| **AGENT** | Create tickets (auto-assigned); list/view/update status on **assigned** tickets only; manual override on accessible tickets |

### Enforcement layers

| Layer | Mechanism |
|-------|-----------|
| API | FastAPI dependencies: `require_admin`, `require_agent_or_admin`, `ensure_ticket_access` |
| Frontend | Nav links and pages gated by `localStorage.role` (API remains source of truth) |

## Ticket data model

MongoDB `tickets` documents include:

| Field group | Fields |
|-------------|--------|
| Core | `title`, `description`, `customer_email`, `status`, `sentiment`, `assigned_queue`, `assigned_agent_id`, `created_by`, `created_at`, `updated_at` |
| Effective classification | `category`, `priority` — what the UI and routing use today |
| Original AI | `ai_category`, `ai_priority`, `ai_sentiment`, `ai_confidence`, `ai_explanation` — never overwritten by override |
| Manual override | `category_override`, `priority_override`, `override_reason`, `overridden_by`, `overridden_at` |

### Effective value rules

Implemented in `ticket_mapping.py`:

- **Effective category** = `category_override` if present and ≠ `ai_category`, else `ai_category`
- **Effective priority** = `priority_override` if present and ≠ `ai_priority`, else `ai_priority`
- **Real override** = override field differs from corresponding AI field (used for analytics)

### Status and enums

- **Status:** OPEN, IN_PROGRESS, RESOLVED, CLOSED
- **Priority:** LOW, MEDIUM, HIGH, URGENT
- **Sentiment:** POSITIVE, NEUTRAL, NEGATIVE
- **Categories:** Billing, Technical, Account, Feature Request, Complaint, General

## AI classification design

**Module:** `app/services/classifier.py`

```text
title + description
        │
        ▼
  keyword scan (first matching category rule)
        │
        ├── priority keywords (urgent / high / low)
        ├── sentiment keywords (negative / positive)
        ├── confidence score (match strength)
        └── explanation string
        │
        ▼
  resolve_assigned_queue(category, priority, sentiment)
```

Category rules are ordered; first keyword hit wins. Config files `classification_keywords.json` and `routing_rules.json` exist for future externalization but the live logic is in Python services.

## Smart routing design

**Module:** `app/services/routing.py`

Routing runs **after** classification:

| Condition | Queue |
|-----------|-------|
| Billing + URGENT priority | Escalations |
| Complaint category | Escalations |
| General + NEGATIVE sentiment | Customer Success |
| Default by category | Billing Support, Technical Support, Account Support, Product Team, etc. |
| Unknown category | General Support |

## Manual override design

**Endpoints:**

- `PATCH /tickets/{id}/override` — agent or admin; requires accessible ticket
- `DELETE /tickets/{id}/override` — reset to AI classification

**Behavior:**

1. Request must include both `category` and `priority`
2. Rejected with `400` if selected values match AI (no-op override)
3. Only differing fields stored in `category_override` / `priority_override`
4. AI fields remain unchanged
5. Response enriches `overridden_by_name` and `overridden_by_email` from `users` collection
6. `has_manual_override` flag for UI

## Analytics design

**Endpoint:** `GET /analytics/summary` (admin only)

**Ticket metrics:** totals by status, priority, category, sentiment; resolution rate

**AI metrics** (`compute_ai_accuracy_metrics`):

| Metric | Definition |
|--------|------------|
| `total_classified_tickets` | Tickets with both `ai_category` and `ai_priority` |
| `overridden_ticket_count` | Real overrides only |
| `accepted_ai_count` | Classified − overridden |
| `override_rate` | overridden / total × 100 |
| `ai_accuracy` | accepted / total × 100 |
| `ai_classification_summary` | Chart data: Accepted vs Manually Overridden |

## Deployment architecture

### Docker Compose (development)

```text
┌──────────────── docker-compose network ────────────────┐
│  mongo:27017 ◄── backend:8000 ◄── browser ──► frontend:5173 │
└────────────────────────────────────────────────────────┘
         ▲
    host ports 27017, 8000, 5173
```

- Backend env: `MONGODB_URI=mongodb://mongo:27017/triageiq`
- Frontend env: `VITE_API_BASE_URL=http://localhost:8000` (browser on host)

### Kubernetes (optional)

```text
┌────────────── cluster ──────────────┐
│  triageiq-mongodb:27017             │
│         ▲                           │
│  triageiq-backend:8000              │
│         ▲                           │
│  triageiq-frontend:5173             │
│  (ClusterIP; port-forward/Ingress)  │
└─────────────────────────────────────┘
```

- **ConfigMap** — `MONGODB_URI`, CORS, JWT algorithm, frontend API URL
- **Secret** — `JWT_SECRET` (created at deploy time, not in git)
- **PVC** — MongoDB data persistence (1Gi in example manifest)

See [`k8s/README.md`](../k8s/README.md) for apply order and teardown.

### CI/CD

GitHub Actions runs parallel backend and frontend jobs on every push/PR. Backend tests use an ephemeral MongoDB 7.0 service container and isolated database `triageiq_test`.

## Backend module layout

```text
backend/app/
├── core/config.py          # Settings from environment
├── db/mongodb.py           # Motor connection
├── routers/
│   ├── auth.py
│   ├── tickets.py
│   ├── analytics.py
│   └── users.py
├── schemas/                # Pydantic models
└── services/
    ├── classifier.py
    ├── routing.py
    ├── ticket_mapping.py
    └── security.py
```

## Frontend module layout

```text
frontend/src/
├── api/api.js              # Axios client + endpoint helpers
├── components/AppLayout.jsx
├── pages/                  # Login, Dashboard, Tickets, TicketDetail, etc.
└── utils/                  # Badge components and helpers
```
