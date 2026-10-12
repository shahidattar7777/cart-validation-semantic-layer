"""Agent comparison: Claude with and without the semantic layer.

Two conditions, same model, same tool (read-only SQL), same questions:
  raw       the agent sees the raw table/column catalog of schema pd only
            (no graph, no YAML). This is the "flat tables" agent.
  semantic  the agent also gets semantic/*.yaml and can traverse the AGE
            graph cart_kg through cypher() inside the same SQL tool.

    set ANTHROPIC_API_KEY=...                 (PowerShell: $env:ANTHROPIC_API_KEY="...")
    python agent/run_eval.py                  # haiku + sonnet, raw + semantic, q1-q6, 1 run each
    python agent/run_eval.py --runs 3 --workers 6
    python agent/run_eval.py --models sonnet --conditions semantic --questions q3

Results go to agent/results/<timestamp>/ (report.md, runs.jsonl, transcripts/).
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from pathlib import Path

import psycopg
import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.db import _load_env, connect  # noqa: E402

AGENT_DIR = ROOT / "agent"

MODELS = {"haiku": "claude-haiku-5-5", "sonnet": "claude-sonnet-5-5"}
# USD per million tokens (platform.claude.com/docs/en/about-claude/pricing, Oct 2026).
# Haiku 5.5 has a higher tier for prompts over 100k tokens.
PRICES = {
    "claude-haiku-5-5": [(100_000, dict(inp=0.10, out=0.50, cw=0.125, cr=0.01)),
                         (None, dict(inp=0.50, out=2.50, cw=0.625, cr=0.05))],
    "claude-sonnet-5-5": [(None, dict(inp=2.00, out=10.00, cw=2.50, cr=0.10))],
}

BLOCK_RAW = re.compile(r"cypher\s*\(|ag_catalog|cart_kg|ag_graph|ag_label", re.I)
MAX_ROWS = 200
MAX_CHARS = 15_000

ID_RE = re.compile(
    r"\b(?:URS|FS|CS|DS)-[A-Z]+-\d{2,3}\b|\bFM-\d{2}\b|\bFRA-\d{3}\b|\bCAPA-\d{2}-\d{3}\b|\bCC-\d{2}-\d{3}\b"
    r"|\bDEV-\d{2}-\d{3}\b|\b(?:PPQ|ENG|PD)26-\d{2,3}\b|\bLV\d{2}-\d{3}\b|\bSOP-[A-Z]+-\d{3}\b"
    r"|\bAMV?-[A-Z0-9]+(?:-[A-Z0-9]+)*\b|\bPPQ-\d{3}\b|\b(?:IQ|OQ|PQ)-[A-Z]+-\d{2}\b|\bTC-[A-Z]+-[A-Z]+-\d{2}\b"
    r"|\bRA-[A-Z]+-[A-Z0-9]+\b|\bSYS-[A-Z]+\b|\b(?:INC|FRZ|PRDG|LOVO|CRF)-[0-9A-Z-]+\b")

SYSTEM_BASE = """You are a data analyst supporting a CAR-T cell therapy process development, validation and quality team. You answer questions by querying a PostgreSQL database with the run_sql tool (read-only). Investigate until you are confident, check your assumptions against the data, and do not guess.

When you are done, write your answer in prose, then end with a fenced json block:
```json
{{"answer_ids": ["..."]}}
```
In answer_ids, list the IDs of the records that directly answer the question (for example requirement, risk, CAPA, change control, batch, lot or document IDs), not every record you looked at.

## Database catalog (schema pd)
{schema}
"""

SYSTEM_SEMANTIC = """
## Semantic layer
The team maintains a semantic layer, given below as YAML. Use its vocabulary, aliases, definitions and table mappings. Where it defines a concept (for example how "verified" or "high criticality" is decided), use that definition rather than your own.

## Knowledge graph
The same database holds an Apache AGE graph named cart_kg, built from the semantic layer. Node labels are the `entities`; edge types are the `relationships` (direction from -> to). Nodes carry only `id` plus classification codes (ptype, record_type, criticality, req_category, sys_class, run_type, ra_type). EVALUATES edges carry crit_no. All values, text, dates, scores and results stay in the pd tables: traverse the graph for IDs, then join to pd tables.

Syntax, inside run_sql:
  SELECT kg_txt(a) AS x, kg_txt(b) AS y
  FROM cypher('cart_kg', $$ MATCH (a:Label)-[:EDGE]->(b:Other) WHERE a.id = 'X' RETURN a.id, b.id $$) AS (a agtype, b agtype);
- kg_txt(agtype) converts a graph value to text for joins and filters.
- The AS (...) column list must match the RETURN list.
- One label per node. For alternative labels or edge types, use UNION inside the cypher text. Variable-length paths such as -[*1..3]-> work.
- Do anti-joins (NOT EXISTS) and date logic in SQL after the cypher() call.

```yaml
{process_yaml}
```

```yaml
{validation_yaml}
```
"""

_print_lock = threading.Lock()


def log(msg: str) -> None:
    with _print_lock:
        print(msg, flush=True)


# --------------------------------------------------------------------------- database tool
def raw_connect():
    _load_env()
    return psycopg.connect(host=os.environ.get("PGHOST", "localhost"), port=int(os.environ.get("PGPORT", "5455")),
                           dbname=os.environ.get("PGDATABASE", "cartpd"), user="cart_raw", password="cart_raw")


def format_rows(cols, rows, more: bool) -> str:
    def cell(v):
        s = "NULL" if v is None else str(v)
        return s if len(s) <= 300 else s[:297] + "..."
    lines = [" | ".join(cols)] + [" | ".join(cell(v) for v in r) for r in rows]
    out = "\n".join(lines)
    note = f"\n({len(rows)} rows{', truncated at ' + str(MAX_ROWS) if more else ''})"
    if len(out) > MAX_CHARS:
        out = out[:MAX_CHARS] + "\n... output truncated"
    return out + note


def run_sql(condition: str, query: str) -> tuple[str, bool]:
    if condition == "raw" and BLOCK_RAW.search(query):
        return "ERROR: the graph is not available in this environment.", True
    try:
        conn = raw_connect() if condition == "raw" else connect()
        with conn:
            with conn.cursor() as cur:
                if condition == "semantic":
                    cur.execute("SET TRANSACTION READ ONLY")
                    cur.execute("SET LOCAL statement_timeout = '30s'")
                    cur.execute("LOAD 'age'")
                    cur.execute('SET LOCAL search_path = ag_catalog, "$user", public, pd')
                cur.execute(query)
                if cur.description is None:
                    return "OK (no rows returned)", False
                cols = [d.name for d in cur.description]
                rows = cur.fetchmany(MAX_ROWS + 1)
                more = len(rows) > MAX_ROWS
                return format_rows(cols, rows[:MAX_ROWS], more), False
    except Exception as e:  # noqa: BLE001 - the agent should see any database error
        return f"ERROR: {type(e).__name__}: {str(e).strip()[:1500]}", True


def ensure_raw_role() -> None:
    with connect() as conn, conn.cursor() as cur:
        cur.execute((AGENT_DIR / "setup_roles.sql").read_text(encoding="utf-8"))
        conn.commit()


def catalog_text() -> str:
    with connect() as conn, conn.cursor() as cur:
        cur.execute("""SELECT table_name, string_agg(column_name || ' ' || data_type, ', ' ORDER BY ordinal_position)
                       FROM information_schema.columns WHERE table_schema = 'pd'
                       GROUP BY table_name ORDER BY table_name""")
        return "\n".join(f"pd.{t}({c})" for t, c in cur.fetchall())


def build_prompts() -> dict[str, str]:
    base = SYSTEM_BASE.format(schema=catalog_text())
    sem = base + SYSTEM_SEMANTIC.format(
        process_yaml=(ROOT / "semantic" / "process.yaml").read_text(encoding="utf-8"),
        validation_yaml=(ROOT / "semantic" / "validation.yaml").read_text(encoding="utf-8"))
    return {"raw": base, "semantic": sem}


def tool_def(condition: str) -> dict:
    desc = f"Run one read-only SQL statement on PostgreSQL and return up to {MAX_ROWS} rows."
    if condition == "semantic":
        desc += " The statement may call cypher('cart_kg', ...) to traverse the knowledge graph."
    return {"name": "run_sql", "description": desc,
            "input_schema": {"type": "object", "properties": {"query": {"type": "string", "description": "SQL statement"}},
                             "required": ["query"]}}


# --------------------------------------------------------------------------- scoring
def extract_ids(text: str) -> tuple[list[str], str]:
    blocks = re.findall(r"```json\s*(\{.*?\})\s*```", text, re.S)
    for b in reversed(blocks):
        try:
            ids = json.loads(b).get("answer_ids")
            if isinstance(ids, list):
                return [str(i).strip().upper() for i in ids], "json"
        except json.JSONDecodeError:
            pass
    return sorted(set(ID_RE.findall(text.upper()))), "regex-fallback"


def score_clusters(q: dict, ids: list[str]) -> dict:
    got = set(ids)
    found, missed = [], []
    for c in q["clusters"]:
        ok = set(c["capas"]) <= got and (not c.get("cause_any") or got & set(c["cause_any"]))
        (found if ok else missed).append(c["label"])
    in_any = set().union(*(set(c["capas"]) for c in q["clusters"]))
    capas = {i for i in got if i.startswith("CAPA-")}
    recall = len(found) / len(q["clusters"])
    precision = len(capas & in_any) / len(capas) if capas else 0.0
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    return dict(score=round(f1, 3), recall=round(recall, 3), precision=round(precision, 3), missed=missed,
                extra=sorted(capas - in_any))


def score(q: dict, ids: list[str]) -> dict:
    if q["score"] == "clusters":
        return score_clusters(q, ids)
    req, opt = set(q["required"]), set(q.get("optional", []))
    prefixes = q.get("prefixes")
    scored = {i for i in ids if not prefixes or any(i.startswith(p) for p in prefixes)}
    hit = scored & req
    recall = len(hit) / len(req)
    precision = (len(scored & (req | opt)) / len(scored)) if scored else 0.0
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    return dict(score=round(recall if q["score"] == "recall" else f1, 3), recall=round(recall, 3),
                precision=round(precision, 3), missed=sorted(req - scored),
                extra=sorted(scored - req - opt) if q["score"] == "f1" else [])


# --------------------------------------------------------------------------- agent loop
def call_cost(model: str, u) -> float:
    total_in = (u.input_tokens or 0) + (u.cache_creation_input_tokens or 0) + (u.cache_read_input_tokens or 0)
    for limit, p in PRICES[model]:
        if limit is None or total_in <= limit:
            break
    return ((u.input_tokens or 0) * p["inp"] + (u.output_tokens or 0) * p["out"]
            + (u.cache_creation_input_tokens or 0) * p["cw"] + (u.cache_read_input_tokens or 0) * p["cr"]) / 1e6


def run_one(client, prompts, model_key, condition, qid, q, run_idx, max_turns, max_tokens) -> dict:
    model = MODELS[model_key]
    system = prompts[condition]
    tools = [tool_def(condition)]
    messages = [{"role": "user", "content": q["question"].strip()}]
    usage = dict(input=0, output=0, cache_write=0, cache_read=0)
    cost, n_calls, n_err, turns = 0.0, 0, 0, 0
    t0 = time.time()
    final_text, stop, nudged = "", "", False
    while True:
        force_final = turns >= max_turns
        kwargs = dict(model=model, max_tokens=max_tokens, system=system, tools=tools, messages=messages,
                      cache_control={"type": "ephemeral"})
        if force_final:
            kwargs["tool_choice"] = {"type": "none"}
        resp = client.messages.create(**kwargs)
        if resp.stop_reason == "max_tokens" and not any(b.type in ("text", "tool_use") for b in resp.content):
            # thinking used the whole output budget before any answer: retry once with more room
            kwargs["max_tokens"] = max_tokens * 2
            usage["output"] += resp.usage.output_tokens or 0
            cost += call_cost(model, resp.usage)
            resp = client.messages.create(**kwargs)
        u = resp.usage
        usage["input"] += u.input_tokens or 0
        usage["output"] += u.output_tokens or 0
        usage["cache_write"] += u.cache_creation_input_tokens or 0
        usage["cache_read"] += u.cache_read_input_tokens or 0
        cost += call_cost(model, u)
        messages.append({"role": "assistant", "content": [b.model_dump(exclude_none=True) for b in resp.content]})
        stop = resp.stop_reason
        tool_uses = [b for b in resp.content if b.type == "tool_use"]
        if stop != "tool_use" or not tool_uses or force_final:
            final_text = "\n".join(b.text for b in resp.content if b.type == "text")
            if "answer_ids" not in final_text and not nudged:
                nudged = True
                messages.append({"role": "user", "content": "Please give your final answer now, ending with the "
                                                            "json block of answer_ids."})
                turns = max_turns  # forces a final, tool-free answer
                continue
            break
        turns += 1
        results = []
        for tu in tool_uses:
            n_calls += 1
            out, is_err = run_sql(condition, tu.input.get("query", ""))
            n_err += is_err
            results.append({"type": "tool_result", "tool_use_id": tu.id, "content": out, "is_error": is_err})
        if turns >= max_turns:
            results.append({"type": "text", "text": "Tool-call limit reached. Give your final answer now, "
                                                     "with the json block."})
        messages.append({"role": "user", "content": results})
    ids, id_source = extract_ids(final_text)
    sc = score(q, ids)
    return dict(model=model_key, condition=condition, qid=qid, run=run_idx, **sc, answer_ids=ids,
                id_source=id_source, tool_calls=n_calls, sql_errors=n_err, turns=turns, hit_turn_limit=turns >= max_turns,
                stop_reason=stop, seconds=round(time.time() - t0, 1), cost_usd=round(cost, 4), **{f"tok_{k}": v for k, v in usage.items()},
                final_answer=final_text, transcript=messages)


# --------------------------------------------------------------------------- report
def mean(xs):
    xs = list(xs)
    return sum(xs) / len(xs) if xs else 0.0


def write_report(out_dir: Path, rows: list[dict], questions: dict, args, name: str = "report.md") -> None:
    combos = [(m, c) for m in args.models for c in args.conditions]
    L = [f"# Agent comparison: with vs. without the semantic layer", "",
         f"Run {out_dir.name}. Models: {', '.join(MODELS[m] for m in args.models)}. Runs per cell: {args.runs}. "
         f"Max tool rounds: {args.max_turns}.", "",
         "Score: F1 against the answer key (recall only for the open-ended Q2 and Q4; Q3 scored by cause clusters). "
         "1.0 = fully correct. Mean score = average of the per-question means, so questions with more runs don't "
         "weigh more. Runs whose output was cut off before any answer (a harness bug) are excluded.", "",
         "## Summary", "",
         "| Model | Condition | Mean score | Fully correct | Tool calls | SQL errors | Seconds | Cost (USD) |",
         "|---|---|---|---|---|---|---|---|"]
    for m, c in combos:
        rs = [r for r in rows if r["model"] == m and r["condition"] == c and "error" not in r]
        if not rs:
            continue
        q_means = [mean(r["score"] for r in rs if r["qid"] == q) for q in questions if any(r["qid"] == q for r in rs)]
        L.append(f"| {m} | {c} | {mean(q_means):.2f} | {sum(r['score'] == 1 for r in rs)}/{len(rs)} "
                 f"| {mean(r['tool_calls'] for r in rs):.1f} | {mean(r['sql_errors'] for r in rs):.1f} "
                 f"| {mean(r['seconds'] for r in rs):.0f} | {sum(r['cost_usd'] for r in rs):.2f} |")
    L += ["", "## Score by question", "", "| Question | " + " | ".join(f"{m} {c}" for m, c in combos) + " |",
          "|---|" + "---|" * len(combos)]
    for qid, q in questions.items():
        cells = []
        for m, c in combos:
            rs = [r for r in rows if r["model"] == m and r["condition"] == c and r["qid"] == qid and "error" not in r]
            cells.append(f"{mean(r['score'] for r in rs):.2f}" if rs else "-")
        L.append(f"| {qid.upper()} {q['title']} | " + " | ".join(cells) + " |")
    L += ["", "## What each run missed", "", "| Model | Condition | Q | Run | Score | Missed (required) | Wrong extras |",
          "|---|---|---|---|---|---|---|"]
    for r in sorted(rows, key=lambda r: (r["qid"], r["model"], r["condition"], r["run"])):
        if "error" in r:
            L.append(f"| {r['model']} | {r['condition']} | {r['qid']} | {r['run']} | ERROR | {r['error'][:80]} | |")
            continue
        L.append(f"| {r['model']} | {r['condition']} | {r['qid']} | {r['run']} | {r['score']:.2f} | "
                 f"{', '.join(r['missed']) or '-'} | {', '.join(r['extra']) or '-'} |")
    L += ["", "Transcripts: `transcripts/<model>_<condition>_<question>_r<run>.json`. "
          "Each has the full conversation, every SQL statement and its result.", ""]
    (out_dir / name).write_text("\n".join(L), encoding="utf-8")


# --------------------------------------------------------------------------- main
def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--setup", action="store_true", help="create the read-only role used by the raw condition")
    ap.add_argument("--models", nargs="+", default=["haiku", "sonnet"], choices=list(MODELS))
    ap.add_argument("--conditions", nargs="+", default=["raw", "semantic"], choices=["raw", "semantic"])
    ap.add_argument("--questions", nargs="+", default=None)
    ap.add_argument("--runs", type=int, default=1)
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--max-turns", type=int, default=25)
    ap.add_argument("--max-tokens", type=int, default=32000)
    ap.add_argument("--rescore", metavar="RESULTS_DIR", nargs="+",
                    help="re-score earlier runs against the current answer key and merge them (no API calls)")
    args = ap.parse_args()

    if args.rescore:
        dirs = [Path(d) for d in args.rescore]
        qs_all = yaml.safe_load((AGENT_DIR / "questions.yaml").read_text(encoding="utf-8"))["questions"]
        rows, counter = [], {}
        for d in dirs:
            for l in open(d / "runs.jsonl", encoding="utf-8"):
                r = json.loads(l)
                key = (r["model"], r["condition"], r["qid"])
                counter[key] = counter.get(key, 0) + 1
                r["run"], r["source"] = counter[key], d.name
                if "error" not in r and not (r.get("final_answer") or "").strip():
                    r["error"] = f"harness: no answer text (stop_reason={r.get('stop_reason')}), excluded"
                if "error" not in r:
                    r.update(score(qs_all[r["qid"]], r["answer_ids"]))
                rows.append(r)
        rdir = dirs[0] if len(dirs) == 1 else AGENT_DIR / "results" / "combined"
        rdir.mkdir(parents=True, exist_ok=True)
        args.models = [m for m in MODELS if any(r["model"] == m for r in rows)]
        args.conditions = [c for c in ("raw", "semantic") if any(r["condition"] == c for r in rows)]
        args.runs = max(r["run"] for r in rows)
        used = {k: v for k, v in qs_all.items() if any(r["qid"] == k for r in rows)}
        write_report(rdir, rows, used, args, name="report_rescored.md")
        print(f"Wrote {rdir / 'report_rescored.md'}")
        return

    ensure_raw_role()   # idempotent; reloading the data drops schema pd and its grants
    if args.setup:
        print("Role cart_raw ready (read-only, schema pd only).")
        return

    import anthropic  # imported here so --setup works without the SDK
    _load_env()
    if not os.environ.get("ANTHROPIC_API_KEY"):
        sys.exit("Set ANTHROPIC_API_KEY (environment or .env) first.")
    client = anthropic.Anthropic(max_retries=6)

    all_q = yaml.safe_load((AGENT_DIR / "questions.yaml").read_text(encoding="utf-8"))["questions"]
    questions = {k: v for k, v in all_q.items() if not args.questions or k in args.questions}
    prompts = build_prompts()
    out_dir = AGENT_DIR / "results" / datetime.now().strftime("%Y%m%d-%H%M%S")
    (out_dir / "transcripts").mkdir(parents=True, exist_ok=True)

    jobs = [(m, c, qid, r) for m in args.models for c in args.conditions for qid in questions for r in range(1, args.runs + 1)]
    log(f"{len(jobs)} runs -> {out_dir}")
    rows = []
    with ThreadPoolExecutor(max_workers=args.workers) as ex:
        futs = {ex.submit(run_one, client, prompts, m, c, qid, questions[qid], r, args.max_turns, args.max_tokens): (m, c, qid, r)
                for m, c, qid, r in jobs}
        for f in as_completed(futs):
            m, c, qid, r = futs[f]
            try:
                res = f.result()
            except Exception as e:  # noqa: BLE001
                res = dict(model=m, condition=c, qid=qid, run=r, error=f"{type(e).__name__}: {e}")
                log(f"  {m:6s} {c:8s} {qid} r{r}  ERROR {res['error'][:120]}")
                rows.append(res)
                continue
            (out_dir / "transcripts" / f"{m}_{c}_{qid}_r{r}.json").write_text(
                json.dumps(res, indent=1, default=str), encoding="utf-8")
            res.pop("transcript")
            rows.append(res)
            log(f"  {m:6s} {c:8s} {qid} r{r}  score {res['score']:.2f}  calls {res['tool_calls']:2d}  "
                f"${res['cost_usd']:.3f}  missed {','.join(res['missed']) or '-'}")
    with open(out_dir / "runs.jsonl", "w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, default=str) + "\n")
    write_report(out_dir, rows, questions, args)
    log(f"\nReport: {out_dir / 'report.md'}  (total ${sum(r.get('cost_usd', 0) for r in rows):.2f})")


if __name__ == "__main__":
    main()
