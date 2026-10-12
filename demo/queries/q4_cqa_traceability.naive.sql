-- Q4 (flat-table agent, plausible attempt)
-- Search risk rows and criteria for "CAR" (the question says %CAR+), and pull the QC results.
SELECT 'FMEA row' AS layer, ri_id AS item, failure_mode || ' [' || cqa_impacted || ']' AS detail
FROM pd.val_risk_item WHERE cqa_impacted ILIKE '%CAR%'
UNION ALL
SELECT 'PPQ criterion', protocol_id || ' #' || crit_no, attribute_txt
FROM pd.val_ppq_criterion WHERE attribute_txt ILIKE '%CAR%'
UNION ALL
SELECT 'QC result', batch_id, test_code || ' = ' || result_val || ' ' || coalesce(pass_fail, '')
FROM pd.qc_rel_results WHERE test_code = 'FC-CAR' AND batch_id LIKE 'PPQ%'
ORDER BY 1, 2;
