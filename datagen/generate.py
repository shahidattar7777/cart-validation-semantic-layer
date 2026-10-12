"""Generate all synthetic CSVs.

    python -m datagen.generate            # writes ./data/*.csv (seed 42)
    python -m datagen.generate --seed 7 --out data_alt
"""
from __future__ import annotations

import argparse
import csv
from datetime import date, datetime
from pathlib import Path

import numpy as np

from . import process, validation

# Load order respects foreign keys.
TABLE_ORDER = [
    "donor", "leukopak", "val_system", "equipment", "material_lot", "material_coa", "batch_master",
    "uo01_aph_receipt", "uo02_tcell_sel", "uo03_activation", "uo04_transduction", "uo05_expansion",
    "uo06_harvest", "uo07_form_fill", "qc_rel_results", "equipment_event", "hist_tag_data",
    "val_spec_item", "val_risk_assessment", "val_risk_item", "val_protocol", "val_test_case",
    "val_test_exec", "val_ppq_criterion", "analytical_method", "sop", "qms_deviation", "qms_capa",
    "qms_change_control", "trace_link",
]


def _fmt(v):
    if v is None:
        return ""
    if isinstance(v, datetime):
        return v.strftime("%Y-%m-%d %H:%M:%S")
    if isinstance(v, date):
        return v.isoformat()
    if isinstance(v, float):
        return repr(round(v, 6))
    return str(v)


def generate(seed: int = 42) -> dict[str, list[dict]]:
    rng = np.random.default_rng(seed)
    tables = process.build(rng)
    tables.update(validation.build(tables))
    missing = set(TABLE_ORDER) - set(tables)
    assert not missing, f"generator did not produce: {missing}"
    return tables


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--out", default="data")
    args = ap.parse_args()
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    tables = generate(args.seed)
    for name in TABLE_ORDER:
        rows = tables[name]
        cols = list(rows[0].keys())
        for r in rows[1:]:
            for c in r:
                if c not in cols:
                    cols.append(c)
        with open(out / f"{name}.csv", "w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(cols)
            for r in rows:
                w.writerow([_fmt(r.get(c)) for c in cols])
        print(f"  {name:22s} {len(rows):>7,d} rows")
    print(f"Wrote {len(TABLE_ORDER)} tables to {out.resolve()}")


if __name__ == "__main__":
    main()
