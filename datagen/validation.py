"""Synthetic validation and QMS records tied to the process data.

Everything here is hand-authored on purpose: validation packages are
documents, not random draws. The planted gaps the demo queries look for:

  G1  URS-EMS-014 (after-hours alarm escalation) was tested in January,
      then CC-26-011 changed the notification configuration in March with
      "no re-testing required". The verification is stale.
  G2  URS-EBR-009 (MOI range check) is configured (CS-EBR-03) but has no
      test case at all.
  G3  URS-INC-004 (door-open alarm) failed OQ on INC-03 (DEV-26-011).
      CAPA-26-012 / CC-26-019 to fix and re-test it are still open, so the
      requirement is verified on INC-01, 02, 04 but not on INC-03.
  G4  High-criticality failure modes FM-02 (Prodigy program) and FM-13
      (CRF freeze profile) are controlled by performance requirements that
      have OQ test cases but no PQ test case. The FMEA's free-text
      "current controls" column claims otherwise.
  G5  DEV-26-021 (freezer) and DEV-26-033 (incubator) have different
      recorded root causes; both trace back to CC-26-011 on the EMS.
  G6  CC-26-022 (raise MOI 5 -> 8) lists one impacted item; the graph
      finds many more.
  G7  PPQ26-03 was in INC-03 during the excursion (CPP out of range during
      PPQ) with no deviation raised.
  Decoys (should NOT be flagged): low-risk requirements verified by supplier
  documentation or inspection; high-risk requirements verified only through
  their FS / CS / DS children.
"""
from __future__ import annotations

from datetime import date


def build(proc: dict[str, list[dict]]) -> dict[str, list[dict]]:
    T: dict[str, list[dict]] = {}
    links: list[dict] = []

    def add(table, **row):
        T.setdefault(table, []).append(row)

    def link(st, s, lt, tt, t):
        links.append(dict(src_type=st, src_id=s, link_type=lt, tgt_type=tt, tgt_id=t))

    # ------------------------------------------------------------------
    # Systems
    # ------------------------------------------------------------------
    systems = [
        ("SYS-INC", "CO2 incubators, GMP Suite 2", "EQUIPMENT", "3", "QUALIFIED"),
        ("SYS-ULT", "-80 C ULT freezers, warehouse", "EQUIPMENT", "3", "QUALIFIED"),
        ("SYS-PRDG", "CliniMACS Prodigy, GMP Suite 2", "EQUIPMENT", "4", "QUALIFIED"),
        ("SYS-LOVO", "LOVO cell processing system", "EQUIPMENT", "4", "QUALIFIED"),
        ("SYS-CRF", "Controlled-rate freezer", "EQUIPMENT", "4", "QUALIFIED"),
        ("SYS-EMS", "Equipment monitoring system (EMS)", "COMPUTERIZED", "4", "VALIDATED"),
        ("SYS-LIMS", "QC laboratory information management system", "COMPUTERIZED", "4+5", "VALIDATED"),
        ("SYS-EBR", "Electronic batch record (MES)", "COMPUTERIZED", "4", "VALIDATED"),
    ]
    for sid, name, cls, cat, st in systems:
        add("val_system", sys_id=sid, sys_name=name, sys_class=cls, gamp_cat=cat, gxp_area="GMP",
            owner_dept="Manufacturing" if cls == "EQUIPMENT" else "QA / IT", val_status=st)

    # EMS monitoring channels (exported from the EMS channel configuration)
    for eq in ["INC-01", "INC-02", "INC-03", "INC-04", "FRZ-80-01", "FRZ-80-02"]:
        link("SYS", "SYS-EMS", "MONITORS", "EQUIP", eq)

    # ------------------------------------------------------------------
    # Specifications: URS / FS / CS / DS
    # (item_id, level, sys, category, text, source, approved)
    # ------------------------------------------------------------------
    S = [
        # --- incubators
        ("URS-INC-001", "URS", "SYS-INC", "PERFORMANCE", "Chamber temperature shall be controlled at 37.0 C with uniformity of +/-0.5 C across the usable volume under loaded conditions."),
        ("URS-INC-002", "URS", "SYS-INC", "PERFORMANCE", "CO2 concentration shall be controlled at 5.0% +/-0.5%."),
        ("URS-INC-003", "URS", "SYS-INC", "ALARM", "High and low temperature alarms shall activate at +/-1.0 C from setpoint, locally and via dry contact to the EMS."),
        ("URS-INC-004", "URS", "SYS-INC", "ALARM", "A door-open alarm shall activate when the door is open for more than 60 s."),
        ("URS-INC-005", "URS", "SYS-INC", "PERFORMANCE", "Temperature shall recover to within +/-0.5 C of setpoint within 15 min after a 30 s door opening."),
        ("URS-INC-006", "URS", "SYS-INC", "PHYSICAL", "Interior surfaces shall be cleanable with the site sporicidal agent."),
        ("URS-INC-007", "URS", "SYS-INC", "INTERFACE", "The incubator shall provide a dry-contact alarm output compatible with the EMS."),
        ("FS-INC-01", "FS", "SYS-INC", "PERFORMANCE", "Supplier FS: PID temperature control, uniformity +/-0.3 C (empty chamber)."),
        ("FS-INC-02", "FS", "SYS-INC", "ALARM", "Supplier FS: configurable high/low temperature alarms, relay output."),
        ("FS-INC-04", "FS", "SYS-INC", "ALARM", "Supplier FS: door switch and door-open alarm delay (configurable)."),
        ("FS-INC-03", "FS", "SYS-INC", "PERFORMANCE", "Supplier FS: thermal-conductivity CO2 sensor and control loop."),
        # --- ULT freezers
        ("URS-ULT-001", "URS", "SYS-ULT", "PERFORMANCE", "Chamber shall be maintained at or below -70 C (setpoint -80 C) at all mapped locations under load."),
        ("URS-ULT-002", "URS", "SYS-ULT", "ALARM", "A high-temperature alarm shall activate at -70 C, locally and via the EMS."),
        ("URS-ULT-003", "URS", "SYS-ULT", "PERFORMANCE", "Temperature shall recover to below -70 C within 30 min after a 60 s door opening."),
        ("URS-ULT-004", "URS", "SYS-ULT", "PHYSICAL", "The freezer shall have an independent battery-backed temperature display."),
        ("URS-ULT-005", "URS", "SYS-ULT", "PHYSICAL", "The freezer door shall be lockable."),
        # --- Prodigy
        ("URS-PRDG-001", "URS", "SYS-PRDG", "PERFORMANCE", "Cell selection shall be performed in a closed, single-use tubing set without breach of sterility."),
        ("URS-PRDG-002", "URS", "SYS-PRDG", "PERFORMANCE", "The CD4/CD8 enrichment program shall run with locked, version-controlled parameters and deliver purity >= 90% CD3+."),
        ("URS-PRDG-003", "URS", "SYS-PRDG", "SECURITY", "Program editing shall be restricted by user role."),
        ("URS-PRDG-004", "URS", "SYS-PRDG", "DATA", "The process log shall be exportable with a tamper-evident audit trail."),
        ("URS-PRDG-005", "URS", "SYS-PRDG", "PERFORMANCE", "Centrifugation and wash steps shall meet supplier specification."),
        # --- LOVO
        ("URS-LOVO-001", "URS", "SYS-LOVO", "PERFORMANCE", "Wash shall achieve >= 85% viable cell recovery."),
        ("URS-LOVO-002", "URS", "SYS-LOVO", "PERFORMANCE", "Processing shall be closed."),
        # --- CRF
        ("URS-CRF-001", "URS", "SYS-CRF", "PERFORMANCE", "The freezer shall execute freezing profile CRF-P01 within +/-2 C of the programmed curve with a representative load."),
        ("URS-CRF-002", "URS", "SYS-CRF", "DATA", "Chamber and sample-probe temperatures shall be recorded for the batch record."),
        ("URS-CRF-003", "URS", "SYS-CRF", "ALARM", "An alarm shall activate on LN2 supply failure."),
        # --- EMS
        ("URS-EMS-010", "URS", "SYS-EMS", "DATA", "The EMS shall acquire temperature and CO2 from monitored equipment at intervals of 1 min or less."),
        ("URS-EMS-011", "URS", "SYS-EMS", "ALARM", "The EMS shall raise an alarm when a value exceeds its configured limit for the configured delay."),
        ("URS-EMS-012", "URS", "SYS-EMS", "CONTROL", "Alarm limits and delays shall be configured per equipment as defined in the configuration specification."),
        ("URS-EMS-013", "URS", "SYS-EMS", "DATA", "The EMS shall keep an audit trail of configuration changes and alarm acknowledgements."),
        ("URS-EMS-014", "URS", "SYS-EMS", "ALARM", "Unacknowledged critical alarms shall be escalated to on-call personnel by SMS and voice call within 15 min, 24/7."),
        ("URS-EMS-015", "URS", "SYS-EMS", "DATA", "The EMS shall generate monthly excursion summary reports."),
        ("URS-EMS-016", "URS", "SYS-EMS", "DATA", "Data shall be retained for product shelf life plus one year."),
        ("CS-EMS-01", "CS", "SYS-EMS", "DATA", "Channel map: INC01-INC04 TEMP/CO2, FRZ8001-FRZ8002 TEMP; 1 min scan."),
        ("CS-EMS-02", "CS", "SYS-EMS", "ALARM", "Alarm limits: INC TEMP 36.0/38.0 C delay 5 min; INC CO2 4.0/6.0%; FRZ TEMP -70 C delay 10 min; door 60 s."),
        ("CS-EMS-03", "CS", "SYS-EMS", "ALARM", "Notification groups and escalation: tier 0 local, tier 1 GRP-ONCALL-MFG at +15 min, tier 2 supervisor at +30 min."),
        ("CS-EMS-04", "CS", "SYS-EMS", "DATA", "Audit trail enabled for configuration and acknowledgement events."),
        # --- LIMS
        ("URS-LIMS-001", "URS", "SYS-LIMS", "DATA", "Results shall be recorded with analyst, date/time and instrument ID."),
        ("URS-LIMS-002", "URS", "SYS-LIMS", "CONTROL", "Results shall require second-person review before approval."),
        ("URS-LIMS-003", "URS", "SYS-LIMS", "CONTROL", "Results shall be compared to specification and out-of-specification results flagged automatically."),
        ("URS-LIMS-004", "URS", "SYS-LIMS", "CONTROL", "VCN shall be calculated from ddPCR transgene and reference copies per SOP-QC-201."),
        ("URS-LIMS-005", "URS", "SYS-LIMS", "DATA", "A certificate of analysis shall be generated from approved results only."),
        ("URS-LIMS-006", "URS", "SYS-LIMS", "DATA", "Changes to results shall be captured in an audit trail."),
        ("URS-LIMS-007", "URS", "SYS-LIMS", "DATA", "Reports shall be exportable to PDF."),
        ("CS-LIMS-01", "CS", "SYS-LIMS", "CONTROL", "Specification tables and OOS flag rules for release tests."),
        ("CS-LIMS-02", "CS", "SYS-LIMS", "CONTROL", "Result review and approval workflow."),
        ("FS-LIMS-01", "FS", "SYS-LIMS", "CONTROL", "VCN calculation function: VCN = 2 x (transgene copies / reference copies)."),
        ("DS-LIMS-01", "DS", "SYS-LIMS", "CONTROL", "Design of custom VCN calculation script (LIMS extension, Category 5)."),
        # --- EBR
        ("URS-EBR-001", "URS", "SYS-EBR", "CONTROL", "The EBR shall enforce step sequence per the master batch record."),
        ("URS-EBR-002", "URS", "SYS-EBR", "CONTROL", "Material scans shall verify released status and expiry."),
        ("URS-EBR-003", "URS", "SYS-EBR", "CONTROL", "Equipment scans shall verify qualification and calibration status."),
        ("URS-EBR-007", "URS", "SYS-EBR", "CONTROL", "Vector volume shall be calculated from target MOI, viable cell count and CoA functional titer."),
        ("URS-EBR-008", "URS", "SYS-EBR", "SECURITY", "Electronic signatures shall meet 21 CFR Part 11."),
        ("URS-EBR-009", "URS", "SYS-EBR", "CONTROL", "Target MOI outside 4.0-6.0 TU/cell shall be rejected for GMP runs."),
        ("URS-EBR-010", "URS", "SYS-EBR", "DATA", "Incubator ID and placement time shall be recorded for each culture vessel."),
        ("CS-EBR-01", "CS", "SYS-EBR", "CONTROL", "Master batch record recipe configuration (step sequence)."),
        ("CS-EBR-02", "CS", "SYS-EBR", "CONTROL", "Calculation configuration: vector volume = MOI x cells / functional titer."),
        ("CS-EBR-03", "CS", "SYS-EBR", "CONTROL", "Range check configuration: MOI 4.0-6.0 TU/cell, hard stop."),
    ]
    approved = {"SYS-INC": date(2025, 11, 20), "SYS-ULT": date(2025, 11, 20), "SYS-PRDG": date(2025, 12, 1),
                "SYS-LOVO": date(2025, 12, 1), "SYS-CRF": date(2025, 12, 1), "SYS-EMS": date(2025, 12, 10),
                "SYS-LIMS": date(2026, 1, 8), "SYS-EBR": date(2026, 2, 2)}
    for iid, lvl, sid, cat, text in S:
        add("val_spec_item", item_id=iid, spec_level=lvl, doc_no=f"{lvl}-{sid[4:]}", doc_ver="1.0", sys_id=sid,
            req_category=cat, item_text=text, source="SUPPLIER" if lvl == "FS" and sid.startswith("SYS-INC") else "SITE",
            approved_dt=approved[sid])
    for child, parent in [("FS-INC-01", "URS-INC-001"), ("FS-INC-02", "URS-INC-003"), ("FS-INC-04", "URS-INC-004"),
                          ("FS-INC-03", "URS-INC-002"), ("CS-EMS-01", "URS-EMS-010"), ("CS-EMS-02", "URS-EMS-011"),
                          ("CS-EMS-02", "URS-EMS-012"), ("CS-EMS-03", "URS-EMS-014"), ("CS-EMS-04", "URS-EMS-013"),
                          ("CS-LIMS-01", "URS-LIMS-003"), ("CS-LIMS-02", "URS-LIMS-002"), ("FS-LIMS-01", "URS-LIMS-004"),
                          ("DS-LIMS-01", "FS-LIMS-01"), ("CS-EBR-01", "URS-EBR-001"), ("CS-EBR-02", "URS-EBR-007"),
                          ("CS-EBR-03", "URS-EBR-009")]:
        link("SPEC", child, "TRACE", "SPEC", parent)

    # ------------------------------------------------------------------
    # SOPs
    # ------------------------------------------------------------------
    sops = [
        ("SOP-MFG-101", "Apheresis receipt and inspection", "Apheresis receipt", None),
        ("SOP-MFG-102", "CD4/CD8 selection on CliniMACS Prodigy", "T cell selection", "SYS-PRDG"),
        ("SOP-MFG-103", "T cell activation and seeding", "Activation", None),
        ("SOP-MFG-104", "Lentiviral transduction: vector thaw, MOI calculation and addition", "Transduction", None),
        ("SOP-MFG-105", "Expansion in G-Rex vessels and incubator use", "Expansion", "SYS-INC"),
        ("SOP-MFG-106", "Harvest and wash on LOVO", "Harvest", "SYS-LOVO"),
        ("SOP-MFG-107", "Formulation, fill and controlled-rate freezing", "Formulation and fill", "SYS-CRF"),
        ("SOP-MAT-401", "Storage and handling of viral vector", None, "SYS-ULT"),
        ("SOP-FAC-301", "Equipment alarm response and escalation", None, "SYS-EMS"),
        ("SOP-QC-201", "VCN by ddPCR", None, None),
        ("SOP-QC-202", "CAR expression by flow cytometry", None, None),
    ]
    for sid, title, step, sys_id in sops:
        add("sop", sop_id=sid, title=title, doc_ver="3.0" if sid in ("SOP-MFG-103", "SOP-MFG-105", "SOP-MFG-106") else "2.0",
            effective_dt=date(2026, 5, 1) if sid in ("SOP-MFG-103", "SOP-MFG-105", "SOP-MFG-106") else date(2026, 1, 5),
            owner_dept="QC" if "QC" in sid else "Manufacturing", process_step=step, sys_id=sys_id)

    # ------------------------------------------------------------------
    # Analytical methods
    # ------------------------------------------------------------------
    methods = [
        ("AM-FC-CAR", "CAR expression by flow cytometry", "Flow cytometry", "FC-CAR", 5, 90, "% of CD3+"),
        ("AM-VCN", "Vector copy number by ddPCR", "ddPCR", "VCN-DDPCR", 0.1, 6.0, "copies/cell"),
        ("AM-POT", "IFN-gamma release after CD19+ target co-culture", "Co-culture + ELISA", "POT-IFNG", 500, 25000, "pg/mL"),
        ("AM-VIAB", "Viability by NC-200 (AO/DAPI)", "Image cytometry", "VIAB-NC200", 20, 100, "%"),
        ("AM-CD3", "CD3 purity by flow cytometry", "Flow cytometry", "FC-CD3", 50, 100, "%"),
    ]
    for mid, name, tech, code, lo, hi, uom in methods:
        add("analytical_method", method_id=mid, method_name=name, technique=tech, qc_test_code=code,
            val_range_lo=lo, val_range_hi=hi, uom=uom, status="VALIDATED")

    # ------------------------------------------------------------------
    # Risk assessments
    # ------------------------------------------------------------------
    add("val_risk_assessment", ra_id="RA-PFMEA-001", ra_type="pFMEA", title="Process FMEA, CAR-T process PV2.0",
        sys_id=None, doc_ver="2.0", approved_dt=date(2026, 4, 28))
    for sid, _, cls, _, _ in systems:
        add("val_risk_assessment", ra_id=f"RA-FRA-{sid[4:]}", ra_type="FRA",
            title=f"Functional risk assessment, {sid}", sys_id=sid, doc_ver="1.0", approved_dt=approved[sid])

    # pFMEA rows: free-text columns written the way a cross-functional team
    # fills a spreadsheet (synonyms, abbreviations, several CQAs per cell).
    P = [
        # id, step, parameter, failure mode, effect, cqa text, cause, S, O, D, controls (free text), mitigated by
        ("FM-01", "Apheresis receipt", "Apheresis hold time", "Hold time > 48 h", "Reduced T cell fitness", "Viability; Fold expansion",
         "Courier delay", 7, 3, 3, "Courier SOP, receipt check", ["SOP-MFG-101"]),
        ("FM-02", "T cell selection", "Selection program parameters", "Wrong or edited program run", "Low purity, skewed CD4:CD8",
         "CD3 purity; CD4/CD8 ratio", "Program not locked", 8, 3, 5, "Locked programs, Prodigy OQ/PQ", ["URS-PRDG-002", "SOP-MFG-102"]),
        ("FM-03", "T cell selection", "Tubing set integrity", "Breach of closed system", "Contamination", "Sterility",
         "Defective tubing set", 10, 2, 4, "Closed system verified in Prodigy OQ and PQ", ["URS-PRDG-001"]),
        ("FM-04", "Activation", "Seeding density", "Seeding density outside 0.4-0.6 x10^6/mL", "Altered expansion and phenotype",
         "Tscm; Fold expansion", "Counting error", 6, 4, 4, "NC-200 count, second-person check", ["SOP-MFG-103"]),
        ("FM-05", "Transduction", "MOI (TU/cell)", "MOI above target", "Excess integrations", "VCN",
         "Calculation error, titer under-estimated", 9, 3, 4, "EBR vector volume calculation; second-person verification",
         ["URS-EBR-007", "URS-EBR-009", "SOP-MFG-104"]),
        ("FM-06", "Transduction", "MOI (TU/cell)", "MOI below target", "Low transduction", "%CAR+; Potency",
         "Titer over-estimated, vector degradation", 8, 4, 4, "EBR calculation; CoA titer", ["URS-EBR-007", "SOP-MFG-104"]),
        ("FM-07", "Transduction", "Vector storage temperature", "Vector held above -70 C", "Loss of functional titer",
         "Transduction efficiency; VCN", "ULT freezer failure", 8, 2, 6, "ULT qualification; EMS alarms",
         ["URS-ULT-001", "URS-ULT-002", "URS-EMS-014", "SOP-MAT-401"]),
        ("FM-08", "Transduction", "Time from activation to transduction", "Transduction outside 20-30 h", "Lower transduction",
         "TE", "Scheduling", 6, 3, 3, "Batch record timing check", ["SOP-MFG-104"]),
        ("FM-09", "Expansion", "Incubator temperature", "Temperature below 36.5 C", "Reduced growth and viability",
         "Viability; Fold expansion", "Incubator failure, door not closed", 8, 3, 4, "Incubator OQ/PQ; EMS alarms; SOP-MFG-105",
         ["URS-INC-001", "URS-INC-003", "URS-EMS-011", "URS-EMS-014", "SOP-MFG-105"]),
        ("FM-10", "Expansion", "CO2 %", "CO2 outside 4.5-5.5%", "pH drift, reduced growth", "Fold expansion",
         "Sensor drift", 5, 3, 4, "Incubator OQ; quarterly calibration", ["URS-INC-002"]),
        ("FM-11", "Expansion", "Culture duration", "Harvest outside day 7-9", "Altered phenotype and dose",
         "Tscm; CAR+ viable cell dose", "Scheduling", 6, 2, 2, "Batch record", ["SOP-MFG-106"]),
        ("FM-12", "Harvest", "Wash", "Excess cell loss during wash", "Low dose", "CAR+ viable cell dose",
         "LOVO malfunction", 6, 3, 3, "LOVO OQ/PQ", ["URS-LOVO-001"]),
        ("FM-13", "Formulation and fill", "Freeze profile", "Deviation from programmed freeze curve", "Low post-thaw viability",
         "Post-thaw viability", "Profile error, probe placement", 8, 3, 5, "CRF OQ; PQ by engineering runs", ["URS-CRF-001"]),
        ("FM-14", "QC release", "VCN calculation", "VCN mis-calculated in LIMS", "Wrong release decision", "VCN",
         "Script error", 9, 2, 5, "LIMS validation", ["URS-LIMS-004"]),
        ("FM-15", "QC release", "OOS flagging", "OOS result not flagged", "Release of non-conforming lot",
         "Viability; %CAR+; VCN; CD3 purity", "Specification table error", 10, 2, 4, "LIMS validation; second-person review",
         ["URS-LIMS-003", "URS-LIMS-002"]),
        ("FM-16", "Expansion", "Incubator door", "Door left open or unlatched", "Temperature and CO2 loss",
         "Viability; Fold expansion", "Human error", 8, 4, 3, "Door alarm; EMS escalation; operator training",
         ["URS-INC-004", "URS-EMS-014", "SOP-MFG-105"]),
    ]

    def risk_class(s, o, d):
        # Team rule (documented in the pFMEA): severity-led, not RPN-led.
        if s >= 8:
            return "HIGH"
        if s >= 5 and s * o * d >= 50:
            return "MEDIUM"
        return "LOW"

    for fid, step, par, fm, eff, cqa, cause, s, o, d, ctl, mit in P:
        add("val_risk_item", ri_id=fid, ra_id="RA-PFMEA-001", process_step=step, parameter_txt=par, failure_mode=fm,
            effect=eff, cqa_impacted=cqa, cause=cause, sev=s, occ=o, det=d, rpn=s * o * d,
            risk_class=risk_class(s, o, d), current_controls=ctl, assurance_approach=None)
        for m in mit:
            link("RISK", fid, "MITIGATES", "SOP" if m.startswith("SOP") else "SPEC", m)

    # FRA rows: one per URS. Risk class drives assurance approach (CSA-style).
    fra_low = {"URS-INC-006": "INSPECTION", "URS-ULT-004": "SUPPLIER_DOC", "URS-ULT-005": "INSPECTION",
               "URS-EMS-015": "UNSCRIPTED", "URS-EMS-016": "SUPPLIER_DOC", "URS-LIMS-007": "UNSCRIPTED"}
    fra_med = {"URS-INC-002", "URS-INC-005", "URS-INC-007", "URS-ULT-003", "URS-PRDG-003", "URS-PRDG-004",
               "URS-PRDG-005", "URS-LOVO-001", "URS-CRF-002", "URS-CRF-003", "URS-EBR-010"}
    n = 0
    for iid, lvl, sid, cat, text in S:
        if lvl != "URS":
            continue
        n += 1
        if iid in fra_low:
            rc, sev, approach = "LOW", 3, fra_low[iid]
        elif iid in fra_med:
            rc, sev, approach = "MEDIUM", 6, "SCRIPTED (limited)"
        else:
            rc, sev, approach = "HIGH", 9, "SCRIPTED (robust)"
        rid = f"FRA-{n:03d}"
        add("val_risk_item", ri_id=rid, ra_id=f"RA-FRA-{sid[4:]}", process_step=None, parameter_txt=None,
            failure_mode=f"Function fails: {text[:70]}", effect="Product quality / data integrity impact",
            cqa_impacted=None, cause=None, sev=sev, occ=None, det=None, rpn=None, risk_class=rc,
            current_controls=None, assurance_approach=approach)
        link("RISK", rid, "ASSESSES", "SPEC", iid)

    # ------------------------------------------------------------------
    # Protocols, test cases, executions
    # ------------------------------------------------------------------
    protos = [
        # id, type, title, sys, method, approved, status
        ("IQ-INC-01", "IQ", "Installation qualification, CO2 incubators", "SYS-INC", None, date(2026, 1, 12)),
        ("OQ-INC-01", "OQ", "Operational qualification, CO2 incubators", "SYS-INC", None, date(2026, 1, 26)),
        ("PQ-INC-01", "PQ", "Performance qualification (loaded mapping), CO2 incubators", "SYS-INC", None, date(2026, 2, 23)),
        ("IQ-ULT-01", "IQ", "Installation qualification, ULT freezers", "SYS-ULT", None, date(2026, 1, 12)),
        ("OQ-ULT-01", "OQ", "Operational qualification, ULT freezers", "SYS-ULT", None, date(2026, 1, 20)),
        ("PQ-ULT-01", "PQ", "Performance qualification (loaded mapping), ULT freezers", "SYS-ULT", None, date(2026, 2, 9)),
        ("IQ-PRDG-01", "IQ", "Installation qualification, CliniMACS Prodigy", "SYS-PRDG", None, date(2026, 1, 15)),
        ("OQ-PRDG-01", "OQ", "Operational qualification, CliniMACS Prodigy", "SYS-PRDG", None, date(2026, 2, 2)),
        ("PQ-PRDG-01", "PQ", "Performance qualification (closed processing), CliniMACS Prodigy", "SYS-PRDG", None, date(2026, 3, 2)),
        ("IQ-LOVO-01", "IQ", "Installation qualification, LOVO", "SYS-LOVO", None, date(2026, 1, 15)),
        ("OQ-LOVO-01", "OQ", "Operational qualification, LOVO", "SYS-LOVO", None, date(2026, 2, 2)),
        ("PQ-LOVO-01", "PQ", "Performance qualification, LOVO", "SYS-LOVO", None, date(2026, 3, 2)),
        ("IQ-CRF-01", "IQ", "Installation qualification, controlled-rate freezer", "SYS-CRF", None, date(2026, 1, 22)),
        ("OQ-CRF-01", "OQ", "Operational qualification, controlled-rate freezer", "SYS-CRF", None, date(2026, 2, 9)),
        ("IQ-EMS-01", "IQ", "Installation verification, EMS", "SYS-EMS", None, date(2026, 1, 5)),
        ("OQ-EMS-01", "OQ", "Functional and configuration testing, EMS", "SYS-EMS", None, date(2026, 1, 12)),
        ("OQ-LIMS-01", "OQ", "Functional and configuration testing, LIMS", "SYS-LIMS", None, date(2026, 2, 2)),
        ("OQ-EBR-01", "OQ", "Functional and configuration testing, EBR", "SYS-EBR", None, date(2026, 3, 9)),
        ("AMV-FC-CAR-01", "AMV", "Method validation, CAR expression by flow", None, "AM-FC-CAR", date(2026, 3, 2)),
        ("AMV-VCN-01", "AMV", "Method validation, VCN by ddPCR", None, "AM-VCN", date(2026, 3, 2)),
        ("AMV-POT-01", "AMV", "Method validation, IFN-gamma potency", None, "AM-POT", date(2026, 3, 16)),
        ("AMV-VIAB-01", "AMV", "Method validation, viability (NC-200)", None, "AM-VIAB", date(2026, 2, 16)),
        ("AMV-CD3-01", "AMV", "Method validation, CD3 purity by flow", None, "AM-CD3", date(2026, 3, 2)),
        ("PPQ-001", "PPQ", "Process performance qualification, CAR-T process PV2.0", None, None, date(2026, 5, 22)),
    ]
    for pid, pt, title, sid, mid, ad in protos:
        status = "EXECUTION COMPLETE - REPORT PENDING" if pt == "PPQ" else "APPROVED - REPORT APPROVED"
        if pid == "OQ-INC-01":
            status = "REPORT APPROVED WITH EXCEPTION (INC-03 TC-OQ-INC-04, DEV-26-011)"
        add("val_protocol", protocol_id=pid, ptype=pt, title=title, sys_id=sid, method_id=mid, doc_ver="1.0",
            approved_dt=ad, status=status)

    units = {"SYS-INC": ["INC-01", "INC-02", "INC-03", "INC-04"], "SYS-ULT": ["FRZ-80-01", "FRZ-80-02"],
             "SYS-PRDG": ["PRDG-01", "PRDG-02"], "SYS-LOVO": ["LOVO-01"], "SYS-CRF": ["CRF-01"],
             "SYS-EMS": ["SYS-EMS"], "SYS-LIMS": ["SYS-LIMS"], "SYS-EBR": ["SYS-EBR"]}
    proto_sys = {p[0]: p[3] for p in protos}

    TC = [
        # tc, protocol, title, method, acceptance, lo, hi, uom, verifies[], exec date
        ("TC-IQ-INC-01", "IQ-INC-01", "Installation and EMS dry-contact wiring", "SCRIPTED", "Wired and alarm received at EMS", None, None, None, ["URS-INC-007"], date(2026, 1, 14)),
        ("TC-IQ-INC-02", "IQ-INC-01", "Surface finish inspection", "INSPECTION", "Compatible with sporicidal agent", None, None, None, ["URS-INC-006"], date(2026, 1, 14)),
        ("TC-OQ-INC-01", "OQ-INC-01", "Temperature control at setpoint (empty)", "SCRIPTED", "37.0 +/-0.5 C at 9 probes", 36.0, 38.0, "C", ["URS-INC-001", "FS-INC-01"], date(2026, 2, 3)),
        ("TC-OQ-INC-02", "OQ-INC-01", "CO2 control", "SCRIPTED", "5.0 +/-0.5%", 4.0, 6.0, "%", ["URS-INC-002", "FS-INC-03"], date(2026, 2, 4)),
        ("TC-OQ-INC-03", "OQ-INC-01", "High/low temperature alarms", "SCRIPTED", "Alarm at +/-1.0 C, local and EMS", None, None, None, ["URS-INC-003", "FS-INC-02"], date(2026, 2, 5)),
        ("TC-OQ-INC-04", "OQ-INC-01", "Door-open alarm", "SCRIPTED", "Alarm activates <= 60 s after door opened", None, None, None, ["URS-INC-004"], date(2026, 2, 10)),
        ("TC-OQ-INC-05", "OQ-INC-01", "Door-opening recovery", "SCRIPTED", "Recovery <= 15 min", None, None, None, ["URS-INC-005"], date(2026, 2, 11)),
        ("TC-PQ-INC-01", "PQ-INC-01", "Loaded chamber temperature mapping, 24 h, 9 probes", "SCRIPTED", "All probes 36.5-37.5 C", 36.5, 37.5, "C", ["URS-INC-001"], date(2026, 3, 3)),
        ("TC-IQ-ULT-01", "IQ-ULT-01", "Independent display: supplier certificate review", "SUPPLIER_DOC", "Supplier documentation confirms feature", None, None, None, ["URS-ULT-004"], date(2026, 1, 14)),
        ("TC-IQ-ULT-02", "IQ-ULT-01", "Door lock inspection", "INSPECTION", "Lock present and functional", None, None, None, ["URS-ULT-005"], date(2026, 1, 14)),
        ("TC-OQ-ULT-01", "OQ-ULT-01", "Pull-down and hold (empty)", "SCRIPTED", "<= -70 C at all probes", -90, -70, "C", ["URS-ULT-001"], date(2026, 1, 21)),
        ("TC-OQ-ULT-02", "OQ-ULT-01", "High-temperature alarm", "SCRIPTED", "Alarm at -70 C, local and EMS", None, None, None, ["URS-ULT-002"], date(2026, 1, 22)),
        ("TC-OQ-ULT-03", "OQ-ULT-01", "Door-opening recovery", "SCRIPTED", "Recovery <= 30 min", None, None, None, ["URS-ULT-003"], date(2026, 1, 22)),
        ("TC-PQ-ULT-01", "PQ-ULT-01", "Loaded mapping, 72 h, 15 probes", "SCRIPTED", "All probes <= -70 C", -90, -70, "C", ["URS-ULT-001"], date(2026, 2, 12)),
        ("TC-IQ-PRDG-01", "IQ-PRDG-01", "Installation per supplier checklist", "SCRIPTED", "Complete", None, None, None, [], date(2026, 1, 16)),
        ("TC-OQ-PRDG-01", "OQ-PRDG-01", "Tubing set integrity / pressure test", "SCRIPTED", "No leak", None, None, None, ["URS-PRDG-001"], date(2026, 2, 4)),
        ("TC-OQ-PRDG-02", "OQ-PRDG-01", "Program lock and version check", "SCRIPTED", "Locked program cannot be edited; version displayed", None, None, None, ["URS-PRDG-002"], date(2026, 2, 4)),
        ("TC-OQ-PRDG-03", "OQ-PRDG-01", "Role-based access", "SCRIPTED", "Operator role cannot edit programs", None, None, None, ["URS-PRDG-003"], date(2026, 2, 5)),
        ("TC-OQ-PRDG-04", "OQ-PRDG-01", "Process log export and audit trail", "SCRIPTED", "Log complete; edits audited", None, None, None, ["URS-PRDG-004"], date(2026, 2, 5)),
        ("TC-OQ-PRDG-05", "OQ-PRDG-01", "Centrifugation and wash function", "SCRIPTED", "Per supplier specification", None, None, None, ["URS-PRDG-005"], date(2026, 2, 6)),
        ("TC-PQ-PRDG-01", "PQ-PRDG-01", "Closed processing, 3 consecutive media runs", "SCRIPTED", "Sterility no growth, no breach", None, None, None, ["URS-PRDG-001"], date(2026, 3, 5)),
        ("TC-IQ-LOVO-01", "IQ-LOVO-01", "Installation per supplier checklist", "SCRIPTED", "Complete", None, None, None, [], date(2026, 1, 16)),
        ("TC-OQ-LOVO-01", "OQ-LOVO-01", "Closed processing and wash function", "SCRIPTED", "No breach; function per spec", None, None, None, ["URS-LOVO-002"], date(2026, 2, 6)),
        ("TC-PQ-LOVO-01", "PQ-LOVO-01", "Wash recovery with representative cells, 3 runs", "SCRIPTED", ">= 85% recovery", 85, 100, "%", ["URS-LOVO-001", "URS-LOVO-002"], date(2026, 3, 10)),
        ("TC-IQ-CRF-01", "IQ-CRF-01", "Installation and LN2 supply per supplier checklist", "SCRIPTED", "Complete", None, None, None, [], date(2026, 1, 23)),
        ("TC-OQ-CRF-01", "OQ-CRF-01", "Profile CRF-P01 execution (empty chamber)", "SCRIPTED", "Within +/-2 C of programmed curve", None, None, None, ["URS-CRF-001"], date(2026, 2, 11)),
        ("TC-OQ-CRF-02", "OQ-CRF-01", "Temperature data recording", "SCRIPTED", "Data complete and exportable", None, None, None, ["URS-CRF-002"], date(2026, 2, 11)),
        ("TC-OQ-CRF-03", "OQ-CRF-01", "LN2 supply failure alarm", "SCRIPTED", "Alarm activates", None, None, None, ["URS-CRF-003"], date(2026, 2, 12)),
        ("TC-IQ-EMS-01", "IQ-EMS-01", "Install and channel configuration", "SCRIPTED", "All channels reporting", None, None, None, ["CS-EMS-01"], date(2026, 1, 7)),
        ("TC-OQ-EMS-01", "OQ-EMS-01", "Acquisition interval", "SCRIPTED", "<= 1 min", None, None, None, ["URS-EMS-010", "CS-EMS-01"], date(2026, 1, 14)),
        ("TC-OQ-EMS-02", "OQ-EMS-01", "Alarm limits and delays", "SCRIPTED", "Alarms per CS-EMS-02", None, None, None, ["CS-EMS-02"], date(2026, 1, 15)),
        ("TC-OQ-EMS-03", "OQ-EMS-01", "Audit trail", "SCRIPTED", "Config changes and acks audited", None, None, None, ["URS-EMS-013", "CS-EMS-04"], date(2026, 1, 16)),
        ("TC-OQ-EMS-04", "OQ-EMS-01", "Alarm escalation to on-call (SMS + voice)", "SCRIPTED", "Tier-1 notification <= 15 min, after hours", None, None, None, ["CS-EMS-03"], date(2026, 1, 20)),
        ("TC-OQ-EMS-05", "OQ-EMS-01", "Monthly excursion report (exploratory)", "UNSCRIPTED", "Report generated", None, None, None, ["URS-EMS-015"], date(2026, 1, 21)),
        ("TC-OQ-EMS-06", "OQ-EMS-01", "Data retention: supplier assessment", "SUPPLIER_DOC", "Supplier documentation reviewed", None, None, None, ["URS-EMS-016"], date(2026, 1, 21)),
        ("TC-OQ-LIMS-01", "OQ-LIMS-01", "Result entry metadata", "SCRIPTED", "Analyst, timestamp, instrument captured", None, None, None, ["URS-LIMS-001"], date(2026, 2, 9)),
        ("TC-OQ-LIMS-02", "OQ-LIMS-01", "Review and approval workflow", "SCRIPTED", "Approval blocked without review", None, None, None, ["CS-LIMS-02"], date(2026, 2, 9)),
        ("TC-OQ-LIMS-03", "OQ-LIMS-01", "Specification check and OOS flag", "SCRIPTED", "OOS flagged for all release tests", None, None, None, ["CS-LIMS-01"], date(2026, 2, 10)),
        ("TC-OQ-LIMS-04", "OQ-LIMS-01", "VCN calculation (boundary values)", "SCRIPTED", "Matches independent calculation", 0.1, 8.0, "copies/cell", ["FS-LIMS-01", "DS-LIMS-01"], date(2026, 2, 11)),
        ("TC-OQ-LIMS-05", "OQ-LIMS-01", "CoA generation", "SCRIPTED", "Only approved results on CoA", None, None, None, ["URS-LIMS-005"], date(2026, 2, 11)),
        ("TC-OQ-LIMS-06", "OQ-LIMS-01", "Result audit trail", "SCRIPTED", "Changes audited with reason", None, None, None, ["URS-LIMS-006"], date(2026, 2, 12)),
        ("TC-OQ-LIMS-07", "OQ-LIMS-01", "PDF export (exploratory)", "UNSCRIPTED", "Export works", None, None, None, ["URS-LIMS-007"], date(2026, 2, 12)),
        ("TC-OQ-EBR-01", "OQ-EBR-01", "Step sequence enforcement", "SCRIPTED", "Out-of-sequence step blocked", None, None, None, ["CS-EBR-01"], date(2026, 3, 16)),
        ("TC-OQ-EBR-02", "OQ-EBR-01", "Material status and expiry check", "SCRIPTED", "Expired / quarantined lot blocked", None, None, None, ["URS-EBR-002"], date(2026, 3, 16)),
        ("TC-OQ-EBR-03", "OQ-EBR-01", "Equipment status check", "SCRIPTED", "Unqualified equipment blocked", None, None, None, ["URS-EBR-003"], date(2026, 3, 17)),
        ("TC-OQ-EBR-04", "OQ-EBR-01", "Vector volume calculation", "SCRIPTED", "Matches independent calculation", 2.5, 10.0, "TU/cell", ["URS-EBR-007", "CS-EBR-02"], date(2026, 3, 17)),
        ("TC-OQ-EBR-05", "OQ-EBR-01", "Electronic signatures", "SCRIPTED", "Part 11 signature manifestations", None, None, None, ["URS-EBR-008"], date(2026, 3, 18)),
        ("TC-OQ-EBR-06", "OQ-EBR-01", "Incubator ID capture", "SCRIPTED", "Recorded per vessel", None, None, None, ["URS-EBR-010"], date(2026, 3, 18)),
        # AMV (verify method performance characteristics, not URS)
        ("TC-AMV-CAR-01", "AMV-FC-CAR-01", "Accuracy, precision, range", "SCRIPTED", "Per ICH Q2(R2) protocol criteria", 5, 90, "% of CD3+", [], date(2026, 3, 20)),
        ("TC-AMV-VCN-01", "AMV-VCN-01", "Accuracy, precision, range", "SCRIPTED", "Per ICH Q2(R2) protocol criteria", 0.1, 6.0, "copies/cell", [], date(2026, 3, 24)),
        ("TC-AMV-POT-01", "AMV-POT-01", "Accuracy, precision, range", "SCRIPTED", "Per ICH Q2(R2) protocol criteria", 500, 25000, "pg/mL", [], date(2026, 4, 2)),
        ("TC-AMV-VIAB-01", "AMV-VIAB-01", "Accuracy, precision, range", "SCRIPTED", "Per protocol criteria", 20, 100, "%", [], date(2026, 2, 25)),
        ("TC-AMV-CD3-01", "AMV-CD3-01", "Specificity, precision, range", "SCRIPTED", "Per ICH Q2(R2) protocol criteria", 50, 100, "%", [], date(2026, 3, 18)),
    ]
    method_target = {"AMV-FC-CAR-01": "AM-FC-CAR", "AMV-VCN-01": "AM-VCN", "AMV-POT-01": "AM-POT", "AMV-VIAB-01": "AM-VIAB",
                     "AMV-CD3-01": "AM-CD3"}
    execs = []
    ex_n = 0

    def run(tc, target, d, result="PASS", actual="Meets acceptance criteria", by="VAL-03", rev="QA-02"):
        nonlocal ex_n
        ex_n += 1
        eid = f"TX-{ex_n:04d}"
        execs.append(dict(exec_id=eid, tc_id=tc, target_id=target, exec_dt=d, executed_by=by, reviewed_by=rev,
                          result=result, actual_result=actual))
        return eid

    failed_exec = None
    for tc, pid, title, meth, acc, lo, hi, uom, ver, d in TC:
        add("val_test_case", tc_id=tc, protocol_id=pid, title=title, method=meth, acceptance_crit=acc,
            tested_lo=lo, tested_hi=hi, uom=uom)
        for v in ver:
            link("TC", tc, "VERIFIES", "SPEC", v)
        targets = [method_target[pid]] if pid in method_target else units[proto_sys[pid]]
        for i, tgt in enumerate(targets):
            if tc == "TC-OQ-INC-04" and tgt == "INC-03":
                failed_exec = run(tc, tgt, d, "FAIL", "Alarm activated at 142 s")
            else:
                dd = date.fromordinal(d.toordinal() + (i // 2))
                while dd.weekday() >= 5:
                    dd = date.fromordinal(dd.toordinal() + 1)
                run(tc, tgt, dd)
    # Like-for-like compressor replacement on FRZ-80-02: partial requalification
    requal = [run("TC-OQ-ULT-01", "FRZ-80-02", date(2026, 4, 24), actual="24 h pull-down and hold <= -78 C"),
              run("TC-OQ-ULT-02", "FRZ-80-02", date(2026, 4, 24))]
    T["val_test_exec"] = execs

    # ------------------------------------------------------------------
    # PPQ protocol: batches and acceptance criteria (free text attributes)
    # ------------------------------------------------------------------
    ppq_batches = [b["batch_id"] for b in proc["batch_master"] if b["run_type"] == "PPQ"]
    for b in ppq_batches:
        link("PROTOCOL", "PPQ-001", "RELATED", "BATCH", b)
    crit = [
        ("CPP", "MOI (TU/cell)", 4.0, 6.0, "TU/cell"),
        ("CPP", "Seeding density (x10^6 cells/mL)", 0.4, 0.6, "x10^6/mL"),
        ("CPP", "Incubator temperature during expansion", 36.5, 37.5, "C"),
        ("CPP", "Culture duration (days)", 7, 9, "days"),
        ("CPP", "Time from activation to transduction", 20, 30, "h"),
        ("IPC", "Viability at harvest", 80, None, "%"),
        ("PERFORMANCE", "Fold expansion", 8, None, "fold"),
        ("CQA", "CAR expression (% CAR+ of CD3+)", 20, None, "% of CD3+"),
        ("CQA", "Vector copy number (per CAR+ cell)", None, 5.0, "copies/CAR+ cell"),
        ("CQA", "Viability (release)", 70, None, "%"),
        ("CQA", "CD3+ purity", 80, None, "%"),
        ("CQA", "Potency (IFN-g release)", 1000, None, "pg/mL"),
    ]
    for i, (cls, txt, lo, hi, uom) in enumerate(crit, 1):
        add("val_ppq_criterion", protocol_id="PPQ-001", crit_no=i, crit_class=cls, attribute_txt=txt, lo=lo, hi=hi, uom=uom)

    # ------------------------------------------------------------------
    # QMS: deviations, CAPAs, change controls
    # ------------------------------------------------------------------
    eng = sorted(b["batch_id"] for b in proc["batch_master"] if b["run_type"] == "ENG")
    D = [
        dict(dev_no="DEV-26-011", record_type="TEST_INCIDENT", open_dt=date(2026, 2, 10), event_ts=None, dev_class="MINOR",
             title="OQ test incident: INC-03 door-open alarm late",
             description="During execution of TC-OQ-INC-04 on INC-03 the door-open alarm activated at 142 s (criterion <= 60 s). INC-01, INC-02 and INC-04 passed.",
             impact_assessment="Qualification test incident. INC-03 door alarm function not verified.",
             rc_category="EQUIPMENT - COMPONENT", root_cause="Door switch misaligned.", status="CLOSED", closed_dt=date(2026, 2, 24),
             rel=[("EXEC", failed_exec), ("EQUIP", "INC-03"), ("PROTOCOL", "OQ-INC-01"), ("CAPA", "CAPA-26-012")]),
        dict(dev_no="DEV-26-018", record_type="DEVIATION", open_dt=date(2026, 3, 25), event_ts=None, dev_class="MINOR",
             title="Expired CD8 bead lot scanned during dry run",
             description="EBR blocked an expired CD8 bead lot during an operator training dry run. No product involved.",
             impact_assessment="No impact. Control worked as intended.", rc_category="MATERIAL MANAGEMENT",
             root_cause="Expired lot not removed from cold room.", status="CLOSED", closed_dt=date(2026, 4, 1), rel=[]),
        dict(dev_no="DEV-26-021", record_type="DEVIATION", open_dt=date(2026, 4, 20), event_ts=None, dev_class="MAJOR",
             title="FRZ-80-02 high temperature alarm",
             description="FRZ-80-02 high temperature alarm acknowledged by warehouse staff at 14:40. Compressor found not running. Contents (viral vector and cytokine lots) relocated to FRZ-80-01 at 15:30. Maximum recorded chamber temperature before relocation approx. -36 C. FRZ-80-02 then powered down for repair (chamber readings after 15:30 are from the empty unit). Contents returned to FRZ-80-02 on 24-Apr after pull-down re-verification under CC-26-014.",
             impact_assessment="Materials remained frozen. Supplier stability statement supports storage at <= -65 C; short excursion assessed as low risk. No lots placed on hold.",
             rc_category="EQUIPMENT - COMPRESSOR FAILURE", root_cause="Compressor failure (age-related).", status="CLOSED", closed_dt=date(2026, 5, 12),
             rel=[("EQUIP", "FRZ-80-02"), ("CAPA", "CAPA-26-008")]),
        dict(dev_no="DEV-26-027", record_type="ATYPICAL_RESULT", open_dt=date(2026, 5, 21), event_ts=None, dev_class="MINOR",
             title=f"Low %CAR+ in engineering runs {eng[0]} and {eng[1]}",
             description=f"FC-CAR results for {eng[0]} and {eng[1]} below the 20% target. Transduction performed per SOP-MFG-104; MOI 5.0 TU/cell.",
             impact_assessment="Engineering runs, not for clinical use. No impact to released product.",
             rc_category="STARTING MATERIAL - DONOR VARIABILITY", root_cause="Suspected donor-related variability (low CD3% at apheresis).",
             status="OPEN", closed_dt=None,
             rel=[("BATCH", eng[0]), ("BATCH", eng[1]), ("CAPA", "CAPA-26-016")]),
        dict(dev_no="DEV-26-033", record_type="PROTOCOL_DEVIATION", open_dt=date(2026, 6, 12), event_ts=None, dev_class="MAJOR",
             title="PPQ26-02 harvest viability below PPQ acceptance criterion",
             description="Harvest viability for PPQ26-02 below the PPQ-001 acceptance criterion of 80%. INC-03 door found not fully latched on the morning of 11-Jun; door alarm acknowledged 07:50.",
             impact_assessment="PPQ26-02 does not meet PPQ-001 criterion 6. Release testing within specification.",
             rc_category="HUMAN ERROR - PROCEDURE NOT FOLLOWED", root_cause="Operator did not confirm door latch per SOP-MFG-105.",
             status="CLOSED", closed_dt=date(2026, 7, 3),
             rel=[("BATCH", "PPQ26-02"), ("PROTOCOL", "PPQ-001"), ("EQUIP", "INC-03"), ("CAPA", "CAPA-26-015")]),
        dict(dev_no="DEV-26-038", record_type="DEVIATION", open_dt=date(2026, 7, 14), event_ts=None, dev_class="MINOR",
             title="PPQ26-04 label printer error",
             description="Bag labels misprinted (truncated text). Labels reprinted and reconciled.",
             impact_assessment="No product impact.", rc_category="EQUIPMENT - PRINTER", root_cause="Printer ribbon misfeed.",
             status="CLOSED", closed_dt=date(2026, 7, 21), rel=[("BATCH", "PPQ26-04")]),
        dict(dev_no="DEV-26-041", record_type="DEVIATION", open_dt=date(2026, 8, 3), event_ts=None, dev_class="MINOR",
             title="PPQ26-05 Prodigy tubing set leak at sampling port",
             description="Small leak at sampling port observed during priming, before product contact. Tubing set replaced.",
             impact_assessment="No product contact. Sterility results pending at time of assessment.",
             rc_category="SUPPLIER - MATERIAL DEFECT", root_cause="Sampling port weld defect (supplier).", status="OPEN", closed_dt=None,
             rel=[("BATCH", "PPQ26-05"), ("EQUIP", "PRDG-01"), ("CAPA", "CAPA-26-019")]),
    ]
    for dv in D:
        rel = dv.pop("rel")
        add("qms_deviation", **dv)
        for tt, tid in rel:
            if tt == "EXEC":
                link("EXEC", tid, "RELATED", "DEV", dv["dev_no"])
            else:
                link("DEV", dv["dev_no"], "RELATED", tt, tid)

    capas = [
        ("CAPA-26-008", date(2026, 4, 21), "CORRECTIVE", "Replace FRZ-80-02 compressor and verify pull-down.", "Facilities",
         date(2026, 5, 29), "CLOSED", date(2026, 5, 27), "EFFECTIVE - no recurrence 24-Apr to 26-May", ["CC-26-014"]),
        ("CAPA-26-012", date(2026, 2, 24), "CORRECTIVE", "Replace INC-03 door switch and re-execute TC-OQ-INC-04.", "Engineering",
         date(2026, 3, 31), "OPEN", None, None, ["CC-26-019"]),
        ("CAPA-26-015", date(2026, 6, 15), "CORRECTIVE", "Retrain Suite 2 operators on incubator door latch check (SOP-MFG-105).", "Manufacturing",
         date(2026, 7, 1), "CLOSED", date(2026, 7, 3), "PENDING", []),
        ("CAPA-26-016", date(2026, 5, 28), "PREVENTIVE", "Evaluate minimum CD3% acceptance criterion at apheresis receipt.", "PD",
         date(2026, 9, 30), "OPEN", None, None, []),
        ("CAPA-26-019", date(2026, 8, 5), "CORRECTIVE", "Supplier corrective action request for tubing set sampling port.", "Supply Quality",
         date(2026, 10, 30), "OPEN", None, None, []),
    ]
    for no, od, ct, act, own, due, st, cd, eff, ccs in capas:
        add("qms_capa", capa_no=no, open_dt=od, capa_type=ct, action_desc=act, owner=own, due_dt=due, status=st,
            closed_dt=cd, eff_check=eff)
        for c in ccs:
            link("CAPA", no, "RELATED", "CC", c)

    ccs = [
        ("CC-26-004", date(2026, 2, 20), "Process version PV2.0", "IL-7/IL-15 replace IL-2; seeding density 0.5 x10^6/mL; harvest day 8.",
         "MAJOR", "SOPs 103/105/106 revised; pFMEA updated.", "CLOSED", date(2026, 5, 1),
         [("SOP", "SOP-MFG-103"), ("SOP", "SOP-MFG-105"), ("SOP", "SOP-MFG-106"), ("RA", "RA-PFMEA-001")], []),
        ("CC-26-011", date(2026, 3, 12), "EMS notification group restructure (paging provider change)",
         "On-call rota moved to a new paging provider; notification groups and escalation recipients rebuilt in the EMS configuration (CS-EMS-03). No software change.",
         "MINOR", "Configuration change to notification groups only. No change to validated alarm logic. No re-testing required.",
         "CLOSED", date(2026, 3, 16), [("SPEC", "CS-EMS-03")], []),
        ("CC-26-014", date(2026, 4, 21), "FRZ-80-02 compressor replacement", "Like-for-like compressor replacement.",
         "MINOR", "Partial OQ re-execution (pull-down, alarm).", "CLOSED", date(2026, 4, 23),
         [("EQUIP", "FRZ-80-02")], requal),
        ("CC-26-019", date(2026, 2, 24), "INC-03 door switch replacement", "Replace and realign door switch; re-execute TC-OQ-INC-04.",
         "MINOR", "Re-execution of TC-OQ-INC-04 on INC-03 required.", "APPROVED - NOT IMPLEMENTED", None,
         [("EQUIP", "INC-03")], []),
        ("CC-26-022", date(2026, 8, 20), "Increase transduction target MOI to 8.0 TU/cell",
         "Raise target MOI from 5.0 to 8.0 TU/cell to improve %CAR+ (DoE-MOI-02/03).", "MAJOR",
         "SOP-MFG-104 to be revised.", "IMPACT ASSESSMENT", None, [("SOP", "SOP-MFG-104")], []),
    ]
    for no, od, title, desc, cls, ia, st, impl, impacts, verifs in ccs:
        add("qms_change_control", cc_no=no, open_dt=od, title=title, description=desc, change_class=cls,
            impact_assessment=ia, status=st, impl_dt=impl)
        for tt, tid in impacts:
            link("CC", no, "IMPACTS", tt, tid)
        for ex in verifs:
            link("CC", no, "RELATED", "EXEC", ex)

    T["trace_link"] = links
    return T
