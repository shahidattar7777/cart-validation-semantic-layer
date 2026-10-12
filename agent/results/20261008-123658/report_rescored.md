# Agent comparison: with vs. without the semantic layer

Run claude-rescore. Models: claude-haiku-5-5, claude-sonnet-5-5. Runs per cell: 1. Max tool rounds: 25.

Score: F1 against the answer key (recall only for the open-ended Q2 and Q4; Q3 scored by cause clusters). 1.0 = fully correct.

## Summary

| Model | Condition | Mean score | Fully correct | Tool calls | SQL errors | Seconds | Cost (USD) |
|---|---|---|---|---|---|---|---|
| haiku | raw | 0.88 | 3/6 | 18.7 | 0.2 | 47 | 0.07 |
| haiku | semantic | 0.92 | 5/6 | 16.8 | 0.2 | 49 | 0.08 |
| sonnet | raw | 0.89 | 4/6 | 18.3 | 0.0 | 47 | 0.82 |
| sonnet | semantic | 0.95 | 4/6 | 17.2 | 0.2 | 44 | 0.95 |

## Score by question

| Question | haiku raw | haiku semantic | sonnet raw | sonnet semantic |
|---|---|---|---|---|
| Q1 Unverified high-risk requirements | 0.80 | 1.00 | 0.86 | 1.00 |
| Q2 MOI change impact (CC-26-022) | 1.00 | 1.00 | 1.00 | 1.00 |
| Q3 CAPAs with a shared upstream cause | 0.80 | 0.50 | 0.50 | 0.80 |
| Q4 Traceability chain for %CAR+ | 0.67 | 1.00 | 1.00 | 0.89 |
| Q5 High-criticality risks with OQ but no PQ | 1.00 | 1.00 | 1.00 | 1.00 |
| Q6 CPP excursions during PPQ | 1.00 | 1.00 | 1.00 | 1.00 |

## What each run missed

| Model | Condition | Q | Run | Score | Missed (required) | Wrong extras |
|---|---|---|---|---|---|---|
| haiku | raw | q1 | 1 | 0.80 | URS-EMS-014 | - |
| haiku | semantic | q1 | 1 | 1.00 | - | - |
| sonnet | raw | q1 | 1 | 0.86 | - | URS-CRF-001 |
| sonnet | semantic | q1 | 1 | 1.00 | - | - |
| haiku | raw | q2 | 1 | 1.00 | - | - |
| haiku | semantic | q2 | 1 | 1.00 | - | - |
| sonnet | raw | q2 | 1 | 1.00 | - | - |
| sonnet | semantic | q2 | 1 | 1.00 | - | - |
| haiku | raw | q3 | 1 | 0.80 | EMS after-hours escalation broken by CC-26-011 | - |
| haiku | semantic | q3 | 1 | 0.50 | EMS after-hours escalation broken by CC-26-011, INC-03 door switch / latch (DEV-26-011 and DEV-26-033) | - |
| sonnet | raw | q3 | 1 | 0.50 | EMS after-hours escalation broken by CC-26-011, FRZ-80-02 failure degraded vector lot LV25-118 (DEV-26-027 blames donors) | - |
| sonnet | semantic | q3 | 1 | 0.80 | EMS after-hours escalation broken by CC-26-011 | - |
| haiku | raw | q4 | 1 | 0.67 | DEV-26-021, FM-07, FM-08 | - |
| haiku | semantic | q4 | 1 | 1.00 | - | - |
| sonnet | raw | q4 | 1 | 1.00 | - | - |
| sonnet | semantic | q4 | 1 | 0.89 | URS-EBR-009 | - |
| haiku | raw | q5 | 1 | 1.00 | - | - |
| haiku | semantic | q5 | 1 | 1.00 | - | - |
| sonnet | raw | q5 | 1 | 1.00 | - | - |
| sonnet | semantic | q5 | 1 | 1.00 | - | - |
| haiku | raw | q6 | 1 | 1.00 | - | - |
| haiku | semantic | q6 | 1 | 1.00 | - | - |
| sonnet | raw | q6 | 1 | 1.00 | - | - |
| sonnet | semantic | q6 | 1 | 1.00 | - | - |

Transcripts: `transcripts/<model>_<condition>_<question>_r<run>.json`. Each has the full conversation, every SQL statement and its result.
