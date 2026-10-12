-- Q5 (flat-table agent, plausible attempt)
-- High risk from the approved risk_class; coverage read from the FMEA's controls column.
SELECT ri_id, process_step, failure_mode, sev, rpn, current_controls
FROM pd.val_risk_item
WHERE risk_class = 'HIGH'
  AND current_controls ILIKE '%OQ%'
  AND current_controls NOT ILIKE '%PQ%'
ORDER BY ri_id;
