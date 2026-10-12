-- Q2 (flat-table agent, plausible attempt)
-- Keyword search for "MOI" across the tables that look relevant.
SELECT 'SOP' AS kind, sop_id AS item, title AS evidence FROM pd.sop WHERE title ILIKE '%MOI%'
UNION ALL
SELECT 'Spec item', item_id, left(item_text, 60) FROM pd.val_spec_item WHERE item_text ILIKE '%MOI%'
UNION ALL
SELECT 'Test case', tc_id, title FROM pd.val_test_case WHERE title ILIKE '%MOI%' OR acceptance_crit ILIKE '%MOI%'
UNION ALL
SELECT 'FMEA row', ri_id, failure_mode FROM pd.val_risk_item WHERE parameter_txt ILIKE '%MOI%'
UNION ALL
SELECT 'PPQ criterion', protocol_id || ' #' || crit_no, attribute_txt FROM pd.val_ppq_criterion WHERE attribute_txt ILIKE '%MOI%'
ORDER BY 1, 2;
