"""Build the thin knowledge graph in Apache AGE from the semantic layer YAML.

    python graph/build_graph.py            # drops and rebuilds graph 'cart_kg'

Reads semantic/*.yaml. Every vertex gets an `id` (plus a classification
code where the YAML asks for one); every edge comes from a `relationships`
entry. No measurements, scores, text or statuses are copied into the graph:
queries traverse the graph for identities, then join back to the pd tables.

Free-text columns (FMEA step / parameter / CQA, PPQ criteria, SOP scope)
are resolved to ontology nodes through the YAML aliases. Anything that
does not resolve is reported, which doubles as a coverage check on the
semantic layer itself.
"""
from __future__ import annotations

import re
import sys
from collections import defaultdict
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.db import connect  # noqa: E402

GRAPH = "cart_kg"
CHUNK = 400


def load_semantic() -> dict:
    merged: dict = {"entities": {}, "relationships": {}}
    for name in ["process.yaml", "validation.yaml"]:
        doc = yaml.safe_load((ROOT / "semantic" / name).read_text(encoding="utf-8"))
        for k, v in doc.items():
            if k in ("entities", "relationships"):
                merged[k].update(v)
            elif isinstance(v, dict):
                merged.setdefault(k, {}).update(v)
            elif isinstance(v, list):
                merged.setdefault(k, []).extend(v)
            else:
                merged[k] = v
    return merged


def norm(s: str) -> str:
    return re.sub(r"\s+", " ", str(s).strip().lower())


def lit(v) -> str:
    if v is None:
        return "null"
    if isinstance(v, bool):
        return "true" if v else "false"
    if isinstance(v, (int, float)):
        return repr(v)
    s = str(v).replace("\\", "\\\\").replace("'", "\\'")
    return f"'{s}'"


def cypher(cur, query: str, cols: str = "a agtype"):
    assert "$$" not in query
    cur.execute(f"SELECT * FROM cypher('{GRAPH}', $$ {query} $$) AS ({cols})")
    return cur.fetchall()


def main() -> None:
    sem = load_semantic()

    # ---- alias indexes for ontology nodes
    alias_idx: dict[str, dict[str, str]] = {}
    for label, section in [("UnitOperation", "unit_operations"), ("Parameter", "parameters"),
                           ("QualityAttribute", "quality_attributes")]:
        idx = {}
        for key, spec in sem[section].items():
            for term in [key, spec.get("name"), *spec.get("aliases", [])]:
                if term:
                    t = norm(term)
                    if t in idx and idx[t] != key:
                        raise SystemExit(f"Alias collision in {section}: '{term}' -> {idx[t]} and {key}")
                    idx[t] = key
        alias_idx[label] = idx
    test_code_idx = {spec["test_code"]: key for key, spec in sem["quality_attributes"].items() if spec.get("test_code")}
    not_params = {norm(x) for x in sem.get("not_parameters", [])}

    def resolve(text, labels):
        t = norm(text)
        for lb in labels:
            if t in alias_idx[lb]:
                return lb, alias_idx[lb][t]
        return None, None

    with connect() as conn, conn.cursor() as cur:
        cur.execute("LOAD 'age'")
        cur.execute('SET search_path = ag_catalog, "$user", public')
        cur.execute("SELECT count(*) FROM ag_catalog.ag_graph WHERE name = %s", [GRAPH])
        if cur.fetchone()[0]:
            cur.execute(f"SELECT drop_graph('{GRAPH}', true)")
        cur.execute(f"SELECT create_graph('{GRAPH}')")

        # ------------------------------------------------------------ vertices
        node_ids: dict[str, set] = defaultdict(set)
        for label, spec in sem["entities"].items():
            rows = []
            if "from_yaml" in spec:
                for key, item in sem[spec["from_yaml"]].items():
                    props = {"id": key, "name": item.get("name", key)}
                    if item.get("criticality"):
                        props["criticality"] = item["criticality"]
                    rows.append(props)
            else:
                cur.execute(spec["source"])
                names = [d.name for d in cur.description]
                rows = [dict(zip(names, r)) for r in cur.fetchall()]
            cur.execute(f"SELECT create_vlabel('{GRAPH}', '{label}')")
            for i in range(0, len(rows), CHUNK):
                items = ", ".join("{" + ", ".join(f"{k}: {lit(v)}" for k, v in r.items() if v is not None) + "}"
                                  for r in rows[i:i + CHUNK])
                cypher(cur, f"UNWIND [{items}] AS r CREATE (n:{label}) SET n = r")
            cur.execute(f'CREATE INDEX ON {GRAPH}."{label}" USING gin (properties)')
            node_ids[label] = {r["id"] for r in rows}
            print(f"  vertex {label:20s} {len(rows):>6,d}")

        # ------------------------------------------------------------ edges
        warnings = []

        def edges_for(etype, spec):
            out = []  # (from_label, from_id, to_label, to_id, props)
            if "from_yaml" in spec:
                section, field = spec["from_yaml"].split(".*.")
                for key, item in sem[section].items():
                    vals = item.get(field)
                    if vals is None:
                        continue
                    for v in (vals if isinstance(vals, list) else [vals]):
                        if spec.get("reverse"):
                            out.append((spec["from"], v, spec["to"], key, ()))
                        else:
                            out.append((spec["from"], key, spec["to"], v, ()))
                return out
            cur.execute(spec["source"])
            names = [d.name for d in cur.description]
            for r in cur.fetchall():
                row = dict(zip(names, r))
                vals = list(r)
                f_id, t_id = vals[0], vals[1]
                f_lb = row.get("from_label", spec.get("from"))
                t_lb = row.get("to_label", spec.get("to"))
                if spec.get("resolve_from") == "test_code":
                    if f_id not in test_code_idx:
                        warnings.append(f"{etype}: no quality attribute for test_code {f_id}")
                        continue
                    f_id, f_lb = test_code_idx[f_id], "QualityAttribute"
                if spec.get("resolve_to"):
                    lb, key = resolve(t_id, spec["resolve_to"])
                    if key is None:
                        if not (etype == "INVOLVES" and norm(t_id) in not_params):
                            warnings.append(f"{etype}: '{t_id}' (from {f_id}) not found in {spec['resolve_to']} aliases")
                        continue
                    t_lb, t_id = lb, key
                props = tuple((k, v) for k, v in row.items()
                              if k not in (names[0], names[1], "from_label", "to_label") and v is not None)
                out.append((f_lb, f_id, t_lb, t_id, props))
            return out

        total = 0
        for etype, spec in sem["relationships"].items():
            cur.execute(f"SELECT create_elabel('{GRAPH}', '{etype}')")
            variants = spec.get("variants", [spec])
            all_edges = []
            for v in variants:
                all_edges += edges_for(etype, v)
            groups = defaultdict(list)
            for f_lb, f_id, t_lb, t_id, props in set(all_edges):
                if f_id not in node_ids[f_lb] or t_id not in node_ids[t_lb]:
                    warnings.append(f"{etype}: missing endpoint {f_lb}:{f_id} -> {t_lb}:{t_id}")
                    continue
                groups[(f_lb, t_lb, tuple(k for k, _ in props))].append((f_id, t_id, props))
            n = 0
            for (f_lb, t_lb, pkeys), pairs in groups.items():
                eprops = ("{" + ", ".join(f"{k}: r.{k}" for k in pkeys) + "}") if pkeys else ""
                for i in range(0, len(pairs), CHUNK):
                    items = ", ".join(
                        "{" + ", ".join([f"f: {lit(a)}", f"t: {lit(b)}"] + [f"{k}: {lit(v)}" for k, v in pr]) + "}"
                        for a, b, pr in pairs[i:i + CHUNK])
                    res = cypher(cur, f"UNWIND [{items}] AS r MATCH (a:{f_lb} {{id: r.f}}), (b:{t_lb} {{id: r.t}}) "
                                      f"CREATE (a)-[e:{etype} {eprops}]->(b) RETURN count(e)")
                    n += int(str(res[0][0]))
            total += n
            print(f"  edge   {etype:20s} {n:>6,d}")
        # Helper used by the demo queries to turn agtype ids into text
        cur.execute("""CREATE OR REPLACE FUNCTION public.kg_txt(a ag_catalog.agtype) RETURNS text
                       LANGUAGE sql IMMUTABLE AS $f$ SELECT btrim(a::text, '"') $f$""")
        conn.commit()

    print(f"Graph '{GRAPH}' built: {sum(len(v) for v in node_ids.values()):,} vertices, {total:,} edges.")
    if warnings:
        print(f"\n{len(warnings)} semantic-layer warnings (unresolved terms or missing endpoints):")
        for w in warnings:
            print("  -", w)


if __name__ == "__main__":
    main()
