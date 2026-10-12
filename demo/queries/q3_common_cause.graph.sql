-- Q3. Which CAPAs, raised from different deviations, trace back to the
--     same upstream cause, even though the recorded root causes differ?
--
-- Hops: CAPA <-RESULTED_IN- Deviation -AFFECTS-> Equipment -(PART_OF|MONITORS)- System
--       <-APPLIES_TO- URS <-SATISFIES- ConfigurationSpec <-MODIFIES- ChangeControl
-- SQL then keeps change controls implemented BEFORE both events and adds
-- the evidence: alarm acknowledgement times before vs after the change,
-- and when the affected requirement was last tested.
WITH
pairs AS (
  SELECT DISTINCT kg_txt(d1) AS dev_1, kg_txt(c1) AS capa_1, kg_txt(e1) AS equip_1,
                  kg_txt(d2) AS dev_2, kg_txt(c2) AS capa_2, kg_txt(e2) AS equip_2,
                  kg_txt(s)  AS shared_system, kg_txt(cc) AS change_control
  FROM cypher('cart_kg', $$
    MATCH (c1:CAPA)<-[:RESULTED_IN]-(d1:Deviation)-[:AFFECTS]->(e1:Equipment)-[]-(s:System),
          (c2:CAPA)<-[:RESULTED_IN]-(d2:Deviation)-[:AFFECTS]->(e2:Equipment)-[]-(s)
    WHERE d1.id < d2.id
    MATCH (cc:ChangeControl)-[:MODIFIES]->(:ConfigurationSpec)-[:SATISFIES]->(:UserRequirement)-[:APPLIES_TO]->(s)
    RETURN d1.id, c1.id, e1.id, d2.id, c2.id, e2.id, s.id, cc.id
  $$) AS (d1 agtype, c1 agtype, e1 agtype, d2 agtype, c2 agtype, e2 agtype, s agtype, cc agtype)
),
req AS (        -- requirement whose configuration the change touched
  SELECT kg_txt(cc) AS change_control, kg_txt(u) AS req, kg_txt(tc) AS tc_id
  FROM cypher('cart_kg', $$
    MATCH (cc:ChangeControl)-[:MODIFIES]->(:ConfigurationSpec)-[:SATISFIES]->(u:UserRequirement)
    OPTIONAL MATCH (tc:TestCase)-[:VERIFIES]->(:ConfigurationSpec)-[:SATISFIES]->(u)
    RETURN cc.id, u.id, tc.id
  $$) AS (cc agtype, u agtype, tc agtype)
),
ack AS (        -- after-hours alarm acknowledgement time, before vs after each change
  SELECT c.cc_no,
         round(avg(EXTRACT(epoch FROM e.ack_ts - e.start_ts) / 60) FILTER (WHERE e.start_ts <  c.impl_dt)) AS ack_min_before,
         round(avg(EXTRACT(epoch FROM e.ack_ts - e.start_ts) / 60) FILTER (WHERE e.start_ts >= c.impl_dt)) AS ack_min_after
  FROM pd.qms_change_control c
  JOIN pd.equipment_event e ON e.event_type = 'ALARM'
   AND (EXTRACT(hour FROM e.start_ts) NOT BETWEEN 7 AND 18 OR EXTRACT(isodow FROM e.start_ts) > 5)
  GROUP BY c.cc_no
)
SELECT p.capa_1 || ' / ' || p.capa_2 AS capas,
       p.dev_1 || ' (' || d1.rc_category || ')' AS deviation_1,
       p.dev_2 || ' (' || d2.rc_category || ')' AS deviation_2,
       p.equip_1 || ', ' || p.equip_2 AS equipment,
       p.shared_system, p.change_control, cc.impl_dt AS cc_implemented,
       r.req AS requirement_changed,
       (SELECT max(x.exec_dt) FROM pd.val_test_exec x WHERE x.tc_id = r.tc_id AND x.result = 'PASS') AS req_last_tested,
       a.ack_min_before AS after_hours_ack_min_before,
       a.ack_min_after  AS after_hours_ack_min_after
FROM pairs p
JOIN pd.qms_change_control cc ON cc.cc_no = p.change_control
JOIN pd.qms_deviation d1 ON d1.dev_no = p.dev_1
JOIN pd.qms_deviation d2 ON d2.dev_no = p.dev_2
LEFT JOIN req r ON r.change_control = p.change_control
LEFT JOIN ack a ON a.cc_no = p.change_control
WHERE cc.impl_dt < d1.open_dt AND cc.impl_dt < d2.open_dt
  AND d1.rc_category IS DISTINCT FROM d2.rc_category
ORDER BY 1;
