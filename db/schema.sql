-- =====================================================================
-- CAR-T process development + validation database (synthetic)
--
-- Modeled on how real PD, LIMS, QMS and validation-tool exports tend to
-- look, on purpose:
--   * one master table per entity, one fact table per unit operation
--   * terse, inconsistent column names (via_pct appears in many tables
--     with different meanings; tvc_e6 vs tvc_e9; tnc vs tvc)
--   * vendor CoA and QC results stored key-value (LIMS-style)
--   * historian tags whose names do not match equipment IDs exactly
--   * validation and QMS relationships stored in one generic link table,
--     the way ALM / QMS tools export "related records"
--   * FMEA rows with free-text step / parameter / CQA columns, as in the
--     spreadsheets most risk assessments actually live in
--
-- No COMMENT ON statements on purpose: the "without semantic layer" agent
-- should see only what a raw catalog would show it.
--
-- Everything here is CONTENT. The AGE graph (built later from these
-- tables + the YAML semantic layer) holds identities and relationships.
-- =====================================================================

DROP SCHEMA IF EXISTS pd CASCADE;
CREATE SCHEMA pd;
SET search_path = pd, public;

-- =====================================================================
-- 1. Master data
-- =====================================================================
CREATE TABLE donor (
    donor_id        TEXT PRIMARY KEY,
    age_yrs         INT,
    sex             CHAR(1),
    cmv_serostatus  TEXT,
    source_vendor   TEXT
);

CREATE TABLE leukopak (
    lp_id           TEXT PRIMARY KEY,
    donor_id        TEXT NOT NULL REFERENCES donor(donor_id),
    collection_dt   DATE,
    vendor          TEXT,
    ship_cond       TEXT,
    lp_vol_ml       NUMERIC(6,1)
);

-- Validated systems: equipment families, computerized systems.
-- (The "system" boundary that requirements, risk assessments and
-- protocols are written against.)
CREATE TABLE val_system (
    sys_id          TEXT PRIMARY KEY,
    sys_name        TEXT,
    sys_class       TEXT,          -- EQUIPMENT | COMPUTERIZED
    gamp_cat        TEXT,          -- 1 / 3 / 4 / 5, or 4+5 for configured + custom
    gxp_area        TEXT,
    owner_dept      TEXT,
    val_status      TEXT
);

CREATE TABLE equipment (
    equip_id        TEXT PRIMARY KEY,
    equip_type      TEXT,
    model           TEXT,
    room            TEXT,
    sys_id          TEXT REFERENCES val_system(sys_id),   -- NULL = not qualified (PD lab)
    cal_due_dt      DATE
);

CREATE TABLE material_lot (
    lot_no          TEXT PRIMARY KEY,
    matl_code       TEXT,
    matl_desc       TEXT,
    vendor          TEXT,
    mfg_dt          DATE,
    exp_dt          DATE,
    recv_dt         DATE,
    storage_loc     TEXT,
    lot_status      TEXT
);

CREATE TABLE material_coa (
    lot_no          TEXT NOT NULL REFERENCES material_lot(lot_no),
    test_code       TEXT NOT NULL,
    result_val      NUMERIC,
    result_txt      TEXT,
    uom             TEXT,
    PRIMARY KEY (lot_no, test_code)
);

CREATE TABLE batch_master (
    batch_id        TEXT PRIMARY KEY,
    lp_id           TEXT NOT NULL REFERENCES leukopak(lp_id),
    run_type        TEXT,          -- PD | ENG | PPQ
    proc_ver        TEXT,
    run_purpose     TEXT,
    doe_id          TEXT,
    start_dt        DATE,
    suite           TEXT,
    operator        TEXT,
    batch_status    TEXT,
    comments        TEXT
);

-- =====================================================================
-- 2. Unit operation fact tables
-- =====================================================================
CREATE TABLE uo01_aph_receipt (
    batch_id        TEXT PRIMARY KEY REFERENCES batch_master(batch_id),
    lp_id           TEXT REFERENCES leukopak(lp_id),
    rcpt_ts         TIMESTAMP,
    alloc_vol_ml    NUMERIC(6,1),
    tnc_e9          NUMERIC(8,3),
    via_pct         NUMERIC(5,1),
    cd3_pct         NUMERIC(5,1),
    cd4_pct         NUMERIC(5,1),
    cd8_pct         NUMERIC(5,1),
    cd19_pct        NUMERIC(5,1),
    mono_pct        NUMERIC(5,1),
    hold_hrs        NUMERIC(5,1),
    temp_c          NUMERIC(4,1)
);

CREATE TABLE uo02_tcell_sel (
    batch_id        TEXT PRIMARY KEY REFERENCES batch_master(batch_id),
    sel_ts          TIMESTAMP,
    equip_id        TEXT REFERENCES equipment(equip_id),
    bead_lot_cd4    TEXT REFERENCES material_lot(lot_no),
    bead_lot_cd8    TEXT REFERENCES material_lot(lot_no),
    tnc_pre_e9      NUMERIC(8,3),
    tnc_post_e9     NUMERIC(8,3),
    via_pct         NUMERIC(5,1),
    cd3_pct         NUMERIC(5,1),
    cd4_cd8_ratio   NUMERIC(5,2),
    recov_pct       NUMERIC(5,1)
);

CREATE TABLE uo03_activation (
    batch_id        TEXT PRIMARY KEY REFERENCES batch_master(batch_id),
    act_ts          TIMESTAMP,
    act_lot         TEXT REFERENCES material_lot(lot_no),
    media_lot       TEXT REFERENCES material_lot(lot_no),
    cyto_lot_1      TEXT REFERENCES material_lot(lot_no),
    cyto_lot_2      TEXT REFERENCES material_lot(lot_no),
    vessel          TEXT,
    seed_dens_e6_ml NUMERIC(5,2),
    seed_cells_e6   NUMERIC(8,1),
    act_vol_ml      NUMERIC(7,1)
);

CREATE TABLE uo04_transduction (
    batch_id        TEXT PRIMARY KEY REFERENCES batch_master(batch_id),
    td_ts           TIMESTAMP,
    hrs_post_act    NUMERIC(5,1),
    vec_lot         TEXT REFERENCES material_lot(lot_no),
    moi_tgt         NUMERIC(5,1),
    cells_at_td_e6  NUMERIC(8,1),
    vec_vol_ul      NUMERIC(8,1),
    enh_lot         TEXT REFERENCES material_lot(lot_no)
);

CREATE TABLE uo05_expansion (
    batch_id        TEXT NOT NULL REFERENCES batch_master(batch_id),
    day_no          INT NOT NULL,
    sample_ts       TIMESTAMP,
    equip_id        TEXT REFERENCES equipment(equip_id),
    cult_vol_ml     NUMERIC(7,1),
    vcd_e6_ml       NUMERIC(7,3),
    via_pct         NUMERIC(5,1),
    tvc_e6          NUMERIC(9,1),
    gluc_g_l        NUMERIC(5,2),
    lac_g_l         NUMERIC(5,2),
    feed_vol_ml     NUMERIC(7,1),
    car_pos_pct     NUMERIC(5,1),
    PRIMARY KEY (batch_id, day_no)
);

CREATE TABLE uo06_harvest (
    batch_id        TEXT PRIMARY KEY REFERENCES batch_master(batch_id),
    hvst_ts         TIMESTAMP,
    hvst_day        INT,
    tvc_e9          NUMERIC(8,3),
    via_pct         NUMERIC(5,1),
    equip_id        TEXT REFERENCES equipment(equip_id),
    post_wash_tvc_e9 NUMERIC(8,3),
    wash_recov_pct  NUMERIC(5,1)
);

CREATE TABLE uo07_form_fill (
    batch_id        TEXT PRIMARY KEY REFERENCES batch_master(batch_id),
    ff_ts           TIMESTAMP,
    cryo_lot        TEXT REFERENCES material_lot(lot_no),
    tgt_conc_e6_ml  NUMERIC(6,1),
    fill_vol_ml     NUMERIC(6,1),
    n_bags          INT,
    equip_id        TEXT REFERENCES equipment(equip_id),
    crf_profile     TEXT,
    post_thaw_via_pct NUMERIC(5,1)
);

-- LIMS export: one row per batch per test
CREATE TABLE qc_rel_results (
    batch_id        TEXT NOT NULL REFERENCES batch_master(batch_id),
    test_code       TEXT NOT NULL,
    test_purpose    TEXT,          -- RELEASE (GMP runs) | CHAR (PD runs)
    test_dt         DATE,
    result_val      NUMERIC,
    result_txt      TEXT,
    uom             TEXT,
    spec_lo         NUMERIC,
    spec_hi         NUMERIC,
    spec_txt        TEXT,
    pass_fail       TEXT,
    PRIMARY KEY (batch_id, test_code)
);

-- =====================================================================
-- 3. Equipment monitoring (EMS) and historian
-- =====================================================================
CREATE TABLE equipment_event (
    event_id        TEXT PRIMARY KEY,
    equip_id        TEXT REFERENCES equipment(equip_id),
    event_type      TEXT,
    alarm_code      TEXT,
    start_ts        TIMESTAMP,
    ack_ts          TIMESTAMP,
    ack_by          TEXT,
    end_ts          TIMESTAMP,
    event_desc      TEXT
);

CREATE TABLE hist_tag_data (
    tag             TEXT NOT NULL,
    ts              TIMESTAMP NOT NULL,
    val             NUMERIC(7,2),
    qual            TEXT,
    PRIMARY KEY (tag, ts)
);

-- =====================================================================
-- 4. Validation records (content)
-- =====================================================================
-- URS / FS / CS / DS line items (one row per requirement or spec item)
CREATE TABLE val_spec_item (
    item_id         TEXT PRIMARY KEY,
    spec_level      TEXT,          -- URS | FS | CS | DS
    doc_no          TEXT,
    doc_ver         TEXT,
    sys_id          TEXT REFERENCES val_system(sys_id),
    req_category    TEXT,          -- PERFORMANCE | ALARM | CONTROL | DATA | SECURITY | PHYSICAL | INTERFACE
    item_text       TEXT,
    source          TEXT,          -- SITE | SUPPLIER
    approved_dt     DATE
);

CREATE TABLE val_risk_assessment (
    ra_id           TEXT PRIMARY KEY,
    ra_type         TEXT,          -- pFMEA | FRA
    title           TEXT,
    sys_id          TEXT REFERENCES val_system(sys_id),
    doc_ver         TEXT,
    approved_dt     DATE
);

-- One row per failure mode / function. Free-text columns are copied from
-- the spreadsheet the assessment was performed in.
CREATE TABLE val_risk_item (
    ri_id           TEXT PRIMARY KEY,
    ra_id           TEXT NOT NULL REFERENCES val_risk_assessment(ra_id),
    process_step    TEXT,
    parameter_txt   TEXT,
    failure_mode    TEXT,
    effect          TEXT,
    cqa_impacted    TEXT,
    cause           TEXT,
    sev             INT,
    occ             INT,
    det             INT,
    rpn             INT,
    risk_class      TEXT,          -- HIGH | MEDIUM | LOW (team-assigned)
    current_controls TEXT,
    assurance_approach TEXT
);

CREATE TABLE val_protocol (
    protocol_id     TEXT PRIMARY KEY,
    ptype           TEXT,          -- IQ | OQ | PQ | PPQ | AMV
    title           TEXT,
    sys_id          TEXT REFERENCES val_system(sys_id),
    method_id       TEXT,
    doc_ver         TEXT,
    approved_dt     DATE,
    status          TEXT
);

CREATE TABLE val_test_case (
    tc_id           TEXT PRIMARY KEY,
    protocol_id     TEXT REFERENCES val_protocol(protocol_id),
    title           TEXT,
    method          TEXT,          -- SCRIPTED | UNSCRIPTED | SUPPLIER_DOC | INSPECTION
    acceptance_crit TEXT,
    tested_lo       NUMERIC,
    tested_hi       NUMERIC,
    uom             TEXT
);

CREATE TABLE val_test_exec (
    exec_id         TEXT PRIMARY KEY,
    tc_id           TEXT NOT NULL REFERENCES val_test_case(tc_id),
    target_id       TEXT,          -- equipment unit or system executed against
    exec_dt         DATE,
    executed_by     TEXT,
    reviewed_by     TEXT,
    result          TEXT,          -- PASS | FAIL
    actual_result   TEXT
);

-- PPQ acceptance criteria (content of the PPQ protocol)
CREATE TABLE val_ppq_criterion (
    protocol_id     TEXT NOT NULL REFERENCES val_protocol(protocol_id),
    crit_no         INT NOT NULL,
    crit_class      TEXT,          -- CPP | CQA | IPC | PERFORMANCE
    attribute_txt   TEXT,
    lo              NUMERIC,
    hi              NUMERIC,
    uom             TEXT,
    PRIMARY KEY (protocol_id, crit_no)
);

CREATE TABLE analytical_method (
    method_id       TEXT PRIMARY KEY,
    method_name     TEXT,
    technique       TEXT,
    qc_test_code    TEXT,
    val_range_lo    NUMERIC,
    val_range_hi    NUMERIC,
    uom             TEXT,
    status          TEXT
);

CREATE TABLE sop (
    sop_id          TEXT PRIMARY KEY,
    title           TEXT,
    doc_ver         TEXT,
    effective_dt    DATE,
    owner_dept      TEXT,
    process_step    TEXT,
    sys_id          TEXT REFERENCES val_system(sys_id)
);

-- =====================================================================
-- 5. QMS records (content)
-- =====================================================================
CREATE TABLE qms_deviation (
    dev_no          TEXT PRIMARY KEY,
    record_type     TEXT,          -- DEVIATION | PROTOCOL_DEVIATION | TEST_INCIDENT | ATYPICAL_RESULT
    open_dt         DATE,
    event_ts        TIMESTAMP,
    dev_class       TEXT,          -- MINOR | MAJOR | CRITICAL
    title           TEXT,
    description     TEXT,
    impact_assessment TEXT,
    rc_category     TEXT,
    root_cause      TEXT,
    status          TEXT,
    closed_dt       DATE
);

CREATE TABLE qms_capa (
    capa_no         TEXT PRIMARY KEY,
    open_dt         DATE,
    capa_type       TEXT,          -- CORRECTIVE | PREVENTIVE
    action_desc     TEXT,
    owner           TEXT,
    due_dt          DATE,
    status          TEXT,
    closed_dt       DATE,
    eff_check       TEXT
);

CREATE TABLE qms_change_control (
    cc_no           TEXT PRIMARY KEY,
    open_dt         DATE,
    title           TEXT,
    description     TEXT,
    change_class    TEXT,          -- MINOR | MAJOR
    impact_assessment TEXT,
    status          TEXT,
    impl_dt         DATE
);

-- Generic "related records" export from the validation / QMS tools.
-- One row per link; link_type is coarse, the way those tools export it.
CREATE TABLE trace_link (
    link_id         BIGSERIAL PRIMARY KEY,
    src_type        TEXT NOT NULL,
    src_id          TEXT NOT NULL,
    link_type       TEXT NOT NULL,
    tgt_type        TEXT NOT NULL,
    tgt_id          TEXT NOT NULL
);

CREATE INDEX ix_lp_donor        ON leukopak(donor_id);
CREATE INDEX ix_batch_lp        ON batch_master(lp_id);
CREATE INDEX ix_td_vec          ON uo04_transduction(vec_lot);
CREATE INDEX ix_exp_equip       ON uo05_expansion(equip_id, sample_ts);
CREATE INDEX ix_hist_ts         ON hist_tag_data(ts);
CREATE INDEX ix_evt_equip       ON equipment_event(equip_id, start_ts);
CREATE INDEX ix_tl_src          ON trace_link(src_type, src_id);
CREATE INDEX ix_tl_tgt          ON trace_link(tgt_type, tgt_id);
CREATE INDEX ix_tx_tc           ON val_test_exec(tc_id);
