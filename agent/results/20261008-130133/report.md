# Agent comparison: with vs. without the semantic layer

Run 20261008-130133. Models: claude-sonnet-5-5. Runs per cell: 2. Max tool rounds: 25.

Score: F1 against the answer key (recall only for the open-ended Q2 and Q4; Q3 scored by cause clusters). 1.0 = fully correct.

## Summary

| Model | Condition | Mean score | Fully correct | Tool calls | SQL errors | Seconds | Cost (USD) |
|---|---|---|---|---|---|---|---|
| sonnet | raw | 0.77 | 2/6 | 24.8 | 0.2 | 63 | 1.10 |
| sonnet | semantic | 0.85 | 1/6 | 20.3 | 0.2 | 57 | 1.02 |

## Score by question

| Question | sonnet raw | sonnet semantic |
|---|---|---|
| Q1 Unverified high-risk requirements | 0.67 | 0.88 |
| Q3 CAPAs with a shared upstream cause | 0.65 | 0.80 |
| Q4 Traceability chain for %CAR+ | 1.00 | 0.89 |

## What each run missed

| Model | Condition | Q | Run | Score | Missed (required) | Wrong extras |
|---|---|---|---|---|---|---|
| sonnet | raw | q1 | 1 | 0.67 | URS-EMS-014 | URS-CRF-001 |
| sonnet | raw | q1 | 2 | 0.67 | URS-EMS-014 | URS-CRF-001 |
| sonnet | semantic | q1 | 1 | 0.75 | - | URS-CRF-001, URS-PRDG-002 |
| sonnet | semantic | q1 | 2 | 1.00 | - | - |
| sonnet | raw | q3 | 1 | 0.80 | EMS after-hours escalation broken by CC-26-011 | - |
| sonnet | raw | q3 | 2 | 0.50 | EMS after-hours escalation broken by CC-26-011, FRZ-80-02 failure degraded vector lot LV25-118 (DEV-26-027 blames donors) | - |
| sonnet | semantic | q3 | 1 | 0.80 | EMS after-hours escalation broken by CC-26-011 | - |
| sonnet | semantic | q3 | 2 | 0.80 | EMS after-hours escalation broken by CC-26-011 | - |
| sonnet | raw | q4 | 1 | 1.00 | - | - |
| sonnet | raw | q4 | 2 | 1.00 | - | - |
| sonnet | semantic | q4 | 1 | 0.89 | URS-EBR-009 | - |
| sonnet | semantic | q4 | 2 | 0.89 | URS-EBR-009 | - |

Transcripts: `transcripts/<model>_<condition>_<question>_r<run>.json`. Each has the full conversation, every SQL statement and its result.
