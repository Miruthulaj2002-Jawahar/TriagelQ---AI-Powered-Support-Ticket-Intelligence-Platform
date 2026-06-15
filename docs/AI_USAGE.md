# AI Tool Usage — TriageIQ

This document describes how AI-assisted tools were used during development and how outputs were validated before inclusion in the codebase.

## Tools used

| Tool | Primary uses |
|------|----------------|
| **Cursor** | In-IDE code generation, refactoring, test writing, Docker/K8s/CI configs, documentation drafts, debugging |
| **ChatGPT** | Architecture brainstorming, API design questions, wording for docs, reviewing error messages |

## What each tool was used for

### Cursor

- Scaffolding FastAPI routers, Pydantic schemas, and MongoDB access patterns
- Implementing manual override logic, analytics metrics, and ticket mapping
- Writing and expanding pytest suites (classifier, routing, RBAC, integration)
- Creating `docker-compose.yml`, Kubernetes manifests, and GitHub Actions workflow
- Frontend pages, API client, badge components, and ESLint fixes
- Seed data script with idempotent ticket generation

### ChatGPT

- Discussing trade-offs: FastAPI vs Flask, local classifier vs external LLM
- Drafting README section structure and architecture diagram descriptions
- Clarifying JWT + OAuth2 password flow patterns for FastAPI
- Reviewing pytest fixture strategies for isolated MongoDB test databases

## Effective prompts (examples)

### 1. Manual override and analytics

> Update the TriageIQ manual override and AI accuracy implementation. Store original AI values separately from override values. Effective category should be override only when it differs from AI. Analytics should report override_rate and ai_accuracy. Add tests for override logic.

**Why it worked:** Clear acceptance criteria, field names, and test expectations produced a focused backend + frontend change set.

### 2. Backend tests and CI safety

> Add backend tests and coverage for TriageIQ. Use a separate test database like triageiq_test. Include classifier unit tests, routing tests, and at least five API integration tests. Add pytest --cov=app with MongoDB service container in GitHub Actions.

**Why it worked:** Specified tools, isolation strategy, and CI constraints — matched the final `conftest.py` and workflow design.

### 3. Kubernetes manifests without breaking Compose

> Add Kubernetes manifests for backend, frontend, and MongoDB. Backend should use the MongoDB service name. No real secrets in YAML. Do not break Docker Compose or local development.

**Why it worked:** Explicit non-goals prevented overwriting existing dev workflows.

## Example: incorrect or incomplete AI suggestion

**Issue:** An early suggestion put `renderDetailValue` and badge helper functions in the same file as React badge components (`badges.jsx`). ESLint reported:

```text
Fast refresh only works when a file only exports components.
```

**Why it was wrong:** Vite React Fast Refresh requires component-only exports in `.jsx` files that participate in hot reload. Mixing utility functions with components breaks that rule.

**How it was caught:** Running `npm run lint` locally and in GitHub Actions CI.

**Fix applied:**

- Moved `formatBadgeLabel` to `frontend/src/utils/badgeHelpers.js`
- Moved `renderDetailValue` to `frontend/src/utils/renderDetailValue.jsx`
- Left `badges.jsx` exporting only `StatusBadge`, `PriorityBadge`, and `SentimentBadge`
- Updated imports in `TicketDetail.jsx`, `CreateTicket.jsx`, and related pages

## Review and testing statement

All AI-generated code was **reviewed manually**, run against **Ruff** and **ESLint**, and validated with:

- **60 backend pytest cases** (~92% app coverage)
- **`npm run build`** for the frontend
- **Manual smoke tests** via Docker Compose (login, tickets, override, analytics, seed data)

No code was merged solely on AI output without local verification.

## Guidelines followed

1. Prefer small, reviewable diffs over large generated blocks
2. Never commit secrets suggested by AI — use `.env.example` placeholders
3. Cross-check generated API paths against actual routers and OpenAPI docs
4. Run tests after every significant AI-assisted change
