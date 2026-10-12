"""Check the agent plumbing without calling the API (free).

    python agent/selftest.py

- the raw condition can read pd tables but not the graph, and is read-only
- the semantic condition can run cypher() and is read-only
- the answer key scores the reference answers as 1.0 and a typical
  flat-table answer lower
"""
from __future__ import annotations

import sys
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from agent.run_eval import AGENT_DIR, build_prompts, ensure_raw_role, extract_ids, run_sql, score  # noqa: E402

ok = True


def check(name, cond, detail=""):
    global ok
    ok &= bool(cond)
    print(f"  [{'PASS' if cond else 'FAIL'}] {name}" + (f"  ({detail})" if detail and not cond else ""))


ensure_raw_role()
print("Database tool")
out, err = run_sql("raw", "SELECT count(*) FROM batch_master")
check("raw: can query pd tables", not err, out)
out, err = run_sql("raw", "SELECT * FROM cypher('cart_kg', $$ MATCH (n) RETURN n LIMIT 1 $$) AS (n agtype)")
check("raw: graph blocked", err)
out, err = run_sql("raw", "SELECT count(*) FROM information_schema.tables WHERE table_schema NOT IN ('pd','information_schema','pg_catalog')")
check("raw: graph tables not visible in information_schema", not err and out.splitlines()[1].strip() == "0", out)
out, err = run_sql("raw", "DELETE FROM batch_master")
check("raw: read-only", err and ("read-only" in out or "permission denied" in out), out)
out, err = run_sql("semantic", "SELECT kg_txt(b) FROM cypher('cart_kg', $$ MATCH (p:Protocol {ptype:'PPQ'})-[:INCLUDES_BATCH]->(b:Batch) RETURN b.id $$) AS (b agtype)")
check("semantic: cypher works", not err and "PPQ26-01" in out, out)
out, err = run_sql("semantic", "DELETE FROM pd.batch_master")
check("semantic: read-only", err and "read-only" in out, out)

print("Prompts")
p = build_prompts()
check("raw prompt has no YAML or graph", "cart_kg" not in p["raw"] and "aliases" not in p["raw"])
check("semantic prompt has YAML", "quality_attributes" in p["semantic"] and "cart_kg" in p["semantic"])
print(f"  raw prompt ~{len(p['raw']) // 4:,} tokens, semantic prompt ~{len(p['semantic']) // 4:,} tokens")

print("Scoring")
qs = yaml.safe_load((AGENT_DIR / "questions.yaml").read_text(encoding="utf-8"))["questions"]
for qid, q in qs.items():
    ref = list(q["required"]) if q["score"] != "clusters" else sorted(
        set().union(*(set(c["capas"]) | set(c.get("cause_any", [])[:1]) for c in q["clusters"])))
    s = score(q, ref)
    check(f"{qid}: reference answer scores 1.0", s["score"] == 1.0, s)
naive_q1 = ["URS-EBR-001", "URS-EBR-009", "URS-EMS-011", "URS-EMS-012", "URS-EMS-014", "URS-LIMS-002", "URS-LIMS-003", "URS-LIMS-004"]
check("q1: the flat-table answer scores below 1", score(qs["q1"], naive_q1)["score"] < 1, score(qs["q1"], naive_q1))
ids, src = extract_ids('Answer...\n```json\n{"answer_ids": ["fm-02", "FM-13"]}\n```')
check("json answer block parsed", ids == ["FM-02", "FM-13"] and src == "json", (ids, src))

print("\nAll checks passed." if ok else "\nSome checks failed.")
sys.exit(0 if ok else 1)
