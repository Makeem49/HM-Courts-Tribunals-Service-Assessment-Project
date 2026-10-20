# HMCTS Casework Task Manager

A small full-stack task-management application built with Flask, Marshmallow, SQLAlchemy, SQLite and vanilla JavaScript. The frontend and backend are separated into distinct directories; Flask serves the static frontend and exposes a JSON REST API.

## Features

- Create, list, retrieve, edit and delete tasks.
- Change task status independently: `pending`, `in_progress` or `completed`.
- Optional description and required due date/time.
- Server-side pagination, search and status filtering, summary counts, overdue indicators and responsive layout.
- Marshmallow request validation and consistent JSON error responses.
- SQLite persistence, repository/service separation and API tests.

## Requirements

- Python 3.10+
- pip

## Run locally

```bash
python -m venv .venv
source .venv/bin/activate       # Windows: .venv\\Scripts\\activate
pip install -r requirements.txt
python run.py
```

Open <http://127.0.0.1:5000>. The database is created automatically on first launch. For production, set `SECRET_KEY` and `DATABASE_URL` environment variables, turn off Flask debug mode, and use a production WSGI server.

## Run with Docker

```bash
docker compose up --build -d
```

Open <http://localhost:8000>. The container runs the app under Gunicorn as a non-root user and reports health via `/api/health`. The SQLite database is stored in the `task-data` named volume, so tasks persist across restarts and rebuilds.

| Command | Purpose |
|---|---|
| `docker compose logs -f app` | Follow application and access logs |
| `docker compose run --rm --no-deps app pytest -q -p no:cacheprovider` | Run the test suite inside the image |
| `docker compose down` | Stop the app (data is kept) |
| `docker compose down -v` | Stop the app and delete the database volume |

Configuration is read from the docker compose environment or a `.env` 

- `SECRET_KEY`: set this to a long random value outside local development.
- `APP_PORT`: the host port (default `8000`). Port 5000 is avoided because macOS uses it for AirPlay Receiver.
- `GUNICORN_CMD_ARGS`: overrides the default `--workers 1 --threads 4`. Keep a single worker while using SQLite.

## Tests

```bash
pytest -q
```

The tests use an isolated in-memory SQLite database. They cover creation, listing/filtering, pagination, search, summary counts, retrieval, status updates, general updates, deletion, invalid input, missing records and empty updates.

## Architecture

```text
app/
  api/tasks.py                  HTTP routes and response mapping
  models/task.py                SQLAlchemy persistence model
  repositories/task_repository.py  Database access
  schemas/task_schema.py        Marshmallow validation/serialisation
  services/task_service.py      Business rules and orchestration
  extensions.py                 Shared SQLAlchemy extension
  __init__.py                   Application factory and error handlers
frontend/
  index.html                    Semantic page structure
  css/styles.css                Responsive interface styling
  js/app.js                     UI state, DOM rendering and Fetch API calls
tests/                          pytest API tests
run.py                          Local entry point and WSGI app (run:app)
Dockerfile                      Production image (Gunicorn, non-root)
docker-compose.yml              Local container setup with a persistent volume
```

Routes only handle HTTP concerns. The service layer coordinates business operations, while the repository owns data access. Marshmallow schemas validate input before the service receives it. The frontend does not directly access the database.

## API reference

Base URL: `/api/tasks`. JSON request and response bodies use UTF-8. Dates must be ISO-8601 date-times with an explicit timezone, for example `2030-10-20T15:00:00Z`. Accepted statuses are `pending`, `in_progress`, and `completed`.

| Method | Endpoint | Description | Success |
|---|---|---|---|
| `GET` | `/api/tasks` | List tasks one page at a time, sorted by due date | `200` |
| `GET` | `/api/tasks?status=pending&search=bundle&page=2` | Filter, search and page through tasks | `200` |
| `GET` | `/api/tasks/summary` | Count tasks by status | `200` |
| `POST` | `/api/tasks` | Create a task | `201` |
| `GET` | `/api/tasks/{id}` | Retrieve a task | `200` |
| `PATCH` | `/api/tasks/{id}` | Partially update task fields | `200` |
| `PATCH` | `/api/tasks/{id}/status` | Update only the status | `200` |
| `DELETE` | `/api/tasks/{id}` | Delete a task | `204` |
| `GET` | `/api/health` | Health check | `200` |

### Listing, pagination and search

`GET /api/tasks` accepts these optional query parameters. Blank values are ignored; invalid values return `400`.

| Parameter | Default | Description |
|---|---|---|
| `page` | `1` | 1-based page number. A page past the end returns an empty `items` list. |
| `page_size` | `10` | Tasks per page, from 1 to 100. |
| `status` | — | One of `pending`, `in_progress` or `completed`. |
| `search` | — | Case-insensitive match on title or description (max 200 characters). |

```json
{
  "items": [{"id": 11, "title": "Review case documents", "...": "..."}],
  "count": 1,
  "total": 11,
  "page": 2,
  "page_size": 10,
  "pages": 2
}
```

`count` is the number of items on this page; `total` is the number of tasks matching the filters across all pages.

`GET /api/tasks/summary` returns workload totals that are unaffected by paging or filters:

```json
{"total": 11, "pending": 6, "in_progress": 3, "completed": 2}
```

### Create task example

`POST /api/tasks`

```json
{
  "title": "Review case documents",
  "description": "Check the latest submission.",
  "status": "pending",
  "due_at": "2030-10-20T15:00:00Z"
}
```

`description` is optional and may be `null`; `status` defaults to `pending`. The title must contain 1–160 non-whitespace characters and must be unique: titles are compared case-insensitively after trimming whitespace, so `Review case documents` and ` review CASE documents ` count as the same title. Descriptions are limited to 5,000 characters.

### Update status example

`PATCH /api/tasks/1/status`

```json
{"status": "in_progress"}
```

### Error format

Validation failures return `400`:

```json
{
  "error": "Validation failed",
  "details": {"title": ["Short validation message"]}
}
```

A missing task returns `404` with `error` and `message`. Creating a task, or renaming one, with a title that another task already uses returns `409`:

```json
{"error": "Conflict", "message": "A task with this title already exists."}
```

Unexpected server errors return a generic `500` response; details are written to the application log rather than exposed to the client.

