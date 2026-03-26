import os
import logging
from datetime import datetime, date
from decimal import Decimal
from typing import List, Dict, Any

import httpx
from sqlalchemy.orm import Session
from sqlalchemy.dialects.postgresql import insert as pg_insert

from models.customer import Customer

logger = logging.getLogger(__name__)

FLASK_BASE_URL = os.getenv("FLASK_BASE_URL", "http://mock-server:5000")
FETCH_LIMIT = int(os.getenv("FETCH_LIMIT", "10"))


def _parse_customer(raw: Dict[str, Any]) -> Dict[str, Any]:
    """Normalise raw JSON from Flask into DB-ready dict."""
    dob = raw.get("date_of_birth")
    if isinstance(dob, str) and dob:
        try:
            dob = datetime.strptime(dob, "%Y-%m-%d").date()
        except ValueError:
            dob = None

    created_at = raw.get("created_at")
    if isinstance(created_at, str) and created_at:
        try:
            created_at = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
        except ValueError:
            created_at = None

    balance = raw.get("account_balance")
    if balance is not None:
        try:
            balance = Decimal(str(balance))
        except Exception:
            balance = None

    return {
        "customer_id": raw.get("customer_id"),
        "first_name": raw.get("first_name"),
        "last_name": raw.get("last_name"),
        "email": raw.get("email"),
        "phone": raw.get("phone"),
        "address": raw.get("address"),
        "date_of_birth": dob,
        "account_balance": balance,
        "created_at": created_at,
    }


def fetch_all_customers() -> List[Dict[str, Any]]:
    """Fetch every customer from Flask, handling pagination automatically."""
    all_customers: List[Dict[str, Any]] = []
    page = 1

    with httpx.Client(timeout=30) as client:
        while True:
            url = f"{FLASK_BASE_URL}/api/customers"
            params = {"page": page, "limit": FETCH_LIMIT}
            logger.info(f"Fetching page {page} from Flask: {url}")

            response = client.get(url, params=params)
            response.raise_for_status()
            payload = response.json()

            data = payload.get("data", [])
            all_customers.extend(data)

            total = payload.get("total", 0)
            if len(all_customers) >= total or not data:
                break

            page += 1

    logger.info(f"Fetched {len(all_customers)} customers from Flask")
    return all_customers


def upsert_customers(db: Session, raw_records: List[Dict[str, Any]]) -> int:
    """Upsert customer records into PostgreSQL. Returns number of records processed."""
    if not raw_records:
        return 0

    parsed = [_parse_customer(r) for r in raw_records]

    stmt = pg_insert(Customer).values(parsed)
    stmt = stmt.on_conflict_do_update(
        index_elements=["customer_id"],
        set_={
            "first_name": stmt.excluded.first_name,
            "last_name": stmt.excluded.last_name,
            "email": stmt.excluded.email,
            "phone": stmt.excluded.phone,
            "address": stmt.excluded.address,
            "date_of_birth": stmt.excluded.date_of_birth,
            "account_balance": stmt.excluded.account_balance,
            "created_at": stmt.excluded.created_at,
        },
    )
    db.execute(stmt)
    db.commit()

    logger.info(f"Upserted {len(parsed)} records into PostgreSQL")
    return len(parsed)
