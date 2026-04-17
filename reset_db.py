#!/usr/bin/env python
"""Reset the database to its initial state."""
from __future__ import annotations

import os
import sys
from pathlib import Path

import db

DB_PATH = os.environ.get("ECOMM_DB", "ecomm.sqlite")


def reset_database() -> None:
    """Delete the existing database and reinitialize it."""
    db_file = Path(DB_PATH)

    if db_file.exists():
        print(f"Deleting {DB_PATH}...")
        db_file.unlink()
        print("✓ Database deleted.")

    print(f"Initializing fresh database at {DB_PATH}...")
    db.initialize(DB_PATH)
    print("✓ Database initialized with seed data.")
    print("\nDatabase reset complete!")


if __name__ == "__main__":
    try:
        reset_database()
    except Exception as e:
        print(f"Error resetting database: {e}", file=sys.stderr)
        sys.exit(1)
