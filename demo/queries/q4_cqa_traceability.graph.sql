-- Q4. Full traceability chain for the CQA "%CAR+" (transduction efficiency):
--     which parameters drive it, which risks threaten it, which controls and
--     tests cover those risks, how it is measured and validated, and how it
--     performed in PPQ.
--
-- The question says "%CAR+"; the semantic layer resolves it to
-- QualityAttribute 'transduction_efficiency' (aliases: %CAR+, TE, CAR expression...).
-- Hops: QA <-INFLUENCES- Parameter <-INVOLVES- FailureMode -MITIGATED_BY-> URS|SOP
--       URS <-VERIFIES(-via spec)- TestCase -PART_OF-> Protocol
--       QA -MEASURED_BY-> AnalyticalMethod <-VALIDATES- Protocol
--       QA <-EVALUATES- Protocol(PPQ) -INCLUDES_BATCH-> Batch <-AFFECTS- Deviation
--       Deviation -AFFECTS-> Equipment <-STORED_IN- MaterialLot <-USED- StepRun <-HAS_STEP- Batch <-AFFECTS- Deviation
WITH
g AS (
  SELECT kg_txt(layer) AS layer, kg_txt(item) AS item, kg_txt(via) AS via, kg_txt(k) AS k
  FROM cypher('cart_kg', $$
    MATCH (q:QualityAttribute {id: 'transduction_efficiency'})<-[:INFLUENCES]-(p:Parameter)
    RETURN '1 Parameter', p.id, p.criticality, null
    UNION
    MATCH (q:QualityAttribute {id: 'transduction_efficiency'})<-[:AFFECTS]-(f:FailureMode)
    RETURN '2 Failure mode', f.id, 'affects CQA', null
    UNION
    MATCH (q:QualityAttribute {id: 'transduction_efficiency'})<-[:INFLUENCES]-(p:Parameter)<-[:INVOLVES]-(f:FailureMode)
    RETURN '2 Failure mode', f.id, 'involves ' + p.id, null
    UNION
    MATCH (q:QualityAttribute {id: 'transduction_efficiency'})<-[:INFLUENCES]-(:Parameter)<-[:INVOLVES]-(f:FailureMode)-[:MITIGATED_BY]->(c)
    RETURN '3 Control', c.id, 'mitigates ' + f.id, null
    UNION
    MATCH (q:QualityAttribute {id: 'transduction_efficiency'})<-[:AFFECTS]-(f:FailureMode)-[:MITIGATED_BY]->(c)
    RETURN '3 Control', c.id, 'mitigates ' + f.id, null
    UNION
    MATCH (q:QualityAttribute {id: 'transduction_efficiency'})<-[:INFLUENCES]-(:Parameter)<-[:INVOLVES]-(:FailureMode)-[:MITIGATED_BY]->(u:UserRequirement)<-[:VERIFIES]-(tc:TestCase)-[:PART_OF]->(pr:Protocol)
    RETURN '4 Test evidence', tc.id, u.id, pr.id
    UNION
    MATCH (q:QualityAttribute {id: 'transduction_efficiency'})<-[:INFLUENCES]-(:Parameter)<-[:INVOLVES]-(:FailureMode)-[:MITIGATED_BY]->(u:UserRequirement)<-[:SATISFIES]-()<-[:VERIFIES]-(tc:TestCase)-[:PART_OF]->(pr:Protocol)
    RETURN '4 Test evidence', tc.id, u.id, pr.id
    UNION
    MATCH (q:QualityAttribute {id: 'transduction_efficiency'})<-[:AFFECTS]-(:FailureMode)-[:MITIGATED_BY]->(u:UserRequirement)<-[:VERIFIES]-(tc:TestCase)-[:PART_OF]->(pr:Protocol)
    RETURN '4 Test evidence', tc.id, u.id, pr.id
    UNION
    MATCH (q:QualityAttribute {id: 'transduction_efficiency'})<-[:AFFECTS]-(:FailureMode)-[:MITIGATED_BY]->(u:UserRequirement)<-[:SATISFIES]-()<-[:VERIFIES]-(tc:TestCase)-[:PART_OF]->(pr:Protocol)
    RETURN '4 Test evidence', tc.id, u.id, pr.id
    UNION
    MATCH (q:QualityAttribute {id: 'transduction_efficiency'})-[:MEASURED_BY]->(m:AnalyticalMethod)
    OPTIONAL MATCH (v:Protocol)-[:VALIDATES]->(m)
    RETURN '5 Method', m.id, v.id, null
    UNION
    MATCH (q:QualityAttribute {id: 'transduction_efficiency'})<-[e:EVALUATES]-(pp:Protocol)-[:INCLUDES_BATCH]->(b:Batch)
    RETURN '6 PPQ batch', b.id, pp.id, toString(e.crit_no)
    UNION
    MATCH (q:QualityAttribute {id: 'transduction_efficiency'})<-[:AFFECTS]-(:FailureMode)-[:MITIGATED_BY]->(:UserRequirement)-[:APPLIES_TO]->(s:System)<-[:PART_OF]-(e:Equipment)<-[:AFFECTS]-(d:Deviation)
    RETURN '7 Deviation', d.id, 'on control equipment ' + e.id, null
    UNION
    MATCH (q:QualityAttribute {id: 'transduction_efficiency'})<-[:INFLUENCES]-(:Parameter)-[:SET_AT]->(:UnitOperation)<-[:INSTANCE_OF]-(:StepRun)<-[:HAS_STEP]-(b:Batch)<-[:AFFECTS]-(d:Deviation)
    RETURN '7 Deviation', d.id, 'on batch ' + b.id, b.id
    UNION
    MATCH (d1:Deviation)-[:AFFECTS]->(e:Equipment)<-[:STORED_IN]-(l:MaterialLot)<-[:USED]-(sr:StepRun)<-[:HAS_STEP]-(b:Batch)<-[:AFFECTS]-(d2:Deviation),
          (sr)-[:INSTANCE_OF]->(:UnitOperation)<-[:SET_AT]-(:Parameter)-[:INFLUENCES]->(q:QualityAttribute {id: 'transduction_efficiency'})
    WHERE d1.id <> d2.id
    RETURN '8 Hidden link', d1.id + ' -> ' + e.id + ' <- ' + l.id + ' -> ' + d2.id, b.id, null
  $$) AS (layer agtype, item agtype, via agtype, k agtype)
),
stale AS (       -- test cases whose verified spec was modified by a change implemented after their last execution
  SELECT kg_txt(tc) AS tc_id, kg_txt(cc) AS cc_no
  FROM cypher('cart_kg', $$
    MATCH (cc:ChangeControl)-[:MODIFIES]->(s)<-[:VERIFIES]-(tc:TestCase) RETURN tc.id, cc.id
  $$) AS (tc agtype, cc agtype)
),
g_filtered AS (   -- batch deviations only count if that batch's %CAR+ was below specification
  SELECT g.* FROM g
  LEFT JOIN pd.qc_rel_results q ON q.batch_id = g.k AND q.test_code = 'FC-CAR'
  WHERE NOT (g.layer = '7 Deviation' AND g.k IS NOT NULL AND NOT coalesce(q.result_val < q.spec_lo, false))
  UNION ALL
  SELECT '4 Test evidence', '(none)', c.item, NULL FROM g c
  WHERE c.layer = '3 Control' AND c.item LIKE 'URS-%'
    AND NOT EXISTS (SELECT 1 FROM g t WHERE t.layer = '4 Test evidence' AND t.via = c.item)
)
SELECT g.layer, g.item, string_agg(DISTINCT g.via, '; ') AS linked_via,
  max(CASE
    WHEN g.layer = '2 Failure mode' THEN r.risk_class || ' S' || r.sev || ': ' || r.failure_mode || ' [cqa text: "' || r.cqa_impacted || '"]'
    WHEN g.layer = '3 Control' THEN coalesce(left(si.item_text, 60), so.title)
    WHEN g.layer = '4 Test evidence' AND g.item = '(none)' THEN 'NO TEST CASE for this control'
    WHEN g.layer = '4 Test evidence' THEN pt.ptype || ' ' || g.k || ' / ' || x.res
         || coalesce((SELECT ' / STALE: last run before ' || st.cc_no FROM stale st
                      JOIN pd.qms_change_control c ON c.cc_no = st.cc_no
                      WHERE st.tc_id = g.item
                        AND c.impl_dt > (SELECT max(exec_dt) FROM pd.val_test_exec e WHERE e.tc_id = g.item)
                      LIMIT 1), '')
    WHEN g.layer = '5 Method' THEN am.method_name || ', validated ' || am.val_range_lo || '-' || am.val_range_hi || ' ' || am.uom
    WHEN g.layer = '6 PPQ batch' THEN q.result_val || ' ' || q.uom || ' vs >= ' || c.lo || ' -> ' || q.pass_fail
    WHEN g.layer = '7 Deviation' THEN d.record_type || ': ' || d.title || ' [recorded root cause: ' || d.rc_category || ']'
    WHEN g.layer = '8 Hidden link' THEN 'Deviation on storage equipment of a lot used at transduction of a batch with its own deviation'
  END) AS detail
FROM g_filtered g
LEFT JOIN pd.val_risk_item r ON g.layer = '2 Failure mode' AND r.ri_id = g.item
LEFT JOIN pd.val_spec_item si ON g.layer = '3 Control' AND si.item_id = g.item
LEFT JOIN pd.sop so ON g.layer = '3 Control' AND so.sop_id = g.item
LEFT JOIN pd.val_protocol pt ON g.layer = '4 Test evidence' AND pt.protocol_id = g.k
LEFT JOIN LATERAL (SELECT string_agg(DISTINCT x.result, '/') || ' x' || count(*) AS res
                   FROM pd.val_test_exec x WHERE x.tc_id = g.item) x ON g.layer = '4 Test evidence' AND g.item <> '(none)'
LEFT JOIN pd.analytical_method am ON g.layer = '5 Method' AND am.method_id = g.item
LEFT JOIN pd.qc_rel_results q ON g.layer = '6 PPQ batch' AND q.batch_id = g.item AND q.test_code = 'FC-CAR'
LEFT JOIN pd.val_ppq_criterion c ON g.layer = '6 PPQ batch' AND c.protocol_id = g.via AND c.crit_no::text = g.k
LEFT JOIN pd.qms_deviation d ON g.layer = '7 Deviation' AND d.dev_no = g.item
GROUP BY g.layer, g.item
ORDER BY g.layer, g.item;
