# Terminology and structure review (GAMP 5, FDA CSA, and the guidance that actually applies)

Written for an audience that does validation for a living. Each claim below was checked against the source listed at the end, as of October 2026. Where something could only be checked through secondary sources (GAMP 5 itself is paywalled), it says so.

## Bottom line

1. **The FDA CSA guidance does not apply to a CAR-T process.** Present its concepts as good practice that GAMP 5 (2nd ed.) is aligned with, never as "per FDA".
2. **"Protocol (IQ/OQ/PQ/PPQ)" mixes different lifecycles.** That's fine in one graph (connecting them is the point), but each must keep its own vocabulary. "PQ" is the term most likely to be misread.
3. **The FMEA unit is the failure mode, not the assessment.** Use the team-assigned risk class as the source of truth, not an RPN cut-off. This repo's documented team rule is severity-led (S ≥ 8 → HIGH). ICH Q9(R1) doesn't prescribe a scoring scheme; it warns that poorly designed scoring scales add subjectivity.
4. **"No test coverage" is the wrong question.** The right one is "no verification evidence appropriate to the risk". Not every requirement needs a scripted test.
5. **"Deviation" is too broad.** QA distinguishes GMP deviations, protocol deviations, test incidents, OOS investigations, and atypical results on non-release tests.
6. **PD runs are not GMP.** They don't carry deviations, CAPAs or release pass/fail. The first draft data did, and a QA reviewer would have stopped reading there.

## 1. Which guidance applies

| Document | Status (Oct 2026) | Applies to this CAR-T process? |
|---|---|---|
| FDA, *Computer Software Assurance for Production and Quality Management System Software* | Final Sept 24, 2025; re-issued Feb 3, 2026 with the "Quality Management System" title to align with the QMSR. Issued by CDRH and CBER. | **No.** Scope is software used in *medical device* production or the quality system under 21 CFR 820. It does not address 21 CFR 210/211 or 600-series biologics. CBER co-issuing it doesn't widen the scope. |
| QMSR (21 CFR 820 incorporating ISO 13485:2016) | Effective Feb 2, 2026 | No (device regulation). It is why CSA was retitled. |
| ISPE GAMP 5, 2nd ed. | Published July 2022 | **Yes, as the industry standard** for computerized system validation in GxP. Aligned with CSA's risk-based thinking. |
| 21 CFR 211.68, 21 CFR Part 11 | In force | **Yes (US).** These are the regulatory hooks for computerized systems in drug and biologics manufacturing. |
| EudraLex Vol. 4 **Part IV**, GMP for ATMPs | In force since 2018; revision under discussion (EC concept paper 2025) | **Yes, if EU-facing.** Part IV is a stand-alone GMP for ATMPs, with its own sections on qualification, validation and computerized systems. |
| EU GMP Annex 11 | In force. A revised draft (with Chapter 4 and a new Annex 22 on AI) was published for consultation in July 2025; check current status before presenting. | Not directly applicable to ATMPs under Part IV, but widely used as the reference for computerized systems. |
| ASTM E2500 | Current edition E2500-25 (March 2025) | Yes, as a guide for specification, design and verification of manufacturing systems and equipment. It uses "verification" rather than "qualification". |
| EU GMP Annex 15 | In force | As for Annex 11: a reference for qualification and validation alongside Part IV, not directly binding on ATMPs. |
| FDA, *Process Validation: General Principles and Practices* (2011) | Final | **Yes.** Stage 1 design, Stage 2 process qualification (including PPQ), Stage 3 continued process verification. |
| ICH Q9(R1) | Adopted Jan 2023 | Yes (quality risk management). |
| ICH Q2(R2) / Q14 | Final; FDA adoption announced March 2024 | Yes (analytical procedure validation and development). |
| FDA, *Considerations for the Development of CAR T Cell Products* | Final, Jan 2024 | Yes (CMC expectations, including VCN, potency, comparability). |
| FDA, *Investigating OOS Test Results for Pharmaceutical Production* | Rev. May 2022 (CDER) | **Formally no.** It is scoped to chemistry-based testing; biological and cell-based assays are outside its stated scope. The investigation requirement itself comes from 21 CFR 211.192, and the guidance's principles are commonly applied to cell therapy release testing. |
| USP <1058> | Official title still *Analytical Instrument Qualification*. A lifecycle revision ("…and System Qualification") was proposed in PF 51(2) and is still in progress. | Yes, for the QC instruments (not modeled here; see section 4). |

**How the repo handles it:** `semantic/validation.yaml` describes test methods as SCRIPTED / UNSCRIPTED / SUPPLIER_DOC / INSPECTION and risk as HIGH / MEDIUM / LOW. The terms "high process risk" and "scripted (robust/limited)" are borrowed from CSA as vocabulary, and the docs say so. Nothing claims FDA CSA compliance.

## 2. Your node types, term by term

| Term | Verdict | Issue | What the repo does |
|---|---|---|---|
| `UserRequirement` | ✅ | The URS is the *document*; you're modeling line items, which is right. | Line items in `val_spec_item`, with `doc_no`. |
| `FunctionalSpec` | ⚠️ Scale it | For equipment, the FS is usually the supplier's. For configured software (GAMP Cat. 4) the key document is the **Configuration Specification**. According to ECA's summary of changes, the 2nd edition removed the dedicated FS appendix (D2). A model that requires FS for everything will look dated. | FS kept (supplier FS for incubators, one LIMS function); **`ConfigurationSpec` added** for EMS, LIMS and EBR. |
| `DesignSpec` | ⚠️ Cat. 5 only | Expected mainly for custom code. A DS for an incubator would raise eyebrows. | One DS only: the custom LIMS VCN calculation script (LIMS is "4+5"). |
| `RiskAssessment` (FMEA, S/O/D) | ⚠️ Split it | (a) The thing that links to controls is the **failure mode row**, not the document. (b) Different assessments exist: process FMEA (ICH Q9 tool), functional risk assessment for computerized systems (GAMP), and system impact or criticality assessments for equipment. (c) **RPN:** ICH Q9(R1) doesn't mention RPN, but it names "poorly designed risk scoring scales" as a source of subjectivity and says scores should rest on evidence. Multiplying S×O×D lets a high-severity, low-occurrence failure rank below a nuisance. | `RiskAssessment` (document, `ra_type` pFMEA / FRA) **+ `FailureMode`** (row). `risk_class` is team-assigned and severity-led (S ≥ 8 → HIGH). The demo shows an RPN ≥ 100 rule dropping six S ≥ 8 failure modes. |
| `Protocol (IQ/OQ/PQ/PPQ)` | ⚠️ Different lifecycles | IQ/OQ/PQ are **equipment qualification**. ASTM E2500 calls these activities verification, and the FDA PV guidance talks about "qualification of utilities and equipment" without the IQ/OQ/PQ labels. **PPQ is process validation stage 2.** **"PQ" vs "PPQ" is the most common confusion** in the field. For software, GAMP talks about verification and testing; IQ/OQ/PQ labels are common but not required. Method validation (AMV) is a fourth lifecycle. | `ptype` ∈ IQ, OQ, PQ, PPQ, AMV. The vocabulary states "PQ = equipment performance under routine load, NOT process PQ". Software protocols are titled "functional and configuration testing" even though `ptype` is OQ. |
| `TestCase` | ✅ with nuance | Not every requirement needs a scripted test. GAMP 5 and CSA both support unscripted (ad hoc, error-guessing, exploratory) testing and leveraging supplier documentation for lower-risk functions. | `method` ∈ SCRIPTED, UNSCRIPTED, SUPPLIER_DOC, INSPECTION. The Q1 definition accepts non-scripted evidence for MEDIUM/LOW risk. |
| `TestExecution` | ✅ | Real executions are recorded per *step*, with objective evidence. CSA prefers digital records (system logs, audit trails) to screenshots and warns against excess evidence. | One row per test case per unit. The step level isn't modeled (see section 5). |
| `Deviation` | ⚠️ Too broad | QA distinguishes a **GMP deviation**, a **protocol deviation**, a **test incident / discrepancy** during qualification, an **OOS investigation** (lab, release testing), and an **atypical result** on non-release data. Each has a different procedure and timeline. | One table and label with `record_type`. The ENG low %CAR+ is an ATYPICAL_RESULT, not an OOS, because engineering runs aren't released; their release-panel results are labeled CONFORMS / NONCONFORMING (INFO), not PASS / FAIL. |
| `CAPA` | ✅ | Not every deviation needs a CAPA. A CAPA needs an effectiveness check. | `eff_check` column; some deviations correctly have no CAPA. |
| `ChangeControl` | ✅ | The impact assessment is where revalidation scope is decided, which is exactly what Q2 tests. | `MODIFIES` edges = items listed in the impact assessment. |
| `SOP` | ✅ | | |
| CPP → test case link | ⚠️ Not direct | Nothing in a real package "tests a CPP". CPPs are controlled through the control strategy (risk → controls → verification) and demonstrated in PPQ. | No direct edge. The chain runs through `FailureMode` and `MITIGATED_BY` (see `validation_model.md` §3). |
| Traceability matrix | ✅ as a view | No regulation mandates a matrix as such; traceability is the expectation and the matrix is one way to show it. (Secondary source on GAMP; the 2nd-ed. text wasn't checked directly.) | Not stored. It's a query over the graph. |
| "Validated" vs "qualified" | Wording | Equipment is *qualified*; processes, computerized systems and methods are *validated*. | `val_status` uses QUALIFIED for equipment and VALIDATED for systems. |

## 3. Process and specification claims to watch

- **"VCN < 5 copies/cell" is not an FDA limit.** The 2024 CAR-T guidance says VCN should be determined and reported for each lot, with a release criterion justified by risk assessment.
- **State the VCN basis.** The CAR-T guidance discusses VCN relative to transduced (CAR+) cells as more informative than an average over all cells. The repo reports both: `VCN-DDPCR` (all cells, report only) and `VCN-PER-CAR` (copies per CAR+ cell, calculated in LIMS), and applies the internal ≤ 5.0 limit per CAR+ cell. A limit on a bulk average would let a batch with low %CAR+ and a high copy number per transduced cell pass unnoticed. The figure 5 is an industry convention. The repo labels it an internal specification.
- **Number of PPQ batches:** the FDA PV guidance sets no number (it does not say three). It asks for sufficient statistical confidence and expects concurrent release to be rare.
- **Healthy-donor material:** the CAR-T guidance supports it for developmental batches and notes patient cells may behave differently. No FDA document I found explicitly endorses an all-healthy-donor PPQ for an autologous product. Expect questions on that (see section 5).

## 4. Structural gaps a validation reviewer will notice

These are gaps in the *model*, not errors. They're worth a line in the README so nobody thinks you missed them:

- **No validation plan or summary reports.** A real package has a VMP or validation plan per system and a summary report per protocol, and PPQ has a report that addresses every deviation. The graph has protocols but not these documents.
- **No analytical instrument qualification** (USP <1058>) for the NC-200, ddPCR, flow cytometer and so on. Methods are validated; the instruments they run on aren't modeled.
- **No Stage 3 CPV** and no periodic review of systems.
- **No aseptic process simulation (media fill) or environmental monitoring.** Anyone in cell therapy will ask about these first.
- **No chain of identity / chain of custody** system. For autologous therapy it's arguably the highest-risk computerized system on site. It's omitted because the demo uses healthy-donor runs.
- **Single version of each document.** Real traceability is version-specific (URS v1.0 vs v2.0). The graph holds current versions only.
- **No approval workflow** (author / reviewer / QA approver, Part 11 signature manifestations) on protocols and reports.
- **The graph itself:** if used to make GxP decisions, the graph build and YAML are a computerized system (see `validation_model.md` §4).

## 5. Where the synthetic data is unrealistic (and a QA person would notice)

**Deliberate, for the demo.** Say these out loud before anyone else does:

- **INC-03 kept being used** while its OQ door-alarm test incident (DEV-26-011) had an open, overdue CAPA. OQ-INC-01's report was approved "with exception", PQ mapping then ran on INC-03 in March, and the unit hosted an engineering run and two PPQ batches. In a functioning QMS a documented conditional release would be needed at minimum, and equipment status in the EBR or QA batch review would normally stop PPQ use. It's planted to show the gap; a QA reviewer will read it as a systemic failure, which is the point.
- **Alarm limits don't bracket the CPP range** (not used by the six queries). Incubator and EMS temperature alarms are at ±1.0 °C (36.0 / 38.0 °C), while the CPP acceptance range is 36.5–37.5 °C, so a drift between 36.0 and 36.5 °C would never alarm. This is a real and common gap, and a good candidate for a seventh question: "does every CPP's control and alarm range sit inside its proven range?"
- **DEV-26-021's impact assessment** ("materials remained frozen, low risk, no lots on hold") is weak on purpose.
- **The size of the vector potency loss** (about 60% after roughly 10 h between −60 and −36 °C) is exaggerated so the signal is clean. Real lentiviral stability depends on formulation.
- **The viability drop from the incubator excursion** (8–26 points depending on culture age) is chosen for clarity.

**Simplifications a reviewer will spot:**

- **Compressed timeline.** GMP suite qualification, CSV of three systems, five method validations, engineering runs and a five-batch PPQ, all between January and August.
- **Five healthy-donor PPQ batches** with no patient material and no statistical rationale for the number.
- **Near-perfect first-pass testing.** Only one failed test execution out of 92, and no good-documentation-practice errors. Real first-pass rates are lower.
- **Tests collapsed to one row** per test case per unit: no steps, no objective evidence, and one generic executor and reviewer.
- **Small FMEA** (16 rows; a real CAR-T pFMEA has hundreds). The FRA has one row per requirement with a class but no S/O/D or rationale.
- **Historian data is hourly**, while URS-EMS-010 requires 1-minute acquisition. Treat it as a downsampled export.
- **Identical calibration due dates** across equipment, and no calibration records beyond one quarterly event.
- **No training records,** so CAPA-26-015's "retrain operators" can't be checked for effectiveness.
- **Healthy-donor attributes** (age, CMV status) are random, and there is no donor eligibility documentation.

## Sources

- FDA CSA guidance page and final text: https://www.fda.gov/regulatory-information/search-fda-guidance-documents/computer-software-assurance-production-and-quality-management-system-software · https://www.fda.gov/media/188844/download · Federal Register notice: https://www.federalregister.gov/api/v1/documents/2025-18468.json
- QMSR: https://www.fda.gov/quality-systems-regulation
- GAMP 5 2nd ed. (publisher page): https://ispe.org/publications/guidance-documents/gamp-5-guide-2nd-edition · ECA summary of changes: https://www.gmp-compliance.org/gmp-news/gamp5-2nd-edition-released
- Traceability (secondary, on GAMP): https://www.spectroscopyonline.com/view/validation-spectrometry-software-proactive-use-traceability-matrix-spectrometry-software-validation
- ASTM E2500-25: https://tienda.aenor.com/en/p/norma-astm-e2500-25-120417
- FDA Process Validation (2011): https://www.fda.gov/media/71021/download
- ICH Q9(R1): https://database.ich.org/sites/default/files/ICH_Q9%28R1%29_Guideline_Step4_2023_0126_0.pdf
- ICH Q2(R2) / Q14 FDA notice: https://www.govinfo.gov/content/pkg/FR-2024-03-07/html/2024-04834.htm
- FDA CAR-T guidance (Jan 2024): https://www.hhs.gov/guidance/sites/default/files/hhs-guidance-documents/FDA/Considerations-for-Development-of-Chimeric-Antigen-Receptor-T-Cell-Products_January-2024.pdf
- FDA OOS guidance: https://www.fda.gov/regulatory-information/search-fda-guidance-documents/investigating-out-specification-test-results-pharmaceutical-production
- USP <1058> proposed revision: https://www.gmp-compliance.org/gmp-news/proposed-update-to-usp-1058-on-analytical-instrument-and-system-qualification · status: https://www.uspnf.com/sites/default/files/usp_pdf/EN/USPNF/usp-nf-commentary/usp-nf-2026-issue-3-deferrals.pdf
- PQ vs PPQ (industry): https://kneat.com/article/mastering-iq-oq-pq-and-ppq/
- FDA draft comparability guidance for CGT (July 2023): https://fda.gov/media/170198/download
