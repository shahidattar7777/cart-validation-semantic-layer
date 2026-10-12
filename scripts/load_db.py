"""Create the pd schema and load the generated CSVs.

    python scripts/load_db.py            # (re)creates schema pd and loads ./data
    python scripts/load_db.py --data data_alt
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from datagen.generate import TABLE_ORDER  # noqa: E402
from scripts.db import ROOT, connect  # noqa: E402


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", default=str(ROOT / "data"))
    args = ap.parse_args()
    data = Path(args.data)
    schema_sql = (ROOT / "db" / "schema.sql").read_text(encoding="utf-8")
    with connect() as conn:
        with conn.cursor() as cur:
            cur.execute(schema_sql)
            for name in TABLE_ORDER:
                path = data / f"{name}.csv"
                with open(path, encoding="utf-8") as f:
                    header = f.readline().strip()
                cols = ", ".join(header.split(","))
                with cur.copy(f"COPY pd.{name} ({cols}) FROM STDIN WITH (FORMAT csv, HEADER true, NULL '')") as cp:
                    with open(path, "rb") as f:
                        while chunk := f.read(1 << 16):
                            cp.write(chunk)
                cur.execute(f"SELECT count(*) FROM pd.{name}")
                print(f"  pd.{name:22s} {cur.fetchone()[0]:>7,d} rows")
        conn.commit()
    print("Loaded.")


if __name__ == "__main__":
    main()
