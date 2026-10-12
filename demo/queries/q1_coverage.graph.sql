-- Q1. Which high-risk user requirements are NOT currently verified?
--
-- Hops: FailureMode(FRA) -ASSESSES-> URS -APPLIES_TO-> System <-PART_OF- Equipment
--       TestCase -VERIFIES-> URS | FS/CS -SATISFIES-> URS | DS -IMPLEMENTS-> FS -SATISFIES-> URS
--       TestExecution -EXECUTES-> TestCase, -PERFORMED_ON-> unit
--       ChangeControl -MODIFIES-> URS | child spec | unit
-- "Currently verified" is defined in semantic/validation.yaml
-- (definitions.currently_verified_requirement).
WITH
risk AS (       -- FRA rating per requirement
  SELECT kg_txt(fm) AS ri_id, kg_txt(req) AS req
  FROM cypher('cart_kg', $$
    MATCH (f:FailureMode)-[:ASSESSES]->(u:UserRequirement) RETURN f.id, u.id
  $$) AS (fm agtype, req agtype)
),
units AS (      -- every unit the requirement applies to
  SELECT DISTINCT kg_txt(req) AS req, kg_txt(unit) AS unit
  FROM cypher('cart_kg', $$
    MATCH (u:UserRequirement)-[:APPLIES_TO]->(s:System)
    OPTIONAL MATCH (e:Equipment)-[:PART_OF]->(s)
    RETURN u.id, coalesce(e.id, s.id)
  $$) AS (req agtype, unit agtype)
),
ver AS (        -- executions of any test case that verifies the URS directly or through FS/CS/DS
  SELECT DISTINCT kg_txt(req) AS req, kg_txt(tc) AS tc_id, kg_txt(x) AS exec_id, kg_txt(unit) AS unit
  FROM cypher('cart_kg', $$
    MATCH (tc:TestCase)-[:VERIFIES]->(u:UserRequirement)
    MATCH (x:TestExecution)-[:EXECUTES]->(tc), (x)-[:PERFORMED_ON]->(t)
    RETURN u.id, tc.id, x.id, t.id
    UNION
    MATCH (tc:TestCase)-[:VERIFIES]->(:ConfigurationSpec)-[:SATISFIES]->(u:UserRequirement)
    MATCH (x:TestExecution)-[:EXECUTES]->(tc), (x)-[:PERFORMED_ON]->(t)
    RETURN u.id, tc.id, x.id, t.id
    UNION
    MATCH (tc:TestCase)-[:VERIFIES]->(:FunctionalSpec)-[:SATISFIES]->(u:UserRequirement)
    MATCH (x:TestExecution)-[:EXECUTES]->(tc), (x)-[:PERFORMED_ON]->(t)
    RETURN u.id, tc.id, x.id, t.id
    UNION
    MATCH (tc:TestCase)-[:VERIFIES]->(:DesignSpec)-[:IMPLEMENTS]->(:FunctionalSpec)-[:SATISFIES]->(u:UserRequirement)
    MATCH (x:TestExecution)-[:EXECUTES]->(tc), (x)-[:PERFORMED_ON]->(t)
    RETURN u.id, tc.id, x.id, t.id
  $$) AS (req agtype, tc agtype, x agtype, unit agtype)
),
chg AS (        -- change controls touching the requirement, a child spec, or a unit
  SELECT DISTINCT kg_txt(req) AS req, kg_txt(unit) AS unit, kg_txt(cc) AS cc_no
  FROM cypher('cart_kg', $$
    MATCH (cc:ChangeControl)-[:MODIFIES]->(u:UserRequirement)
    RETURN u.id, null, cc.id
    UNION
    MATCH (cc:ChangeControl)-[:MODIFIES]->(:ConfigurationSpec)-[:SATISFIES]->(u:UserRequirement)
    RETURN u.id, null, cc.id
    UNION
    MATCH (cc:ChangeControl)-[:MODIFIES]->(:FunctionalSpec)-[:SATISFIES]->(u:UserRequirement)
    RETURN u.id, null, cc.id
    UNION
    MATCH (cc:ChangeControl)-[:MODIFIES]->(e:Equipment)-[:PART_OF]->(:System)<-[:APPLIES_TO]-(u:UserRequirement)
    RETURN u.id, e.id, cc.id
  $$) AS (req agtype, unit agtype, cc agtype)
),
latest AS (     -- latest execution per requirement / unit / test case
  SELECT DISTINCT ON (v.req, v.unit, v.tc_id) v.req, v.unit, v.tc_id, x.exec_dt, x.result, t.method
  FROM ver v JOIN pd.val_test_exec x ON x.exec_id = v.exec_id JOIN pd.val_test_case t ON t.tc_id = v.tc_id
  ORDER BY v.req, v.unit, v.tc_id, x.exec_dt DESC
),
stale_after AS (
  SELECT u.req, u.unit, max(c.impl_dt) AS impl_dt,
         string_agg(DISTINCT c.cc_no, ', ') AS cc_nos
  FROM units u JOIN chg g ON g.req = u.req AND (g.unit IS NULL OR g.unit = u.unit)
  JOIN pd.qms_change_control c ON c.cc_no = g.cc_no AND c.impl_dt IS NOT NULL
  GROUP BY u.req, u.unit
),
per_unit AS (
  SELECT u.req, u.unit, r.risk_class,
    count(l.tc_id) AS n_tests,
    bool_or(l.result = 'PASS'
            AND (s.impl_dt IS NULL OR l.exec_dt >= s.impl_dt)
            AND (r.risk_class <> 'HIGH' OR l.method = 'SCRIPTED')) AS ok,
    bool_or(l.result = 'FAIL') AS any_fail,
    bool_and(l.result IS NULL OR l.result <> 'PASS' OR s.impl_dt IS NULL OR l.exec_dt >= s.impl_dt) AS none_stale,
    max(s.cc_nos) AS cc_nos
  FROM units u
  JOIN risk k ON k.req = u.req
  JOIN pd.val_risk_item r ON r.ri_id = k.ri_id
  LEFT JOIN latest l ON l.req = u.req AND l.unit = u.unit
  LEFT JOIN stale_after s ON s.req = u.req AND s.unit = u.unit
  GROUP BY u.req, u.unit, r.risk_class
)
SELECT p.req AS requirement, i.req_category,
       string_agg(p.unit, ', ' ORDER BY p.unit) AS units_not_verified,
       CASE WHEN max(p.n_tests) = 0 THEN 'No verifying test case (direct or via FS/CS/DS)'
            WHEN bool_or(p.any_fail) THEN 'Latest execution FAILED, not re-executed'
            WHEN NOT bool_and(p.none_stale) THEN 'Verification predates ' || max(p.cc_nos)
            ELSE 'Other' END AS reason,
       left(i.item_text, 70) AS requirement_text
FROM per_unit p JOIN pd.val_spec_item i ON i.item_id = p.req
WHERE p.risk_class = 'HIGH' AND NOT coalesce(p.ok, false)
GROUP BY p.req, i.req_category, i.item_text
ORDER BY p.req;
