# Customer Support Platform

A FastAPI backend for managing customer-support interactions. The project uses a
modular monolith with PostgreSQL, async SQLAlchemy, Pydantic, and Alembic.

## Current functionality

- Customer creation, listing, retrieval, partial updates, and deletion.
- Conversation creation for an existing customer and retrieval by ID.
- CHAT, VOICE, and PHONE channels; new conversations start OPEN.
- Input validation, missing-resource responses, and database constraints.
- Versioned database migrations and automated service/API/persistence tests.

Authentication is not implemented yet. Run this increment locally; the API is not
ready for public deployment. No frontend, LLM, RAG, or telephony integration is included.

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

docker compose -f docker/docker-compose.yml up -d --wait db
uv run alembic -c alembic/alembic.ini upgrade head
uv run uvicorn src.main:app --reload
```

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
| `DATABASE_URL` | `postgresql+asyncpg://postgres:postgres@localhost:5433/customer_support` | Local database connection |

The supplied credentials are development defaults. If your existing `.env` has a
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

Stop the stack while retaining database data:

```bash
docker compose -f docker/docker-compose.yml down
```

Do not add `--volumes` unless you intend to delete the stored database data.
The database container has been verified; the full API image build/start has not
yet been verified in this milestone.

## Use the API

### 1. Create a customer

```bash
curl -i -X POST http://localhost:8000/api/v1/customers \
  -H 'Content-Type: application/json' \
  -d '{"name":"Mona","email":"mona@example.com","phone":"+201234567890"}'
```

Expect HTTP 201 with a generated `id`, contact details, and timestamps. Use that
customer ID in subsequent requests; the examples below assume it is `1`.

### 2. Start a conversation

```bash
curl -i -X POST http://localhost:8000/api/v1/conversations \
  -H 'Content-Type: application/json' \
  -d '{"customer_id":1,"channel":"CHAT"}'
```

Expect HTTP 201 with status `OPEN`, a generated conversation ID, timestamps, and
`ended_at: null`. Use the returned conversation ID to retrieve it:

```bash
curl http://localhost:8000/api/v1/conversations/1
```

### 3. List or update customers

```bash
curl 'http://localhost:8000/api/v1/customers?offset=0&limit=20'
curl -X PATCH http://localhost:8000/api/v1/customers/1 \
  -H 'Content-Type: application/json' \
  -d '{"email":null}'
```

PATCH preserves omitted fields. Explicit null clears email or phone; name cannot
be null. Customer listing is ordered by ID and supports `offset >= 0` and a
`limit` between 1 and 100.

### Endpoint reference

| Method | Path | Success |
| --- | --- | --- |
| GET | `/health` | 200 |
| POST | `/api/v1/customers` | 201 |
| GET | `/api/v1/customers` | 200 |
| GET | `/api/v1/customers/{customer_id}` | 200 |
| PATCH | `/api/v1/customers/{customer_id}` | 200 |
| DELETE | `/api/v1/customers/{customer_id}` | 204, empty body |
| POST | `/api/v1/conversations` | 201 |
| GET | `/api/v1/conversations/{conversation_id}` | 200 |

Conversation creation requires a positive customer ID and channel CHAT, VOICE, or
PHONE. Additional fields, including client-supplied status, are rejected.

Missing customers/conversations return 404 with `detail` and `code` fields.
Invalid input returns 422. Deleting a customer with conversation history is
blocked by the database; a friendly HTTP 409 mapping remains to be implemented.
There is no Conversation update, list, or delete endpoint yet.

## Architecture

```text
HTTP → Route → Controller → Service → Repository → PostgreSQL
```

| Directory/file | Responsibility |
| --- | --- |
| `src/main.py` | Application setup, exception handler, lifespan |
| `src/core/` | Settings, database sessions, application errors |
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
foreign key/index, and channel/status CHECK constraints.

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
```

Service tests mock repositories. API/persistence tests use a fresh SQLite database
per test with foreign-key enforcement and real application layers. PostgreSQL is
not needed for this suite; these tests do not validate Alembic migration execution.

Latest milestone verification:

- 29 tests passed, including history preservation and allowed-state constraints.
- PostgreSQL 18 database container started successfully.
- Migrations applied through `0002`; Alembic reported no schema differences.
- An HTTP smoke check against PostgreSQL verified all channels, UTC timestamps,
  retrieval, invalid input, and missing resources. Smoke-test rows were rolled back.
- A pre-existing Starlette TestClient/httpx deprecation warning remains.

## Development stages

| Stage | Status |
| --- | --- |
| Core backend and Customer CRUD | Complete |
| Conversation creation/retrieval | Complete |
| Messages and conversation history | Next |
| User authentication and human support-agent profiles | Planned |
| Conversation listing, assignment, and lifecycle | Planned |
| Escalations and call records | Planned |
| Full authenticated workflow and container verification | Planned |
| LLM, RAG, AI agents, and real voice integrations | Later |

At each completed stage, update this README with functionality, endpoint examples,
configuration/migration changes, test results, and remaining limitations. Keep
local learning/planning Markdown files out of commits; README is the tracked
project documentation.
