#!/usr/bin/env python3
"""
apply_tags_from_csv.py
----------------------
Read a CSV file with columns: CAUSE,JOURNEY_NUM,DEP_DATE
For each row, run the following SQL against a PostgreSQL database:

1) INSERT INTO ana_tag(code, version) VALUES (%s, 42) ON CONFLICT DO NOTHING;
2) DELETE FROM ana_tag_journey_elt WHERE code = %s;
3) INSERT INTO ana_tag_journey_elt(code, journey_id)
   SELECT %s, id FROM net_journey WHERE (num, dep_date) IN ((%s, %s)) ON CONFLICT DO NOTHING;

Configuration via environment variables:
- PGHOST
- PGPORT (optional, default 5432)
- PGUSER
- PGPASSWORD
- PGDATABASE

Usage:
    python scripts/apply_tags_from_csv.py path/to/file.csv

The script uses parameterized queries (psycopg2) and executes each CSV row in its own transaction.
"""

import argparse
import csv
import os
import sys
import logging
from datetime import datetime
from typing import Optional

try:
    import psycopg2
except Exception:
    print("Missing dependency: psycopg2. Install with: pip install psycopg2-binary")
    raise

from dotenv import load_dotenv

# Load .env file if present
load_dotenv()

# Configure logging
logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"), format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)


def parse_args():
    parser = argparse.ArgumentParser(description="Apply tags and link journeys from a CSV to Postgres DB")
    parser.add_argument("csv_file", help="Path to CSV file. Expected header: CAUSE,JOURNEY_NUM,DEP_DATE")
    return parser.parse_args()


def get_conn():
    # Read variables from .env or environment using the APPIA5_ prefix
    params = {
        "host": os.getenv("APPIA5_PG_HOST", os.getenv("PGHOST", "localhost")),
        "port": int(os.getenv("APPIA5_PG_PORT", os.getenv("PGPORT", 5432))),
        "user": os.getenv("APPIA5_PG_USER", os.getenv("PGUSER", "")),
        "password": os.getenv("APPIA5_PG_PASSWD", os.getenv("PGPASSWORD", "")),
        "dbname": os.getenv("APPIA5_PG_DB", os.getenv("PGDATABASE", "")),
    }

    missing = [k for k, v in params.items() if k in ("user", "password", "dbname") and not v]
    if missing:
        logger.error("Missing required PG env vars: APPIA5_PG_USER, APPIA5_PG_PASSWD, APPIA5_PG_DB must be set (or PGUSER/PGPASSWORD/PGDATABASE)")
        raise RuntimeError("Missing required PG env vars: APPIA5_PG_USER, APPIA5_PG_PASSWD, APPIA5_PG_DB must be set")

    conn = psycopg2.connect(**params)
    return conn


def validate_date(value: str) -> Optional[str]:
    # Accepts ISO date YYYY-MM-DD or YYYY/MM/DD. Returns value unchanged if parseable or None.
    if not value:
        return None
    for fmt in ("%Y-%m-%d", "%Y/%m/%d", "%d-%m-%Y", "%d/%m/%Y"):
        try:
            _ = datetime.strptime(value, fmt)
            return value
        except Exception:
            continue
    return None


def process_row(conn, cause: str, journey_num: str, dep_date: str):
    """Execute SQL for a single CSV row in its own transaction."""
    if not cause:
        raise ValueError("CAUSE is required")

    cur = conn.cursor()

    try:
        # 1) insert into ana_tag
        insert_tag_sql = "INSERT INTO ana_tag(code, version) VALUES (%s, 42) ON CONFLICT DO NOTHING"

        # 3) insert into ana_tag_journey_elt selecting matching journeys
        # We'll use a parameterized form for (num, dep_date) IN ((%s, %s))
        insert_tag_journey_sql = (
            "INSERT INTO ana_tag_journey_elt(code, journey_id)\n"
            "SELECT %s, id FROM net_journey WHERE (num, dep_date) IN ((%s, %s)) ON CONFLICT DO NOTHING"
        )

        logger.debug("Prepared SQLs for cause=%s journey_num=%s dep_date=%s", cause, journey_num, dep_date)

        # Execute within a transaction for this row
        cur.execute(insert_tag_sql, (cause,))

        # If journey_num or dep_date are empty, the SELECT will likely match nothing
        cur.execute(insert_tag_journey_sql, (cause, journey_num, dep_date))

        conn.commit()
        logger.info("Processed cause=%s journey_num=%s dep_date=%s", cause, journey_num, dep_date)

    except Exception:
        conn.rollback()
        logger.exception("Failed to process row cause=%s journey_num=%s dep_date=%s", cause, journey_num, dep_date)
        raise
    finally:
        cur.close()


def main():
    args = parse_args()

    if not os.path.exists(args.csv_file):
        logger.error("CSV file not found: %s", args.csv_file)
        sys.exit(2)

    # Read CSV
    rows = []
    with open(args.csv_file, newline="", encoding="utf-8") as fh:
        reader = csv.reader(fh)
        # Accept a header optionally
        first = next(reader, None)
        if first is None:
            logger.error("Empty CSV file")
            sys.exit(2)

        headers_lower = [h.strip().upper() for h in first]
        has_header = False
        if headers_lower[:3] == ["CAUSE", "JOURNEY_NUM", "DEP_DATE"]:
            has_header = True
        else:
            # assume first line was data
            rows.append(first)

        for r in reader:
            rows.append(r)

    logger.info("Read %d data rows (header=%s)", len(rows), has_header)

    conn = get_conn()

    # Collect unique CAUSE codes and execute a single delete before processing rows
    causes = []
    for r in rows:
        if len(r) >= 1:
            c = r[0].strip()
            if c:
                causes.append(c)

    unique_causes = list(dict.fromkeys(causes))  # preserve order, unique
    if unique_causes:
        logger.info("Deleting existing ana_tag_journey_elt entries for %d unique cause(s)", len(unique_causes))
        cur = conn.cursor()
        try:
            delete_all_sql = "DELETE FROM ana_tag_journey_elt WHERE code = ANY(%s)"
            cur.execute(delete_all_sql, (unique_causes,))
            conn.commit()
            logger.info("Deleted existing ana_tag_journey_elt rows for provided causes")
        except Exception:
            conn.rollback()
            logger.exception("Failed to delete existing ana_tag_journey_elt rows")
            raise
        finally:
            cur.close()

    processed = 0
    errors = 0

    try:
        for r in rows:
            # allow rows with 3+ columns; ignore extras
            if len(r) < 3:
                logger.warning("Skipping malformed row (expected 3 columns): %s", r)
                errors += 1
                continue

            cause = r[0].strip()
            journey_num = r[1].strip()
            dep_date_raw = r[2].strip()

            dep_date = validate_date(dep_date_raw)
            if dep_date_raw and not dep_date:
                logger.warning("Row has invalid date format, still passing through as string: %s", dep_date_raw)
                dep_date = dep_date_raw

            try:
                process_row(conn, cause, journey_num, dep_date)
                processed += 1
            except Exception:
                errors += 1

    finally:
        if conn:
            conn.close()

    logger.info("Done. Processed=%d errors=%d", processed, errors)


if __name__ == "__main__":
    main()
