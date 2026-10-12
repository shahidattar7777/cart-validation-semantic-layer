# Demo queries: with vs. without the semantic layer

Six questions that each need 3–5 hops across process, validation and QMS records. Each one has two versions:

- `demo/queries/qN_*.graph.sql`: Cypher (via AGE) to find the path, then SQL over the fact tables for values, dates and limits. This is what the graph-aware agent should produce, given `semantic/*.yaml`.
- `demo/queries/qN_*.naive.sql`: a hand-written, plausible first attempt by an agent that sees only the raw schema.

Run both with `python scripts/run_demo.py`. Full output is in `demo/RESULTS.md`, and `python scripts/verify.py` checks that the answers below still hold after you regenerate the data. Measured values (viabilities, predictions) shift slightly with the seed; IDs and conclusions don't.

**What real agent runs showed** (Claude Haiku 5.5 and Sonnet 5.5, 3–6 runs per cell on Q1, Q3 and Q4, one run on the others; merged report in `agent/results/combined/`): agents with only the raw schema did far better than these hand-written naive queries. They explored with about 20 SQL calls per question and solved Q2, Q5 and Q6 outright. The semantic layer's effect was concentrated where the team's *definitions* and *vocabulary* matter:

- URS-EMS-014 (verification made stale by a change control) was found in 6 of 6 semantic runs and 2 of 9 raw runs. Raw agents often saw the issue but accepted the change control's "no re-testing required".
- For Haiku on Q4, the semantic runs found both FMEA rows written as "TE" and "Transduction efficiency" in 6 of 6 runs; the raw runs did in 2 of 5.
- No agent in either condition found the CC-26-011 escalation cause in Q3 (0 of 18 runs).

Treat the naive queries as an illustration of failure modes, not as a measure of agent performance.

**Fairness note for the audience.** The graph doesn't contain anything the tables lack, because it is built from them. A SQL expert who knows every link type, naming convention and definition could write each of these in SQL. The point is that an agent *without* that knowledge doesn't. It writes a reasonable-looking query, gets a confident wrong answer, and nothing tells it so. The naive queries illustrate typical failure modes. They are hand-written, not agent output. The real agent-vs-agent comparison comes in the agent phase.

---

## Q1. Which high-risk user requirements are not currently verified?

**Path:** FRA FailureMode → URS (risk) · URS → System ← Equipment (units) · TestCase → URS directly, or → CS/FS → URS, or → DS → FS → URS · TestExecution → TestCase, → unit · ChangeControl → URS / child spec / equipment unit.

**Graph + semantic layer: 3 requirements, each for a different reason.**

| Requirement | Unit | Reason |
|---|---|---|
| URS-EBR-009 (MOI range hard stop) | SYS-EBR | No verifying test case, direct or via FS/CS/DS |
| URS-EMS-014 (after-hours alarm escalation) | SYS-EMS | Verification predates CC-26-011, which changed its configuration spec |
| URS-INC-004 (door-open alarm) | INC-03 only | Latest execution failed, never re-executed |

**Flat-table agent:** "high-risk requirements with no VERIFIES link" returns 8 rows.

- **6 false positives.** URS-EBR-001, URS-EMS-011, URS-EMS-012, URS-LIMS-002, URS-LIMS-003 and URS-LIMS-004 are all verified through their configuration, functional or design specs. The agent didn't know coverage can be indirect.
- **URS-EMS-014 is listed for the wrong reason** ("no test"). It *was* tested; a later change invalidated the test.
- **It misses URS-INC-004.** A test case exists and is linked, and the agent doesn't look at per-unit execution results.

What the agent lacked: the definition of "verified" (`definitions.currently_verified_requirement`), the FS/CS/DS trace semantics, and per-unit verification for equipment.

## Q2. CC-26-022 proposes raising MOI from 5 to 8 TU/cell. What needs re-verification or revalidation?

**Path:** Parameter `moi` → UnitOperation ← SOP · ← FailureMode → URS ← (CS) ← TestCase · → QualityAttribute → AnalyticalMethod · ← PPQ protocol (on MOI and on the CQAs it influences). SQL then decides the action from tested ranges, validated method ranges, PPQ acceptance limits, and the DoE data used to predict %CAR+ and VCN at MOI 8.

**Graph + semantic layer: 15 items with a decision on each.** The change control lists only one of them (SOP-MFG-104). The ones that matter:

- **CS-EBR-03:** the EBR has a hard stop at MOI 6.0, so it would block the new process. It needs reconfiguring and testing, and URS-EBR-009 behind it has no test case at all.
- **PPQ-001 criterion 1:** MOI 8 is outside the PPQ acceptance range of 4.0–6.0 (PPQ ran at 5.0), so PPQ does not cover the change. The MOI DoE (2.5–15) is the Stage 1 basis for a wider range. Criteria 8, 9 and 12 (%CAR+, VCN per CAR+ cell, potency) are affected; predicted VCN per CAR+ cell at MOI 8 is about 2.9 against a limit of 5.0.
- **FM-05, FM-06:** HIGH-risk FMEA rows to re-score.
- **TC-OQ-EBR-04:** no re-test needed, because 8.0 is within the tested 2.5–10.0.
- **AM-VCN, AM-FC-CAR:** no impact. The predicted bulk VCN (about 1.7) and %CAR+ (about 55) are within the validated ranges.

**Flat-table agent:** a keyword search for "MOI" returns 8 rows (the SOP, four spec items, two FMEA rows and the PPQ MOI criterion). That's a reasonable start, but:

- It misses everything downstream through the CQAs: method ranges and the PPQ criteria for %CAR+, VCN and potency.
- It misses TC-OQ-EBR-04, whose title doesn't say "MOI".
- Most importantly, it **can't decide anything.** It doesn't know which tests need re-running, whether the methods are still in range, or that the EBR configuration would block the change. It returns mentions, not an impact assessment.

## Q3. Which CAPAs, from different deviations, trace back to the same upstream cause?

**Path:** CAPA ← Deviation → Equipment — System ← URS ← ConfigurationSpec ← ChangeControl, plus SQL evidence from alarm acknowledgement times and test dates.

**Graph + semantic layer:** CAPA-26-008 (replace freezer compressor) and CAPA-26-015 (retrain operators on door latching). They come from DEV-26-021 and DEV-26-033, whose recorded root causes are "EQUIPMENT - COMPRESSOR FAILURE" and "HUMAN ERROR - PROCEDURE NOT FOLLOWED".

Both pieces of equipment are monitored by SYS-EMS. **CC-26-011** (16 Mar 2026) rebuilt the EMS notification groups, a configuration-only change recorded with "no re-testing required". It modified CS-EMS-03, which satisfies URS-EMS-014 (after-hours escalation), last tested 20 Jan 2026. After-hours alarm acknowledgement went from **18 min** on average before the change to **509 min** after.

Both CAPAs addressed the immediate cause. Neither addressed the escalation failure that turned a compressor fault and an unlatched door into multi-hour excursions.

The data holds two more legitimate shared-cause clusters, which the first agent run found: CAPA-26-008 / CAPA-26-016 (the freezer failure degraded the vector lot behind the "donor variability" deviation) and CAPA-26-012 / CAPA-26-015 (the INC-03 door). This query targets only the EMS cluster, the one that needs the longest path; `agent/questions.yaml` scores all three.

**Flat-table agent:** grouping CAPAs by `rc_category` returns **0 rows**, so it concludes "no CAPAs share a root cause". The categories are different, and the link is several hops away through equipment, the monitoring system's requirements and a change control.

## Q4. Full traceability chain for the CQA "%CAR+"

**Path:** the alias "%CAR+" resolves to `transduction_efficiency` · ← Parameters · ← FailureModes · → controls · → test evidence · → protocols · → AnalyticalMethod · ← PPQ → batches · deviations on control equipment and on batches below specification.

**Graph + semantic layer: 34 rows across 8 layers.**

- 3 parameters
- 5 failure modes. The FMEA calls this CQA "%CAR+", "TE" and "Transduction efficiency" in different rows, and the semantic layer resolves all three.
- 9 controls
- Test evidence, flagging **URS-EBR-009: NO TEST CASE** and **TC-OQ-EMS-04: STALE (last run before CC-26-011)**
- The method and its validation
- 5 PPQ results
- 2 deviations

The last layer is the find: **DEV-26-021 → FRZ-80-02 ← LV25-118 → DEV-26-027.** The freezer deviation and the "low %CAR+, suspected donor variability" investigation are connected through the vector lot that was stored in that freezer and used to transduce the engineering runs. Neither deviation mentions the other.

**Flat-table agent:** searching FMEA rows and PPQ criteria for "CAR" returns 11 rows.

- It finds FM-06 and FM-15, but also FM-11 and FM-12, which matched "CAR+ viable cell dose".
- It misses FM-07 ("Transduction efficiency") and FM-08 ("TE").
- It finds the right PPQ criterion, plus the VCN-per-CAR+ criterion that also matched "CAR".
- It returns no controls, no test evidence, no method, and no deviations.

## Q5. Which high-criticality FMEA risks have OQ coverage but no PQ?

**Path:** FailureMode → URS(PERFORMANCE) → System(EQUIPMENT) · TestCase → URS (or FS → URS) · TestCase → Protocol(ptype).

**Graph + semantic layer: 2 risks.**

| Risk | Requirement | OQ | PQ |
|---|---|---|---|
| FM-02, wrong or edited Prodigy program (S8) | URS-PRDG-002 | TC-OQ-PRDG-02 | none linked (PQ-PRDG-01 exists but covers closed processing only) |
| FM-13, freeze curve deviation (S8) | URS-CRF-001 | TC-OQ-CRF-01 | none linked (no CRF PQ protocol) |

In both cases the FMEA's free-text controls column claims PQ: "Prodigy OQ/PQ" and "PQ by engineering runs". Engineering-run data *can* serve as PQ evidence if it is captured under a protocol. The finding is that no PQ test case or evidence record is linked to these requirements, so the claim can't be traced.

Alarm requirements (for example URS-ULT-002) correctly don't appear. The semantic layer says PQ is expected only for PERFORMANCE requirements; alarms are fully verified at OQ.

**Flat-table agent:** filters on the approved `risk_class = 'HIGH'` (the same column the Q1 naive query uses) and searches the controls column for "OQ" and not "PQ". It returns **0 rows** and concludes "no gaps", because the controls text claims PQ for exactly the two risks that lack it. (An agent that used RPN ≥ 100 as "high" would additionally drop FM-03, FM-07, FM-09, FM-14, FM-15 and FM-16, all S ≥ 8 with RPN < 100.)

## Q6. Did any PPQ batch have a CPP outside its PPQ acceptance range, and was a deviation raised?

**Path:** Protocol(PPQ) → Batch → StepRun → UnitOperation ← Parameter(CPP) ← EVALUATES{crit_no} ← same Protocol · StepRun → Equipment ← System(EMS) · Batch ← Deviation. SQL reads each CPP's value from the source the YAML names. Incubator temperature comes from the historian via the tag rule `INC-03 → INC03.TEMP.PV`.

**Graph + semantic layer:**

| Batch | CPP | Unit | PPQ range | Observed min | Hours out | Deviation |
|---|---|---|---|---|---|---|
| PPQ26-02 | culture_temp | INC-03 | 36.5–37.5 °C | about 33.5 | 11 | DEV-26-033 |
| **PPQ26-03** | culture_temp | INC-03 | 36.5–37.5 °C | about 33.5 | 11 | **NONE** |

PPQ26-03 was in the same incubator during the same excursion, early in its culture. It met every release and PPQ acceptance criterion, so nobody looked. It still had a CPP outside its acceptance range during PPQ with no deviation, which the PPQ report has to address.

**Flat-table agent:** searches deviations for "PPQ" and PPQ release tests for FAIL. It finds DEV-26-033 plus two unrelated minor deviations, sees no failed tests, and concludes PPQ was clean apart from PPQ26-02.

The schema does show which incubator each batch used (`uo05_expansion.equip_id`) and has a temperature criterion in `val_ppq_criterion`. What it lacks are two things the semantic layer supplies:

- that the CPP's values live in the historian, under tag `INC03.TEMP.PV` for equipment `INC-03`
- that "CPP excursion" means checking that series across the expansion window

---

## Typical failure patterns

1. **Wrong definition.** "Untested" instead of "not currently verified"; RPN instead of the approved risk class.
2. **Missing indirection.** Coverage through FS/CS/DS, per-unit execution, links typed only as RELATED.
3. **Vocabulary drift.** %CAR+ / TE / transduction efficiency; a keyword hitting "CAR+ viable cell dose".
4. **Trusting free text.** The FMEA controls column claiming PQ coverage that isn't traceable.
5. **Unjoined sources.** Historian tags that don't match equipment IDs; root causes that differ while the cause is shared.
6. **Confident nulls.** Two naive queries return 0 rows and a third returns a clean bill of health. That is the most dangerous output in a validation context.
