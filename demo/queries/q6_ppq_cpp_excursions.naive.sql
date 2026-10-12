-- Q6 (flat-table agent, plausible attempt)
-- Look for PPQ deviations and failed PPQ release tests.
SELECT 'deviation' AS source, dev_no AS item, title AS detail
FROM pd.qms_deviation WHERE title ILIKE '%PPQ%' OR description ILIKE '%PPQ%'
UNION ALL
SELECT 'failed test', batch_id, test_code || ' = ' || result_val
FROM pd.qc_rel_results WHERE batch_id LIKE 'PPQ%' AND pass_fail = 'FAIL'
ORDER BY 1, 2;
