-- Q5. Which high-criticality FMEA risks are controlled by equipment
--     requirements that have OQ test coverage but no PQ, where PQ is expected?
--
-- Hops: FailureMode -MITIGATED_BY-> URS -APPLIES_TO-> System(EQUIPMENT)
--       URS <-VERIFIES(-via FS)- TestCase -PART_OF-> Protocol(ptype)
-- "High criticality" = approved risk_class, not an RPN cut-off.
-- "PQ expected" = req_category PERFORMANCE (semantic/validation.yaml).
WITH
ctl AS (
  SELECT DISTINCT kg_txt(f) AS ri_id, kg_txt(u) AS req, kg_txt(s) AS sys_id
  FROM cypher('cart_kg', $$
    MATCH (f:FailureMode)-[:MITIGATED_BY]->(u:UserRequirement)-[:APPLIES_TO]->(s:System {sys_class: 'EQUIPMENT'})
    WHERE u.req_category = 'PERFORMANCE'
    RETURN f.id, u.id, s.id
  $$) AS (f agtype, u agtype, s agtype)
),
cov AS (
  SELECT DISTINCT kg_txt(u) AS req, kg_txt(pt) AS ptype, kg_txt(tc) AS tc_id
  FROM cypher('cart_kg', $$
    MATCH (tc:TestCase)-[:VERIFIES]->(u:UserRequirement), (tc)-[:PART_OF]->(p:Protocol)
    RETURN u.id, p.ptype, tc.id
    UNION
    MATCH (tc:TestCase)-[:VERIFIES]->(:FunctionalSpec)-[:SATISFIES]->(u:UserRequirement), (tc)-[:PART_OF]->(p:Protocol)
    RETURN u.id, p.ptype, tc.id
  $$) AS (u agtype, pt agtype, tc agtype)
)
SELECT c.ri_id, r.process_step, r.failure_mode, r.sev, r.rpn, c.req, c.sys_id,
       string_agg(DISTINCT v.tc_id, ', ') FILTER (WHERE v.ptype = 'OQ') AS oq_tests,
       r.current_controls AS fmea_says
FROM ctl c
JOIN pd.val_risk_item r ON r.ri_id = c.ri_id AND r.risk_class = 'HIGH'
LEFT JOIN cov v ON v.req = c.req
GROUP BY c.ri_id, r.process_step, r.failure_mode, r.sev, r.rpn, c.req, c.sys_id, r.current_controls
HAVING bool_or(v.ptype = 'OQ') AND NOT coalesce(bool_or(v.ptype = 'PQ'), false)
ORDER BY c.ri_id;
