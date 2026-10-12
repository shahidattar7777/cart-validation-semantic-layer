-- Q1 (flat-table agent, plausible attempt)
-- "Requirements with no test case linked to them", limited to high-risk ones.
SELECT s.item_id AS requirement, left(s.item_text, 70) AS requirement_text
FROM pd.val_spec_item s
JOIN pd.trace_link a ON a.link_type = 'ASSESSES' AND a.tgt_id = s.item_id
JOIN pd.val_risk_item r ON r.ri_id = a.src_id AND r.risk_class = 'HIGH'
WHERE s.spec_level = 'URS'
  AND NOT EXISTS (SELECT 1 FROM pd.trace_link l
                  WHERE l.link_type = 'VERIFIES' AND l.tgt_id = s.item_id)
ORDER BY 1;
