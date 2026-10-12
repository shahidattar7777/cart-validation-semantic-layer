"""Regression check: the planted stories and gaps are present and the demo
queries find exactly them. Run after regenerating data or editing the YAML.

    python scripts/verify.py
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from scripts.db import ROOT, connect  # noqa: E402

Q = ROOT / "demo" / "queries"
failures = []


def check(name, cond, detail=""):
    print(f"  [{'PASS' if cond else 'FAIL'}] {name}" + (f"  ({detail})" if detail else ""))
    if not cond:
        failures.append(name)


def col(cur, sql, i=0):
    cur.execute(sql)
    return [r[i] for r in cur.fetchall()]


with connect() as conn, conn.cursor() as cur:
    cur.execute("LOAD 'age'")
    cur.execute('SET search_path = ag_catalog, "$user", public')

    print("Process stories")
    cur.execute("""
        SELECT avg(q.result_val) FILTER (WHERE t.td_ts <  '2026-04-20'),
               avg(q.result_val) FILTER (WHERE t.td_ts >= '2026-04-20')
        FROM pd.uo04_transduction t JOIN pd.qc_rel_results q ON q.batch_id = t.batch_id AND q.test_code = 'FC-CAR'
        WHERE t.vec_lot = 'LV25-118' AND t.moi_tgt = 5""")
    before, after = cur.fetchone()
    check("S1 LV25-118 %CAR+ drops after freezer failure", after < 20 < before, f"{before:.1f} -> {after:.1f}")
    eng_fail = col(cur, "SELECT batch_id FROM pd.qc_rel_results WHERE test_code='FC-CAR' AND result_val < 20 AND batch_id NOT LIKE 'PD%'")
    check("S1 all ENG runs (and no PPQ run) below 20% CAR+", sorted(eng_fail) == ["ENG26-01", "ENG26-02", "ENG26-03"], str(eng_fail))
    cur.execute("SELECT via_pct FROM pd.uo06_harvest WHERE batch_id = 'PPQ26-02'")
    check("S2 PPQ26-02 harvest viability < 80%", cur.fetchone()[0] < 80)
    cur.execute("""SELECT min(h.via_pct) FROM pd.uo06_harvest h WHERE h.batch_id IN ('PPQ26-01','PPQ26-03','PPQ26-04','PPQ26-05')""")
    check("S2 other PPQ batches harvest viability >= 80%", cur.fetchone()[0] >= 80)

    print("Demo queries (graph + semantic layer)")

    def run(name):
        cur.execute((Q / name).read_text(encoding="utf-8"))
        return cur.fetchall()

    r = run("q1_coverage.graph.sql")
    check("Q1 finds exactly the three unverified high-risk requirements",
          sorted(x[0] for x in r) == ["URS-EBR-009", "URS-EMS-014", "URS-INC-004"], str([x[0] for x in r]))
    r = run("q2_moi_change_impact.graph.sql")
    items = {x[1] for x in r}
    check("Q2 finds EBR hard stop, PPQ range and FMEA rows",
          {"CS-EBR-03", "URS-EBR-009", "PPQ-001", "FM-05", "FM-06"} <= items)
    r = run("q3_common_cause.graph.sql")
    check("Q3 links CAPA-26-008 and CAPA-26-015 through CC-26-011",
          len(r) == 1 and r[0][0] == "CAPA-26-008 / CAPA-26-015" and r[0][5] == "CC-26-011")
    r = run("q4_cqa_traceability.graph.sql")
    check("Q4 surfaces the freezer -> vector lot -> ENG deviation link",
          any(x[0] == "8 Hidden link" and "LV25-118" in x[1] for x in r))
    check("Q4 deviation layer = DEV-26-021 and DEV-26-027",
          sorted(x[1] for x in r if x[0] == "7 Deviation") == ["DEV-26-021", "DEV-26-027"])
    check("Q4 flags TC-OQ-EMS-04 as stale", any(x[1] == "TC-OQ-EMS-04" and "STALE" in str(x[3]) for x in r))
    r = run("q5_oq_without_pq.graph.sql")
    check("Q5 finds FM-02 and FM-13", sorted(x[0] for x in r) == ["FM-02", "FM-13"], str([x[0] for x in r]))
    r = run("q6_ppq_cpp_excursions.graph.sql")
    check("Q6 finds unreported CPP excursion in PPQ26-03",
          any(x[0] == "PPQ26-03" and x[-1] == "NONE" for x in r))

    print("Flat-table versions miss them")
    check("Q1 naive misses URS-INC-004", "URS-INC-004" not in {x[0] for x in run("q1_coverage.naive.sql")})
    check("Q3 naive finds no shared root cause", len(run("q3_common_cause.naive.sql")) == 0)
    check("Q5 naive finds nothing", len(run("q5_oq_without_pq.naive.sql")) == 0)
    check("Q6 naive does not mention PPQ26-03", all("PPQ26-03" not in str(x) for x in run("q6_ppq_cpp_excursions.naive.sql")))

print(f"\n{'All checks passed.' if not failures else f'{len(failures)} check(s) failed: {failures}'}")
sys.exit(1 if failures else 0)
