"""Shared connection helper. Settings come from environment variables or .env."""
from __future__ import annotations

import os
from pathlib import Path

import psycopg

ROOT = Path(__file__).resolve().parents[1]


def _load_env() -> None:
    env = ROOT / ".env"
    if env.exists():
        for line in env.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip())


def connect(autocommit: bool = False) -> psycopg.Connection:
    _load_env()
    return psycopg.connect(
        host=os.environ.get("PGHOST", "localhost"),
        port=int(os.environ.get("PGPORT", "5455")),
        dbname=os.environ.get("PGDATABASE", "cartpd"),
        user=os.environ.get("PGUSER", "cart"),
        password=os.environ.get("PGPASSWORD", "cart"),
        autocommit=autocommit,
    )
