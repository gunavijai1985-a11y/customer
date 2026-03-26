import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from database import init_db, get_db
from models.customer import Customer
from services.ingestion import fetch_all_customers, upsert_customers

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Initialising database tables...")
    init_db()
    logger.info("Database ready.")
    yield


app = FastAPI(
    title="Customer Pipeline Service",
    description="Ingests customer data from Flask mock server into PostgreSQL",
    version="1.0.0",
    lifespan=lifespan,
)


# ──────────────────────────────────────────────
# Health
# ──────────────────────────────────────────────

@app.get("/api/health")
def health():
    return {"status": "healthy", "service": "pipeline-service"}


# ──────────────────────────────────────────────
# Ingest
# ──────────────────────────────────────────────

@app.post("/api/ingest")
def ingest(db: Session = Depends(get_db)):
    """
    Fetch all customer data from the Flask mock server (handles pagination
    automatically) and upsert every record into PostgreSQL.
    """
    try:
        raw_records = fetch_all_customers()
        records_processed = upsert_customers(db, raw_records)
        return {"status": "success", "records_processed": records_processed}
    except Exception as exc:
        logger.error(f"Ingestion failed: {exc}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Ingestion failed: {str(exc)}")


# ──────────────────────────────────────────────
# Customers
# ──────────────────────────────────────────────

@app.get("/api/customers")
def list_customers(
    page: int = Query(1, ge=1, description="Page number (1-based)"),
    limit: int = Query(10, ge=1, le=100, description="Records per page"),
    db: Session = Depends(get_db),
):
    """Return a paginated list of customers from the database."""
    total = db.query(Customer).count()
    offset = (page - 1) * limit
    customers = (
        db.query(Customer)
        .order_by(Customer.customer_id)
        .offset(offset)
        .limit(limit)
        .all()
    )
    return {
        "data": [c.to_dict() for c in customers],
        "total": total,
        "page": page,
        "limit": limit,
    }


@app.get("/api/customers/{customer_id}")
def get_customer(customer_id: str, db: Session = Depends(get_db)):
    """Return a single customer by ID, or 404 if not found."""
    customer = db.query(Customer).filter(Customer.customer_id == customer_id).first()
    if not customer:
        raise HTTPException(
            status_code=404, detail=f"Customer '{customer_id}' not found"
        )
    return {"data": customer.to_dict()}
