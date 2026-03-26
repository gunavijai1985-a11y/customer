# Customer Data Pipeline

A 3-service Docker data pipeline built for the Backend Developer Technical Assessment.

```
Flask Mock Server (port 5000)
        │
        ▼  (pagination-aware fetch)
FastAPI Pipeline Service (port 8000)
        │
        ▼  (upsert)
PostgreSQL (port 5432)
```

---

## Prerequisites

| Tool | Version |
|---|---|
| Docker Desktop | running |
| docker-compose | v2+ |
| (optional) Python | 3.10+ |

---

## Quick Start

```bash
# Clone / unzip the project, then:
cd customer-pipeline

# Build and start all services
docker-compose up -d --build

# Check all containers are healthy
docker-compose ps
```

Wait ~15 seconds for PostgreSQL and the mock server to be ready, then:

```bash
# Trigger the ingestion pipeline
curl -X POST http://localhost:8000/api/ingest
# → {"status":"success","records_processed":22}
```

---

## Services

### 1. Flask Mock Server — `http://localhost:5000`

Serves 22 customers from `mock-server/data/customers.json`.

| Endpoint | Method | Description |
|---|---|---|
| `/api/health` | GET | Health check |
| `/api/customers` | GET | Paginated list (`page`, `limit` params) |
| `/api/customers/{id}` | GET | Single customer or 404 |

```bash
# Health
curl http://localhost:5000/api/health

# Page 1, 5 records
curl "http://localhost:5000/api/customers?page=1&limit=5"

# Single customer
curl http://localhost:5000/api/customers/CUST001
```

---

### 2. FastAPI Pipeline Service — `http://localhost:8000`

| Endpoint | Method | Description |
|---|---|---|
| `/api/health` | GET | Health check |
| `/api/ingest` | POST | Fetch all Flask data → upsert to PostgreSQL |
| `/api/customers` | GET | Paginated results from DB (`page`, `limit`) |
| `/api/customers/{id}` | GET | Single customer from DB or 404 |
| `/docs` | GET | Interactive Swagger UI |

```bash
# Ingest
curl -X POST http://localhost:8000/api/ingest

# List from DB
curl "http://localhost:8000/api/customers?page=1&limit=5"

# Single from DB
curl http://localhost:8000/api/customers/CUST001
```

Interactive API docs: http://localhost:8000/docs

---

## Project Structure

```
customer-pipeline/
├── docker-compose.yml
├── README.md
├── mock-server/
│   ├── app.py                  # Flask application
│   ├── data/
│   │   └── customers.json      # 22 customer records
│   ├── Dockerfile
│   └── requirements.txt
└── pipeline-service/
    ├── main.py                 # FastAPI application
    ├── database.py             # SQLAlchemy engine & session
    ├── models/
    │   └── customer.py         # Customer ORM model
    ├── services/
    │   └── ingestion.py        # Fetch + upsert logic
    ├── Dockerfile
    └── requirements.txt
```

---

## Stopping Services

```bash
docker-compose down          # stop containers
docker-compose down -v       # stop containers + delete DB volume
```
