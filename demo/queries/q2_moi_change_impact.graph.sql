-- Q2. CC-26-022 proposes raising target MOI from 5.0 to 8.0 TU/cell.
--     What needs re-verification or revalidation, and which items is the
--     change control's own impact assessment missing?
--
-- Hops from Parameter 'moi':
--   -SET_AT-> UnitOperation <-GOVERNS- SOP                          (procedures)
--   <-INVOLVES- FailureMode                                         (risk re-assessment)
--   <-INVOLVES- FailureMode -MITIGATED_BY-> URS <-VERIFIES(-via spec)- TestCase -PART_OF-> Protocol
--   -INFLUENCES-> QualityAttribute -MEASURED_BY-> AnalyticalMethod <-VALIDATES- Protocol(AMV)
--   <-EVALUATES- Protocol(PPQ); QualityAttribute <-EVALUATES- Protocol(PPQ)
-- Then SQL decides the action using content: tested ranges, validated
-- ranges, PPQ limits, and the DoE data to predict CQAs at the new MOI.
WITH
new_moi AS (SELECT 8.0::numeric AS v),
-- predicted CQA values at the new MOI from the PV2.0 DoE runs (linear between bracketing levels)
doe AS (
  SELECT t.moi_tgt,
         avg(q.result_val) FILTER (WHERE q.test_code = 'FC-CAR')    AS car,
         avg(q.result_val) FILTER (WHERE q.test_code = 'VCN-DDPCR') AS vcn,
         avg(q.result_val) FILTER (WHERE q.test_code = 'VCN-PER-CAR') AS vcn_car
  FROM pd.batch_master b JOIN pd.uo04_transduction t USING (batch_id)
  JOIN pd.qc_rel_results q ON q.batch_id = b.batch_id
  WHERE b.doe_id IS NOT NULL AND b.proc_ver = 'PV2.0'
  GROUP BY t.moi_tgt
),
pred AS (
  SELECT lo.car + (hi.car - lo.car) * ((SELECT v FROM new_moi) - lo.moi_tgt) / (hi.moi_tgt - lo.moi_tgt) AS car,
         lo.vcn + (hi.vcn - lo.vcn) * ((SELECT v FROM new_moi) - lo.moi_tgt) / (hi.moi_tgt - lo.moi_tgt) AS vcn,
         lo.vcn_car + (hi.vcn_car - lo.vcn_car) * ((SELECT v FROM new_moi) - lo.moi_tgt) / (hi.moi_tgt - lo.moi_tgt) AS vcn_car
  FROM doe lo, doe hi WHERE lo.moi_tgt = 5.0 AND hi.moi_tgt = 10.0
),
g AS (
  SELECT kg_txt(kind) AS kind, kg_txt(item) AS item, kg_txt(via) AS via, kg_txt(extra) AS extra
  FROM cypher('cart_kg', $$
    MATCH (p:Parameter {id: 'moi'})-[:SET_AT]->(:UnitOperation)<-[:GOVERNS]-(s:SOP)
    RETURN 'SOP', s.id, 'governs the step where MOI is set', null
    UNION
    MATCH (p:Parameter {id: 'moi'})<-[:INVOLVES]-(f:FailureMode)
    RETURN 'FailureMode', f.id, 'FMEA line on MOI', null
    UNION
    MATCH (p:Parameter {id: 'moi'})<-[:INVOLVES]-(f:FailureMode)-[:MITIGATED_BY]->(u:UserRequirement)
    RETURN 'Requirement', u.id, 'control for ' + f.id, null
    UNION
    MATCH (p:Parameter {id: 'moi'})<-[:INVOLVES]-(:FailureMode)-[:MITIGATED_BY]->(u:UserRequirement)<-[:SATISFIES]-(c:ConfigurationSpec)
    RETURN 'ConfigSpec', c.id, 'configures ' + u.id, null
    UNION
    MATCH (p:Parameter {id: 'moi'})<-[:INVOLVES]-(:FailureMode)-[:MITIGATED_BY]->(u:UserRequirement)<-[:VERIFIES]-(tc:TestCase)
    RETURN 'TestCase', tc.id, 'verifies ' + u.id, null
    UNION
    MATCH (p:Parameter {id: 'moi'})<-[:INVOLVES]-(:FailureMode)-[:MITIGATED_BY]->(u:UserRequirement)<-[:SATISFIES]-(c)<-[:VERIFIES]-(tc:TestCase)
    RETURN 'TestCase', tc.id, 'verifies ' + u.id + ' via ' + c.id, null
    UNION
    MATCH (p:Parameter {id: 'moi'})-[:INFLUENCES]->(q:QualityAttribute)-[:MEASURED_BY]->(m:AnalyticalMethod)
    WHERE q.criticality IN ['CQA', 'KQA']
    RETURN 'AnalyticalMethod', m.id, 'measures ' + q.id, q.id
    UNION
    MATCH (p:Parameter {id: 'moi'})<-[e:EVALUATES]-(pp:Protocol)
    RETURN 'PPQ criterion', pp.id, 'MOI', toString(e.crit_no)
    UNION
    MATCH (p:Parameter {id: 'moi'})-[:INFLUENCES]->(q:QualityAttribute)<-[e:EVALUATES]-(pp:Protocol)
    RETURN 'PPQ criterion', pp.id, q.id, toString(e.crit_no)
  $$) AS (kind agtype, item agtype, via agtype, extra agtype)
),
g2 AS (
  SELECT kind, item, string_agg(DISTINCT via, '; ') AS via, extra FROM g GROUP BY kind, item, extra
),
listed AS (     -- what the change control itself lists as impacted
  SELECT kg_txt(x) AS item FROM cypher('cart_kg', $$
    MATCH (:ChangeControl {id: 'CC-26-022'})-[:MODIFIES]->(x) RETURN x.id
  $$) AS (x agtype)
)
SELECT g.kind, g.item, g.via,
  CASE g.kind
    WHEN 'SOP' THEN 'Revise'
    WHEN 'FailureMode' THEN 'Re-score (' || r.risk_class || ', S' || r.sev || ')'
    WHEN 'Requirement' THEN CASE WHEN si.item_text ~ '4\.0-6\.0' THEN 'Hard-codes 4.0-6.0: revise URS' ELSE 'Review' END
                            || CASE WHEN NOT EXISTS (SELECT 1 FROM g t WHERE t.kind = 'TestCase' AND t.via LIKE '%' || g.item || '%')
                                    THEN '; NO test case exists' ELSE '' END
    WHEN 'ConfigSpec' THEN CASE WHEN si2.item_text ~ '4\.0-6\.0' THEN 'EBR hard stop at 6.0 would block MOI 8.0: reconfigure and test' ELSE 'Review' END
    WHEN 'TestCase' THEN CASE WHEN tc.tested_hi IS NULL THEN 'Review'
                              WHEN (SELECT v FROM new_moi) BETWEEN tc.tested_lo AND tc.tested_hi
                                THEN 'No re-test: 8.0 within tested ' || tc.tested_lo || '-' || tc.tested_hi
                              ELSE 'Re-test: 8.0 outside tested range' END
    WHEN 'AnalyticalMethod' THEN
      CASE WHEN g.extra = 'vcn_bulk' THEN
             CASE WHEN (SELECT vcn FROM pred) BETWEEN am.val_range_lo AND am.val_range_hi
                  THEN 'OK: predicted VCN ' || round((SELECT vcn FROM pred), 2) || ' within validated ' || am.val_range_lo || '-' || am.val_range_hi
                  ELSE 'Extend validation range' END
           WHEN g.extra = 'transduction_efficiency' THEN
             CASE WHEN (SELECT car FROM pred) BETWEEN am.val_range_lo AND am.val_range_hi
                  THEN 'OK: predicted %CAR+ ' || round((SELECT car FROM pred), 1) || ' within validated ' || am.val_range_lo || '-' || am.val_range_hi
                  ELSE 'Extend validation range' END
           ELSE 'Review' END
    WHEN 'PPQ criterion' THEN
      CASE WHEN g.via = 'MOI' AND NOT ((SELECT v FROM new_moi) BETWEEN c.lo AND c.hi)
             THEN 'New MOI outside PPQ acceptance range ' || c.lo || '-' || c.hi || ' (PPQ ran at 5.0): PPQ does not cover change; DoE 2.5-15 is the Stage 1 basis'
           WHEN g.via = 'vcn' THEN 'Criterion ' || c.crit_no || ' (' || c.attribute_txt || ' <= ' || c.hi || '): predicted '
                || round((SELECT vcn_car FROM pred), 2) || ' at MOI 8, comparability data needed'
           ELSE 'Criterion ' || c.crit_no || ' (' || c.attribute_txt || ') affected: comparability data needed' END
  END AS action,
  l.item IS NOT NULL AS listed_in_cc
FROM g2 g
LEFT JOIN listed l ON l.item = g.item AND g.kind <> 'PPQ criterion'
LEFT JOIN pd.val_risk_item r ON g.kind = 'FailureMode' AND r.ri_id = g.item
LEFT JOIN pd.val_spec_item si ON g.kind = 'Requirement' AND si.item_id = g.item
LEFT JOIN pd.val_spec_item si2 ON g.kind = 'ConfigSpec' AND si2.item_id = g.item
LEFT JOIN pd.val_test_case tc ON g.kind = 'TestCase' AND tc.tc_id = g.item
LEFT JOIN pd.analytical_method am ON g.kind = 'AnalyticalMethod' AND am.method_id = g.item
LEFT JOIN pd.val_ppq_criterion c ON g.kind = 'PPQ criterion' AND c.protocol_id = g.item AND c.crit_no::text = g.extra
WHERE NOT (g.kind = 'AnalyticalMethod' AND g.extra = 'vcn')
ORDER BY CASE g.kind WHEN 'SOP' THEN 1 WHEN 'FailureMode' THEN 2 WHEN 'Requirement' THEN 3 WHEN 'ConfigSpec' THEN 4
                     WHEN 'TestCase' THEN 5 WHEN 'AnalyticalMethod' THEN 6 ELSE 7 END, g.item, g.via;
