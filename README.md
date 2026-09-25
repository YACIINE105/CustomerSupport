# Customer Support Platform

A FastAPI backend for managing customer-support interactions. The project uses a
modular monolith with PostgreSQL, async SQLAlchemy, Pydantic, and Alembic.

## Current functionality

- Customer creation, listing, retrieval, partial updates, and deletion.
- Conversation creation for an existing customer and retrieval by ID.
- CHAT, VOICE, and PHONE channels; new conversations start OPEN.
- Customer and authenticated human-agent text messages with JSON metadata and a
  paginated conversation timeline.
- Admin-provisioned users, JWT login, roles, and immediate inactive-account checks.
- Human-agent profiles and AVAILABLE/BUSY/OFFLINE availability.
- Input validation, missing-resource responses, and database constraints.
- Versioned database migrations and automated service/API/persistence tests.

All business APIs require an active staff account. This is a single-business,
shared-queue backend; assignment-based access is a later stage. Public deployment
hardening (TLS, login rate limiting, password recovery, and operational controls)
is not complete. No frontend, LLM, RAG, or telephony integration is included.

## Requirements

- Python 3.12 or later and `uv`.
- Docker with Docker Compose. When using WSL, enable your distro's Docker Desktop
  integration and run the commands below from that distro.
- Available local ports: 8000 for the API and 5433 for the project database.

Run all commands from the repository root.

## Quick start: local Python, containerized database

```bash
uv sync --locked

# Create local configuration only if it does not already exist.
[ -f .env ] || cp .env.example .env

# Generate a secret and put its output in .env as JWT_SECRET_KEY (do this once).
uv run python -c "import secrets; print(secrets.token_urlsafe(48))"

docker compose -f docker/docker-compose.yml up -d --wait db
uv run alembic -c alembic/alembic.ini upgrade head
uv run python -m src.cli.bootstrap_admin
uv run uvicorn src.main:app --reload
```

The bootstrap command prompts for an email and a password (12–128 characters).
It refuses to create another initial administrator if one already exists. No
password or administrator account is shipped with the project.

Open:

- [Swagger API explorer](http://localhost:8000/docs)
- [OpenAPI schema](http://localhost:8000/openapi.json)
- [Health endpoint](http://localhost:8000/health)

`/health` reports application liveness; it does not query the database.

## Configuration

Settings are read from environment variables, then `.env`, then code defaults.
The real `.env` is ignored by Git; `.env.example` is tracked.

| Variable | Default | Purpose |
| --- | --- | --- |
| `APP_NAME` | `Customer Support Platform` | API title and health response |
| `APP_VERSION` | `0.1.0` | API version metadata |
| `ENVIRONMENT` | `development` | Environment label |
| `DEBUG` | `false` | FastAPI debug mode and SQL statement logging |
| `JWT_SECRET_KEY` | No default key | Random signing secret, at least 32 bytes |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | `30` | Access-token lifetime (1–1440 minutes) |
| `JWT_ISSUER` | `customer-support` | Required token issuer |
| `JWT_AUDIENCE` | `customer-support-api` | Required token audience |
| `DATABASE_URL` | `postgresql+asyncpg://postgres:postgres@localhost:5433/customer_support` | Local database connection |

Authentication fails with 503 when no signing key is configured. Keep the secret
out of Git and stable across restarts; changing it invalidates existing tokens.
Compose reads the root `.env` for the API container.

The supplied database credentials are development defaults. If your existing `.env` has a
different database URL, update it to match the database you intend to use.

Compose uses project name `customer-support` and a dedicated named volume. Its
database image is `pgvector/pgvector:0.8.6-pg18-trixie`. The host port is 5433 so an
existing PostgreSQL installation on 5432 can remain running. Inside the Compose
network, the API connects to `db:5432`.

The PostgreSQL 18 volume mounts at `/var/lib/postgresql`. The image includes
pgvector, but this application has not enabled the extension or created vector
tables; those belong to a later knowledge-base feature.

## Run the entire stack in Docker

```bash
docker compose -f docker/docker-compose.yml up --build -d
docker compose -f docker/docker-compose.yml ps -a
docker compose -f docker/docker-compose.yml logs api migrate
```

Startup order is database health check → migration job → API. The API becomes
available on port 8000 after migrations succeed. Do not run the local Uvicorn
server and containerized API on that port simultaneously.

For a fresh container-only setup, bootstrap after the API starts:

```bash
docker compose -f docker/docker-compose.yml exec api uv run --no-sync python -m src.cli.bootstrap_admin
```

Stop the stack while retaining database data:

```bash
docker compose -f docker/docker-compose.yml down
```

Do not add `--volumes` unless you intend to delete the stored database data.
The database container has been verified; the full API image build/start has not
yet been verified in this milestone.

## Authentication and permissions

Login accepts JSON (`email`, `password`), not an OAuth form. Use Swagger to call
`POST /api/v1/auth/login`, then paste the returned `access_token` into **Authorize**.
For terminal examples below, save that token in the shell variable `TOKEN`.

```bash
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H 'Content-Type: application/json' \
  -d '{"email":"admin@example.com","password":"YOUR_BOOTSTRAP_PASSWORD"}'
# Copy access_token from the response:
export TOKEN='YOUR_ACCESS_TOKEN'
curl -H "Authorization: Bearer $TOKEN" http://localhost:8000/api/v1/auth/me
```

Avoid putting real passwords into shared shell history; Swagger or a local client
can be used instead. Tokens expire after 30 minutes by default; log in again to
obtain another token. No refresh-token or logout/revocation-list flow is implemented.
Every protected request reloads the User from the database. Deactivation and role
changes therefore affect existing tokens immediately. Reactivation permits any
otherwise-valid unexpired token again.

Passwords use Argon2; JWT verification fixes the algorithm to HS256 and validates
signature, expiry, issuer, audience, subject, and access-token type. This follows
[FastAPI's password-hashing/JWT guidance](https://fastapi.tiangolo.com/tutorial/security/oauth2-jwt/).
Password fields/hashes are excluded from responses and input values are omitted
from validation errors. Account/profile mutations emit actor/target IDs to
operational logs; these logs are not a durable audit-record subsystem.

| Operation | ADMIN | SUPPORT_HEAD | AGENT |
| --- | --- | --- | --- |
| Create users (`auth/register`), change roles/active status | Yes | No | No |
| List users | Yes | Yes | No |
| Create agent profiles | Yes | Yes | No |
| Read profiles | Yes | Yes | Yes |
| Change availability | Any active agent | Any active agent | Own profile |
| Read/create/update customers; create/read conversations and history | Yes | Yes | Yes |
| Delete customers | Yes | Yes | No |
| Record a customer message on that customer's conversation | Yes | Yes | Yes |
| Reply with sender type AGENT | No | No | Own profile only |

There is no public signup or customer-login flow. `auth/register` is an
admin-only account provisioning operation. Active staff share the queue in this
stage; role AGENT alone does not give an account an agent identity until its
profile is created. CUSTOMER messages represent staff recording customer input;
they are not authenticated customer submissions.

## Provision a human agent

With the admin token, create a user (use a real password of 12–128 characters):

```bash
curl -H "Authorization: Bearer $TOKEN" -X POST http://localhost:8000/api/v1/auth/register \
  -H 'Content-Type: application/json' \
  -d '{"email":"mona@example.com","password":"REPLACE_WITH_A_STRONG_PASSWORD","role":"AGENT"}'
```

Then use the returned user ID to create their profile:

```bash
curl -H "Authorization: Bearer $TOKEN" -X POST http://localhost:8000/api/v1/agents \
  -H 'Content-Type: application/json' \
  -d '{"user_id":2,"display_name":"Mona","department":"Support"}'
```

New profiles start OFFLINE. Each user can have at most one profile; only active
users with the AGENT role qualify. An account with a profile must retain its AGENT
role. Log in as that user, put their token in `TOKEN`, and use the returned agent ID:

```bash
curl -H "Authorization: Bearer $TOKEN" -X PATCH http://localhost:8000/api/v1/agents/1/status \
  -H 'Content-Type: application/json' -d '{"status":"AVAILABLE"}'
```

Availability is explicitly set; logging in/out does not change it. Deactivating a
user via admin-only `PATCH /api/v1/users/{id}` sets their profile OFFLINE in the
same transaction. Administrators cannot disable/demote their own account. Example
update bodies are `{"is_active":false}` or `{"role":"SUPPORT_HEAD"}`; email and
password updates are not part of this endpoint. User and agent lists support
`offset` and `limit` (1–100).

## Use the API

### 1. Create a customer

```bash
curl -H "Authorization: Bearer $TOKEN" -i -X POST http://localhost:8000/api/v1/customers \
  -H 'Content-Type: application/json' \
  -d '{"name":"Mona","email":"mona@example.com","phone":"+201234567890"}'
```

Expect HTTP 201 with a generated `id`, contact details, and timestamps. Use that
customer ID in subsequent requests; the examples below assume it is `1`.

### 2. Start a conversation

```bash
curl -H "Authorization: Bearer $TOKEN" -i -X POST http://localhost:8000/api/v1/conversations \
  -H 'Content-Type: application/json' \
  -d '{"customer_id":1,"channel":"CHAT"}'
```

Expect HTTP 201 with status `OPEN`, a generated conversation ID, timestamps, and
`ended_at: null`. Use the returned conversation ID to retrieve it:

```bash
curl -H "Authorization: Bearer $TOKEN" http://localhost:8000/api/v1/conversations/1
```

### 3. Send a message and read the timeline

Use the customer ID and conversation ID returned by the previous requests:

```bash
curl -H "Authorization: Bearer $TOKEN" -i -X POST http://localhost:8000/api/v1/conversations/1/messages \
  -H 'Content-Type: application/json' \
  -d '{"sender_id":1,"content":"Where is my order?","metadata":{"order_id":"A123"}}'
curl -H "Authorization: Bearer $TOKEN" 'http://localhost:8000/api/v1/conversations/1/messages?offset=0&limit=20'
```

Creation returns HTTP 201 with the stored message, its ID, and timestamp. Listing
returns HTTP 200 with an array (empty for an existing conversation with no messages).
Messages are ordered oldest first by `created_at`, then by `id` for equal timestamps.
Use `offset >= 0` and `limit` from 1 to 100; the default page size is 100.

For this stage, `sender_type` defaults to CUSTOMER and `message_type` to TEXT.
For CUSTOMER messages, `sender_id` must match the conversation's customer.
For human replies, pass `"sender_type":"AGENT"` and your own agent profile ID as
`sender_id`, using your agent account's token. AI/SYSTEM senders and non-TEXT
message types are rejected. Content is trimmed, must not be blank, and is limited
to 10,000 characters. `metadata` is an optional JSON object, defaulting to `{}`.
Unknown fields such as client-supplied timestamps are rejected.

The endpoint authenticates staff and checks AGENT attribution against the logged-in
user's profile. Trusted AI/system writers and rules for messaging closed
conversations belong to later stages. No audio upload or realtime delivery is
implemented. Offset pagination does not provide a frozen snapshot during
concurrent writes.

### 4. List or update customers

```bash
curl -H "Authorization: Bearer $TOKEN" 'http://localhost:8000/api/v1/customers?offset=0&limit=20'
curl -H "Authorization: Bearer $TOKEN" -X PATCH http://localhost:8000/api/v1/customers/1 \
  -H 'Content-Type: application/json' \
  -d '{"email":null}'
```

PATCH preserves omitted fields. Explicit null clears email or phone; name cannot
be null. Customer listing is ordered by ID and supports `offset >= 0` and a
`limit` between 1 and 100.

### Endpoint reference

| Method | Path | Success |
| --- | --- | --- |
| GET | `/health` | 200 (public) |
| POST | `/api/v1/auth/login` | 200 (public, credentials required) |
| POST | `/api/v1/auth/register` | 201 (ADMIN) |
| GET | `/api/v1/auth/me` | 200 |
| GET | `/api/v1/users` | 200 (ADMIN / SUPPORT_HEAD) |
| PATCH | `/api/v1/users/{user_id}` | 200 (ADMIN) |
| POST | `/api/v1/agents` | 201 (ADMIN / SUPPORT_HEAD) |
| GET | `/api/v1/agents` | 200 |
| GET | `/api/v1/agents/{agent_id}` | 200 |
| PATCH | `/api/v1/agents/{agent_id}/status` | 200 (manager or own profile) |
| POST | `/api/v1/customers` | 201 |
| GET | `/api/v1/customers` | 200 |
| GET | `/api/v1/customers/{customer_id}` | 200 |
| PATCH | `/api/v1/customers/{customer_id}` | 200 |
| DELETE | `/api/v1/customers/{customer_id}` | 204, empty body |
| POST | `/api/v1/conversations` | 201 |
| GET | `/api/v1/conversations/{conversation_id}` | 200 |
| POST | `/api/v1/conversations/{conversation_id}/messages` | 201 |
| GET | `/api/v1/conversations/{conversation_id}/messages` | 200 |

Conversation creation requires a positive customer ID and channel CHAT, VOICE, or
PHONE. Additional fields, including client-supplied status, are rejected.

Missing users/agents/customers/conversations return 404 with `detail` and `code` fields.
Missing/invalid credentials return 401, forbidden operations return 403, and
duplicate accounts/profiles or incompatible state changes return 409. Invalid input returns 422. Deleting a customer with conversation history is
blocked by the database; a friendly HTTP 409 mapping remains to be implemented.
There is no Conversation update, list, or delete endpoint yet.

## Architecture

```text
HTTP → Route → Controller → Service → Repository → PostgreSQL
```

| Directory/file | Responsibility |
| --- | --- |
| `src/main.py` | Application setup, exception handler, lifespan |
| `src/core/` | Settings, sessions, errors, password/JWT helpers, authentication dependencies |
| `src/cli/` | Initial administrator bootstrap |
| `src/domain/` | Shared domain enums |
| `src/models/` | SQLAlchemy persistence models |
| `src/schemas/` | Pydantic request/response validation |
| `src/repositories/` | Database reads and writes |
| `src/services/` | Business rules and workflows |
| `src/controllers/` | Thin adapters between routes and services |
| `src/routes/` | HTTP endpoints and dependency wiring |
| `src/utils/` | Logging setup |
| `alembic/` | Schema migrations |
| `tests/` | Service, API, and database-constraint tests |
| `docker/` | Dockerfile and Compose configuration |

Repositories flush changes; the request session owns commit/rollback. Function
scope ensures commit completes before a successful response is sent. Related
operations can share one transaction. The app does not create tables on startup.

## Database migrations

```bash
uv run alembic -c alembic/alembic.ini upgrade head
uv run alembic -c alembic/alembic.ini current
uv run alembic -c alembic/alembic.ini check
```

Current revisions: `0001` creates customers; `0002` creates conversations, their
foreign key/index, and channel/status CHECK constraints. Revision `0003` creates
messages with sender/type constraints and the composite timeline index. Revision
`0004` creates users (unique normalized email) and agents (unique user foreign key).

After changing models, ensure they are imported by `alembic/env.py`, then generate
and review a new migration:

```bash
uv run alembic -c alembic/alembic.ini revision --autogenerate -m "describe change"
uv run alembic -c alembic/alembic.ini upgrade head
```

Review constraints, defaults, and downgrade behavior before applying generated
SQL. Test destructive downgrades only on a disposable database.

## Testing and verified behavior

```bash
uv run python -m pytest -q
uv run python -m pytest tests/test_conversation_service.py -v
uv run python -m pytest tests/test_conversation_api.py -v
uv run python -m pytest tests/test_message_service.py tests/test_message_api.py -v
uv run python -m pytest tests/test_auth_service.py tests/test_auth_agents_api.py -v
```

Service tests mock repositories. API/persistence tests use a fresh SQLite database
per test with foreign-key enforcement and real application layers. PostgreSQL is
not needed for this suite; these tests do not validate Alembic migration execution.

Latest milestone verification:

- 95 tests passed, covering real login in existing API tests, invalid/expired JWTs,
  password hashing/redaction, role changes, deactivation, profile uniqueness,
  availability ownership, agent impersonation, and the previous support workflows.
- PostgreSQL 18 database container started successfully.
- Migrations applied through `0004`; Alembic reported no schema differences.
- An HTTP smoke check against PostgreSQL verified all channels, UTC timestamps,
  retrieval, invalid input, and missing resources. The Messages smoke check verified
  metadata, UTC timestamps, ordered retrieval, and pagination. Smoke-test rows
  were rolled back.
- PostgreSQL authenticated smoke check passed: user provisioning, login, profile
  creation, availability, agent reply, and immediate deactivation. All smoke records
  were rolled back; no initial admin was left behind.
- A pre-existing Starlette TestClient/httpx deprecation warning remains.

## Development stages

| Stage | Status |
| --- | --- |
| Core backend and Customer CRUD | Complete |
| Conversation creation/retrieval | Complete |
| Customer/agent text messages and conversation history | Complete |
| User authentication and human support-agent profiles | Complete |
| Conversation listing, assignment, and lifecycle | Next |
| Escalations | Queued after conversation management |
| Call records (no telephony integration) | Queued after escalations |
| Final authenticated workflow, PostgreSQL/migrations, Docker, errors, documentation | Queued after call records |
| LLM, RAG, AI agents, and real voice integrations | Later |

At each completed stage, update this README with functionality, endpoint examples,
configuration/migration changes, test results, and remaining limitations. Keep
local learning/planning Markdown files out of commits; README is the tracked
project documentation.

The next four stages are saved for a later session. No timed execution has been
scheduled and no further implementation starts until requested.
