-- Q3 (flat-table agent, plausible attempt)
-- Group CAPAs by the root cause recorded on their deviations.
SELECT d.rc_category, count(DISTINCT d.dev_no) AS n_deviations,
       string_agg(DISTINCT l.tgt_id, ', ') AS capas
FROM pd.qms_deviation d
JOIN pd.trace_link l ON l.src_type = 'DEV' AND l.src_id = d.dev_no AND l.tgt_type = 'CAPA'
GROUP BY d.rc_category
HAVING count(DISTINCT d.dev_no) > 1;
