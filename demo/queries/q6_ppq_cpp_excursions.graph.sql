-- Q6. Did any PPQ batch have a CPP outside its PPQ acceptance range, and was
--     a deviation raised against that batch or the protocol?
--
-- Hops: Protocol(PPQ) -INCLUDES_BATCH-> Batch -HAS_STEP-> StepRun -INSTANCE_OF-> UnitOperation
--       <-SET_AT- Parameter <-EVALUATES {crit_no}- same Protocol
--       StepRun -RAN_ON-> Equipment <-MONITORS- System(EMS)   (historian-monitored)
--       Batch <-AFFECTS- Deviation, Deviation -AGAINST-> Protocol
-- The semantic layer supplies where each CPP's value lives (process.yaml
-- parameters.*.source) and the historian tag rule; SQL reads the values.
WITH
g AS (
  SELECT DISTINCT kg_txt(pp) AS protocol_id, kg_txt(b) AS batch_id, kg_txt(p) AS param,
         kg_txt(crit) AS crit_no, kg_txt(e) AS equip_id
  FROM cypher('cart_kg', $$
    MATCH (pp:Protocol {ptype: 'PPQ'})-[:INCLUDES_BATCH]->(b:Batch)-[:HAS_STEP]->(sr:StepRun)-[:INSTANCE_OF]->(uo:UnitOperation),
          (p:Parameter {criticality: 'CPP'})-[:SET_AT]->(uo),
          (pp)-[ev:EVALUATES]->(p)
    OPTIONAL MATCH (sr)-[:RAN_ON]->(e:Equipment)<-[:MONITORS]-(:System)
    RETURN pp.id, b.id, p.id, toString(ev.crit_no), e.id
  $$) AS (pp agtype, b agtype, p agtype, crit agtype, e agtype)
),
devs AS (
  SELECT kg_txt(b) AS batch_id, kg_txt(d) AS dev_no
  FROM cypher('cart_kg', $$
    MATCH (d:Deviation)-[:AFFECTS]->(b:Batch)<-[:INCLUDES_BATCH]-(pp:Protocol {ptype: 'PPQ'})
    RETURN b.id, d.id
  $$) AS (b agtype, d agtype)
),
obs AS (        -- observed CPP values, per process.yaml sources
  SELECT g.batch_id, g.param, g.crit_no,
    CASE g.param
      WHEN 'moi'              THEN (SELECT moi_tgt FROM pd.uo04_transduction t WHERE t.batch_id = g.batch_id)
      WHEN 'hrs_post_act'     THEN (SELECT hrs_post_act FROM pd.uo04_transduction t WHERE t.batch_id = g.batch_id)
      WHEN 'seed_density'     THEN (SELECT seed_dens_e6_ml FROM pd.uo03_activation a WHERE a.batch_id = g.batch_id)
      WHEN 'culture_duration' THEN (SELECT hvst_day FROM pd.uo06_harvest h WHERE h.batch_id = g.batch_id)
      WHEN 'culture_temp'     THEN (SELECT min(val) FROM pd.hist_tag_data x, pd.uo03_activation a, pd.uo06_harvest h
                                    WHERE a.batch_id = g.batch_id AND h.batch_id = g.batch_id AND x.qual = 'GOOD'
                                      AND x.tag = replace(g.equip_id, '-', '') || '.TEMP.PV'
                                      AND x.ts BETWEEN a.act_ts AND h.hvst_ts)
    END AS observed_min,
    CASE g.param
      WHEN 'culture_temp' THEN (SELECT count(*) FROM pd.hist_tag_data x, pd.uo03_activation a, pd.uo06_harvest h,
                                       pd.val_ppq_criterion c
                                WHERE a.batch_id = g.batch_id AND h.batch_id = g.batch_id AND x.qual = 'GOOD'
                                  AND c.protocol_id = g.protocol_id AND c.crit_no::text = g.crit_no
                                  AND x.tag = replace(g.equip_id, '-', '') || '.TEMP.PV'
                                  AND x.ts BETWEEN a.act_ts AND h.hvst_ts AND (x.val < c.lo OR x.val > c.hi))
    END AS hours_out,
    g.protocol_id, g.equip_id
  FROM g
  WHERE g.param <> 'culture_temp' OR g.equip_id IS NOT NULL
)
SELECT o.batch_id, o.param, o.equip_id, c.lo || ' - ' || c.hi || ' ' || c.uom AS ppq_range,
       round(o.observed_min, 1) AS observed_min, o.hours_out,
       coalesce((SELECT string_agg(dev_no, ', ') FROM devs d WHERE d.batch_id = o.batch_id), 'NONE') AS deviations_on_batch
FROM obs o
JOIN pd.val_ppq_criterion c ON c.protocol_id = o.protocol_id AND c.crit_no::text = o.crit_no
WHERE o.observed_min < c.lo OR o.observed_min > c.hi OR o.hours_out > 0
ORDER BY o.batch_id, o.param;
