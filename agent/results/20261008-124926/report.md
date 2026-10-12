# Agent comparison: with vs. without the semantic layer

Run 20261008-124926. Models: claude-haiku-5-5. Runs per cell: 5. Max tool rounds: 25.

Score: F1 against the answer key (recall only for the open-ended Q2 and Q4; Q3 scored by cause clusters). 1.0 = fully correct.

## Summary

| Model | Condition | Mean score | Fully correct | Tool calls | SQL errors | Seconds | Cost (USD) |
|---|---|---|---|---|---|---|---|
| haiku | raw | 0.70 | 3/15 | 21.7 | 1.3 | 62 | 0.35 |
| haiku | semantic | 0.65 | 7/15 | 15.7 | 0.3 | 54 | 0.19 |

## Score by question

| Question | haiku raw | haiku semantic |
|---|---|---|
| Q1 Unverified high-risk requirements | 0.81 | 0.40 |
| Q3 CAPAs with a shared upstream cause | 0.56 | 0.56 |
| Q4 Traceability chain for %CAR+ | 0.73 | 1.00 |

## What each run missed

| Model | Condition | Q | Run | Score | Missed (required) | Wrong extras |
|---|---|---|---|---|---|---|
| haiku | raw | q1 | 1 | 0.80 | URS-EMS-014 | - |
| haiku | raw | q1 | 2 | 0.80 | URS-EMS-014 | - |
| haiku | raw | q1 | 3 | 0.80 | URS-EMS-014 | - |
| haiku | raw | q1 | 4 | 1.00 | - | - |
| haiku | raw | q1 | 5 | 0.67 | URS-EMS-014 | URS-CRF-001 |
| haiku | semantic | q1 | 1 | 0.00 | URS-EBR-009, URS-EMS-014, URS-INC-004 | - |
| haiku | semantic | q1 | 2 | 1.00 | - | - |
| haiku | semantic | q1 | 3 | 0.00 | URS-EBR-009, URS-EMS-014, URS-INC-004 | - |
| haiku | semantic | q1 | 4 | 0.00 | URS-EBR-009, URS-EMS-014, URS-INC-004 | - |
| haiku | semantic | q1 | 5 | 1.00 | - | - |
| haiku | raw | q3 | 1 | 0.50 | EMS after-hours escalation broken by CC-26-011, FRZ-80-02 failure degraded vector lot LV25-118 (DEV-26-027 blames donors) | - |
| haiku | raw | q3 | 2 | 0.50 | EMS after-hours escalation broken by CC-26-011, INC-03 door switch / latch (DEV-26-011 and DEV-26-033) | - |
| haiku | raw | q3 | 3 | 0.50 | EMS after-hours escalation broken by CC-26-011, FRZ-80-02 failure degraded vector lot LV25-118 (DEV-26-027 blames donors) | - |
| haiku | raw | q3 | 4 | 0.80 | EMS after-hours escalation broken by CC-26-011 | - |
| haiku | raw | q3 | 5 | 0.50 | EMS after-hours escalation broken by CC-26-011, FRZ-80-02 failure degraded vector lot LV25-118 (DEV-26-027 blames donors) | - |
| haiku | semantic | q3 | 1 | 0.50 | EMS after-hours escalation broken by CC-26-011, FRZ-80-02 failure degraded vector lot LV25-118 (DEV-26-027 blames donors) | - |
| haiku | semantic | q3 | 2 | 0.50 | EMS after-hours escalation broken by CC-26-011, FRZ-80-02 failure degraded vector lot LV25-118 (DEV-26-027 blames donors) | - |
| haiku | semantic | q3 | 3 | 0.80 | EMS after-hours escalation broken by CC-26-011 | - |
| haiku | semantic | q3 | 4 | 0.50 | EMS after-hours escalation broken by CC-26-011, FRZ-80-02 failure degraded vector lot LV25-118 (DEV-26-027 blames donors) | - |
| haiku | semantic | q3 | 5 | 0.50 | EMS after-hours escalation broken by CC-26-011, FRZ-80-02 failure degraded vector lot LV25-118 (DEV-26-027 blames donors) | - |
| haiku | raw | q4 | 1 | 0.89 | FM-08 | - |
| haiku | raw | q4 | 2 | 0.78 | DEV-26-021, FM-07 | - |
| haiku | raw | q4 | 3 | 0.00 | AM-FC-CAR, DEV-26-021, DEV-26-027, FM-06, FM-07, FM-08, LV25-118, PPQ-001, URS-EBR-009 | - |
| haiku | raw | q4 | 4 | 1.00 | - | - |
| haiku | raw | q4 | 5 | 1.00 | - | - |
| haiku | semantic | q4 | 1 | 1.00 | - | - |
| haiku | semantic | q4 | 2 | 1.00 | - | - |
| haiku | semantic | q4 | 3 | 1.00 | - | - |
| haiku | semantic | q4 | 4 | 1.00 | - | - |
| haiku | semantic | q4 | 5 | 1.00 | - | - |

Transcripts: `transcripts/<model>_<condition>_<question>_r<run>.json`. Each has the full conversation, every SQL statement and its result.
