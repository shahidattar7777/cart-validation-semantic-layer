# Agent comparison: with vs. without the semantic layer

Run combined. Models: claude-haiku-5-5, claude-sonnet-5-5. Runs per cell: 6. Max tool rounds: 25.

Score: F1 against the answer key (recall only for the open-ended Q2 and Q4; Q3 scored by cause clusters). 1.0 = fully correct. Mean score = average of the per-question means, so questions with more runs don't weigh more. Runs whose output was cut off before any answer (a harness bug) are excluded.

## Summary

| Model | Condition | Mean score | Fully correct | Tool calls | SQL errors | Seconds | Cost (USD) |
|---|---|---|---|---|---|---|---|
| haiku | raw | 0.88 | 6/20 | 19.8 | 0.9 | 52 | 0.33 |
| haiku | semantic | 0.92 | 12/18 | 17.2 | 0.3 | 54 | 0.24 |
| sonnet | raw | 0.91 | 7/12 | 21.6 | 0.1 | 55 | 1.92 |
| sonnet | semantic | 0.97 | 9/12 | 18.8 | 0.2 | 50 | 1.96 |

## Score by question

| Question | haiku raw | haiku semantic | sonnet raw | sonnet semantic |
|---|---|---|---|---|
| Q1 Unverified high-risk requirements | 0.83 | 1.00 | 0.87 | 1.00 |
| Q2 MOI change impact (CC-26-022) | 1.00 | 1.00 | 1.00 | 1.00 |
| Q3 CAPAs with a shared upstream cause | 0.60 | 0.55 | 0.60 | 0.80 |
| Q4 Traceability chain for %CAR+ | 0.85 | 1.00 | 1.00 | 1.00 |
| Q5 High-criticality risks with OQ but no PQ | 1.00 | 1.00 | 1.00 | 1.00 |
| Q6 CPP excursions during PPQ | 1.00 | 1.00 | 1.00 | 1.00 |

## What each run missed

| Model | Condition | Q | Run | Score | Missed (required) | Wrong extras |
|---|---|---|---|---|---|---|
| haiku | raw | q1 | 1 | 0.80 | URS-EMS-014 | - |
| haiku | raw | q1 | 2 | 0.80 | URS-EMS-014 | - |
| haiku | raw | q1 | 3 | 0.80 | URS-EMS-014 | - |
| haiku | raw | q1 | 4 | 0.80 | URS-EMS-014 | - |
| haiku | raw | q1 | 5 | 1.00 | - | - |
| haiku | raw | q1 | 6 | 0.80 | URS-EMS-014 | - |
| haiku | semantic | q1 | 1 | 1.00 | - | - |
| haiku | semantic | q1 | 2 | ERROR | harness: no answer text (stop_reason=max_tokens), excluded | |
| haiku | semantic | q1 | 3 | ERROR | harness: no answer text (stop_reason=max_tokens), excluded | |
| haiku | semantic | q1 | 4 | 1.00 | - | - |
| haiku | semantic | q1 | 5 | ERROR | harness: no answer text (stop_reason=max_tokens), excluded | |
| haiku | semantic | q1 | 6 | 1.00 | - | - |
| sonnet | raw | q1 | 1 | 1.00 | - | - |
| sonnet | raw | q1 | 2 | 0.80 | URS-EMS-014 | - |
| sonnet | raw | q1 | 3 | 0.80 | URS-EMS-014 | - |
| sonnet | semantic | q1 | 1 | 1.00 | - | - |
| sonnet | semantic | q1 | 2 | 1.00 | - | - |
| sonnet | semantic | q1 | 3 | 1.00 | - | - |
| haiku | raw | q2 | 1 | 1.00 | - | - |
| haiku | semantic | q2 | 1 | 1.00 | - | - |
| sonnet | raw | q2 | 1 | 1.00 | - | - |
| sonnet | semantic | q2 | 1 | 1.00 | - | - |
| haiku | raw | q3 | 1 | 0.80 | EMS after-hours escalation broken by CC-26-011 | - |
| haiku | raw | q3 | 2 | 0.50 | EMS after-hours escalation broken by CC-26-011, FRZ-80-02 failure degraded vector lot LV25-118 (DEV-26-027 blames donors) | - |
| haiku | raw | q3 | 3 | 0.50 | EMS after-hours escalation broken by CC-26-011, INC-03 door switch / latch (DEV-26-011 and DEV-26-033) | - |
| haiku | raw | q3 | 4 | 0.50 | EMS after-hours escalation broken by CC-26-011, FRZ-80-02 failure degraded vector lot LV25-118 (DEV-26-027 blames donors) | - |
| haiku | raw | q3 | 5 | 0.50 | EMS after-hours escalation broken by CC-26-011, FRZ-80-02 failure degraded vector lot LV25-118 (DEV-26-027 blames donors) | - |
| haiku | raw | q3 | 6 | 0.80 | EMS after-hours escalation broken by CC-26-011 | - |
| haiku | semantic | q3 | 1 | 0.50 | EMS after-hours escalation broken by CC-26-011, INC-03 door switch / latch (DEV-26-011 and DEV-26-033) | - |
| haiku | semantic | q3 | 2 | 0.50 | EMS after-hours escalation broken by CC-26-011, FRZ-80-02 failure degraded vector lot LV25-118 (DEV-26-027 blames donors) | - |
| haiku | semantic | q3 | 3 | 0.50 | EMS after-hours escalation broken by CC-26-011, FRZ-80-02 failure degraded vector lot LV25-118 (DEV-26-027 blames donors) | - |
| haiku | semantic | q3 | 4 | 0.50 | EMS after-hours escalation broken by CC-26-011, FRZ-80-02 failure degraded vector lot LV25-118 (DEV-26-027 blames donors) | - |
| haiku | semantic | q3 | 5 | 0.80 | EMS after-hours escalation broken by CC-26-011 | - |
| haiku | semantic | q3 | 6 | 0.50 | EMS after-hours escalation broken by CC-26-011, FRZ-80-02 failure degraded vector lot LV25-118 (DEV-26-027 blames donors) | - |
| sonnet | raw | q3 | 1 | 0.50 | EMS after-hours escalation broken by CC-26-011, FRZ-80-02 failure degraded vector lot LV25-118 (DEV-26-027 blames donors) | - |
| sonnet | raw | q3 | 2 | 0.50 | EMS after-hours escalation broken by CC-26-011, FRZ-80-02 failure degraded vector lot LV25-118 (DEV-26-027 blames donors) | - |
| sonnet | raw | q3 | 3 | 0.80 | EMS after-hours escalation broken by CC-26-011 | - |
| sonnet | semantic | q3 | 1 | 0.80 | EMS after-hours escalation broken by CC-26-011 | - |
| sonnet | semantic | q3 | 2 | 0.80 | EMS after-hours escalation broken by CC-26-011 | - |
| sonnet | semantic | q3 | 3 | 0.80 | EMS after-hours escalation broken by CC-26-011 | - |
| haiku | raw | q4 | 1 | 0.62 | DEV-26-021, FM-07, FM-08 | - |
| haiku | raw | q4 | 2 | 0.75 | DEV-26-021, FM-07 | - |
| haiku | raw | q4 | 3 | 0.88 | FM-08 | - |
| haiku | raw | q4 | 4 | 1.00 | - | - |
| haiku | raw | q4 | 5 | 1.00 | - | - |
| haiku | raw | q4 | 6 | ERROR | harness: no answer text (stop_reason=max_tokens), excluded | |
| haiku | semantic | q4 | 1 | 1.00 | - | - |
| haiku | semantic | q4 | 2 | 1.00 | - | - |
| haiku | semantic | q4 | 3 | 1.00 | - | - |
| haiku | semantic | q4 | 4 | 1.00 | - | - |
| haiku | semantic | q4 | 5 | 1.00 | - | - |
| haiku | semantic | q4 | 6 | 1.00 | - | - |
| sonnet | raw | q4 | 1 | 1.00 | - | - |
| sonnet | raw | q4 | 2 | 1.00 | - | - |
| sonnet | raw | q4 | 3 | 1.00 | - | - |
| sonnet | semantic | q4 | 1 | 1.00 | - | - |
| sonnet | semantic | q4 | 2 | 1.00 | - | - |
| sonnet | semantic | q4 | 3 | 1.00 | - | - |
| haiku | raw | q5 | 1 | 1.00 | - | - |
| haiku | semantic | q5 | 1 | 1.00 | - | - |
| sonnet | raw | q5 | 1 | 1.00 | - | - |
| sonnet | semantic | q5 | 1 | 1.00 | - | - |
| haiku | raw | q6 | 1 | 1.00 | - | - |
| haiku | semantic | q6 | 1 | 1.00 | - | - |
| sonnet | raw | q6 | 1 | 1.00 | - | - |
| sonnet | semantic | q6 | 1 | 1.00 | - | - |

Transcripts: `transcripts/<model>_<condition>_<question>_r<run>.json`. Each has the full conversation, every SQL statement and its result.
