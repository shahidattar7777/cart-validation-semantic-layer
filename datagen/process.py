"""Synthetic CAR-T process data: donors, leukopaks, batches, unit operation
fact tables, QC results, EMS alarms and historian data.

Planted signals (see docs/data_stories.md for the full list):
  S1  Vector lot LV25-118 sat in FRZ-80-02 during a compressor failure on
      2026-04-20. Batches transduced with it AFTER that date lose potency
      (low %CAR+, low VCN). Batches transduced before are normal.
  S2  INC-03 door left unlatched overnight 2026-06-10/11 -> temperature and
      CO2 drop. PPQ26-02 and PPQ26-03 were expanding in INC-03 at the time.
  S3  Two donors (HD-0107, HD-0113) expand poorly regardless of process.
  S4  PV1.0 -> PV2.0 on 2026-05-01 (IL-7/IL-15, lower seeding density,
      day-8 harvest): lower fold expansion, higher Tscm.
  S5  MOI DoE groups: VCN rises with MOI, %CAR+ saturates.
  S6  After EMS change CC-26-011 (2026-03-16) after-hours alarms are no
      longer escalated: acknowledgement times jump from minutes to hours.
"""
from __future__ import annotations

import math
from datetime import date, datetime, timedelta

import numpy as np

# --------------------------------------------------------------------------
# Fixed story anchors
# --------------------------------------------------------------------------
PV2_START = date(2026, 5, 1)
CC_EMS_IMPL = datetime(2026, 3, 16, 9, 0)

FRZ_FAIL_START = datetime(2026, 4, 20, 1, 10)
FRZ_ALARM = datetime(2026, 4, 20, 3, 20)
FRZ_FAIL_ACK = datetime(2026, 4, 20, 14, 40)
FRZ_CONTENTS_MOVED = datetime(2026, 4, 20, 15, 30)
FRZ_REPAIRED = datetime(2026, 4, 23, 10, 0)

INC3_DOOR_OPEN = datetime(2026, 6, 10, 21, 40)
INC3_DOOR_CLOSED = datetime(2026, 6, 11, 7, 50)
INC3_RECOVERED = datetime(2026, 6, 11, 9, 20)

HIST_START = datetime(2026, 1, 5, 0, 0)
HIST_END = datetime(2026, 9, 4, 23, 0)

BAD_VECTOR_LOT = "LV25-118"
LOW_DONORS = {"HD-0107", "HD-0113"}

# Vector lots: (lot, first use, last use, storage, CoA functional titer TU/mL)
VECTOR_LOTS = [
    ("LV25-104", date(2026, 1, 1), date(2026, 3, 1), "FRZ-80-01", 1.21e8),
    ("LV25-118", date(2026, 3, 2), date(2026, 5, 20), "FRZ-80-02", 1.04e8),
    ("LV26-007", date(2026, 5, 21), date(2026, 7, 10), "FRZ-80-01", 1.36e8),
    ("LV26-021", date(2026, 7, 11), date(2026, 12, 31), "FRZ-80-01", 1.12e8),
]


def _lot_for(windows, d):
    for lot, lo, hi in windows:
        if lo <= d <= hi:
            return lot
    return windows[-1][0]


def _weekday(d: date) -> date:
    """Next Tuesday-Friday, so collection (start - 1 day) is Monday-Thursday."""
    while d.weekday() not in (1, 2, 3, 4):
        d += timedelta(days=1)
    return d


def build(rng: np.random.Generator) -> dict[str, list[dict]]:
    T: dict[str, list[dict]] = {}

    def add(table, **row):
        T.setdefault(table, []).append(row)

    # ------------------------------------------------------------------
    # Equipment (val_system rows come from validation.py; ids must match)
    # ------------------------------------------------------------------
    equip = [
        # equip_id, type, model, room, sys_id
        ("INC-PD-01", "CO2 incubator", "Heracell Vios 160i", "B210", None),
        ("INC-PD-02", "CO2 incubator", "Heracell Vios 160i", "B210", None),
        ("PRDG-PD-01", "Cell processing system", "CliniMACS Prodigy", "B212", None),
        ("LOVO-PD-01", "Cell processing system", "LOVO", "B212", None),
        ("CRF-PD-01", "Controlled-rate freezer", "CryoMed 7454", "B214", None),
        ("INC-01", "CO2 incubator", "Heracell Vios 250i", "G2-104", "SYS-INC"),
        ("INC-02", "CO2 incubator", "Heracell Vios 250i", "G2-104", "SYS-INC"),
        ("INC-03", "CO2 incubator", "Heracell Vios 250i", "G2-105", "SYS-INC"),
        ("INC-04", "CO2 incubator", "Heracell Vios 250i", "G2-105", "SYS-INC"),
        ("PRDG-01", "Cell processing system", "CliniMACS Prodigy", "G2-102", "SYS-PRDG"),
        ("PRDG-02", "Cell processing system", "CliniMACS Prodigy", "G2-102", "SYS-PRDG"),
        ("LOVO-01", "Cell processing system", "LOVO", "G2-106", "SYS-LOVO"),
        ("CRF-01", "Controlled-rate freezer", "CryoMed 7456", "G2-108", "SYS-CRF"),
        ("FRZ-80-01", "ULT freezer -80C", "TSX60086", "W105", "SYS-ULT"),
        ("FRZ-80-02", "ULT freezer -80C", "TSX60086", "W105", "SYS-ULT"),
    ]
    for eid, et, model, room, sys_id in equip:
        add("equipment", equip_id=eid, equip_type=et, model=model, room=room,
            sys_id=sys_id, cal_due_dt=date(2026, 12, 15) if sys_id else date(2026, 11, 30))

    # ------------------------------------------------------------------
    # Material lots + CoA
    # ------------------------------------------------------------------
    vec_potency = {}
    for lot, lo, hi, loc, ft in VECTOR_LOTS:
        add("material_lot", lot_no=lot, matl_code="LVV-CD19-BBZ",
            matl_desc="Lentiviral vector, anti-CD19 CAR (4-1BB/CD3z)",
            vendor="VectorWorks Bio", mfg_dt=lo - timedelta(days=75),
            exp_dt=lo + timedelta(days=640), recv_dt=lo - timedelta(days=20),
            storage_loc=loc, lot_status="RELEASED")
        add("material_coa", lot_no=lot, test_code="FT_TU_ML", result_val=ft, result_txt=None, uom="TU/mL")
        add("material_coa", lot_no=lot, test_code="P24_NG_ML", result_val=round(float(rng.normal(1450, 120)), 0),
            result_txt=None, uom="ng/mL")
        add("material_coa", lot_no=lot, test_code="RCL", result_val=None, result_txt="NOT DETECTED", uom=None)
        add("material_coa", lot_no=lot, test_code="STER", result_val=None, result_txt="NO GROWTH", uom=None)
        add("material_coa", lot_no=lot, test_code="ENDO", result_val=round(float(rng.uniform(0.2, 1.1)), 2),
            result_txt=None, uom="EU/mL")
        vec_potency[lot] = float(rng.normal(1.0, 0.04))

    simple_lots = {
        # matl_code: (desc, vendor, storage, [(lot, first, last)])
        "MED-TEXMACS": ("TexMACS GMP medium", "Miltenyi", "CR-01", [
            ("TM2601", date(2026, 1, 1), date(2026, 3, 15)),
            ("TM2603", date(2026, 3, 16), date(2026, 6, 15)),
            ("TM2606", date(2026, 6, 16), date(2026, 12, 31))]),
        "CYT-IL2": ("IL-2, GMP grade", "Miltenyi", "FRZ-80-02", [
            ("IL2-25K11", date(2026, 1, 1), date(2026, 3, 10)),
            ("IL2-26A03", date(2026, 3, 11), date(2026, 12, 31))]),
        "CYT-IL7": ("IL-7, GMP grade", "Miltenyi", "FRZ-80-01", [
            ("IL7-26B02", date(2026, 1, 1), date(2026, 6, 30)),
            ("IL7-26F11", date(2026, 7, 1), date(2026, 12, 31))]),
        "CYT-IL15": ("IL-15, GMP grade", "Miltenyi", "FRZ-80-01", [
            ("IL15-26B05", date(2026, 1, 1), date(2026, 6, 30)),
            ("IL15-26F14", date(2026, 7, 1), date(2026, 12, 31))]),
        "ACT-TRANSACT": ("T cell activation reagent (CD3/CD28 nanomatrix)", "Miltenyi", "CR-01", [
            ("TA-2601", date(2026, 1, 1), date(2026, 3, 31)),
            ("TA-2604", date(2026, 4, 1), date(2026, 12, 31))]),
        "BEAD-CD4": ("CD4 MicroBeads, GMP", "Miltenyi", "CR-01", [
            ("CD4-2601", date(2026, 1, 1), date(2026, 4, 30)),
            ("CD4-2605", date(2026, 5, 1), date(2026, 12, 31))]),
        "BEAD-CD8": ("CD8 MicroBeads, GMP", "Miltenyi", "CR-01", [
            ("CD8-2601", date(2026, 1, 1), date(2026, 4, 30)),
            ("CD8-2605", date(2026, 5, 1), date(2026, 12, 31))]),
        "ENH-VF1": ("Transduction enhancer", "Miltenyi", "CR-01", [
            ("VF-2602", date(2026, 1, 1), date(2026, 12, 31))]),
        "CRYO-CS10": ("Cryopreservation medium, 10% DMSO", "BioLife", "RT-02", [
            ("CS10-2601", date(2026, 1, 1), date(2026, 5, 31)),
            ("CS10-2606", date(2026, 6, 1), date(2026, 12, 31))]),
    }
    lot_windows = {}
    for code, (desc, vendor, loc, lots) in simple_lots.items():
        lot_windows[code] = lots
        for lot, lo, hi in lots:
            add("material_lot", lot_no=lot, matl_code=code, matl_desc=desc, vendor=vendor,
                mfg_dt=lo - timedelta(days=60), exp_dt=lo + timedelta(days=540),
                recv_dt=lo - timedelta(days=14), storage_loc=loc, lot_status="RELEASED")
            add("material_coa", lot_no=lot, test_code="STER", result_val=None, result_txt="PASS", uom=None)
            add("material_coa", lot_no=lot, test_code="ENDO", result_val=round(float(rng.uniform(0.05, 0.5)), 2),
                result_txt=None, uom="EU/mL")
    vec_windows = [(l, lo, hi) for l, lo, hi, _, _ in VECTOR_LOTS]
    vec_ft = {l: ft for l, _, _, _, ft in VECTOR_LOTS}

    # ------------------------------------------------------------------
    # Donors
    # ------------------------------------------------------------------
    donors = {}
    for i in range(1, 19):
        did = f"HD-{100 + i:04d}"
        low = did in LOW_DONORS
        age = int(rng.integers(61, 66)) if low else int(rng.integers(22, 55))
        vendor = str(rng.choice(["HemaCare", "StemExpress"]))
        donors[did] = dict(
            vendor=vendor,
            low=low,
            cd3=float(rng.uniform(29, 35)) if low else float(rng.uniform(48, 72)),
            growth=0.80 if low else float(rng.normal(1.0, 0.05)),
            te=float(rng.normal(0.97, 0.05)) if low else float(rng.normal(1.0, 0.06)),
        )
        add("donor", donor_id=did, age_yrs=age, sex=str(rng.choice(["M", "F"])),
            cmv_serostatus=str(rng.choice(["POS", "NEG"], p=[0.4, 0.6])),
            source_vendor=vendor)
    normal_donors = [d for d in donors if d not in LOW_DONORS]

    # ------------------------------------------------------------------
    # Run plan
    # ------------------------------------------------------------------
    groups = []  # dicts: start, run_type, purpose, n, doe, mois, donor, suite, incs
    d = date(2026, 1, 12)
    while d <= date(2026, 8, 24):
        groups.append(dict(start=_weekday(d), run_type="PD"))
        d += timedelta(days=int(rng.integers(6, 10)))
    # DoE groups (replace nearest PD group date)
    doe_dates = {date(2026, 2, 17): "DOE-MOI-01", date(2026, 7, 7): "DOE-MOI-02", date(2026, 7, 28): "DOE-MOI-03"}
    for dd, doe in doe_dates.items():
        groups.append(dict(start=dd, run_type="PD", doe=doe))
    for i, dd in enumerate([date(2026, 5, 5), date(2026, 5, 12), date(2026, 5, 19)]):
        groups.append(dict(start=dd, run_type="ENG", inc=["INC-02", "INC-03", "INC-04"][i],
                           prdg=["PRDG-01", "PRDG-02", "PRDG-01"][i]))
    ppq_plan = [(date(2026, 6, 2), "INC-01", "PRDG-01"), (date(2026, 6, 4), "INC-03", "PRDG-02"),
                (date(2026, 6, 9), "INC-03", "PRDG-01"), (date(2026, 7, 14), "INC-02", "PRDG-02"),
                (date(2026, 8, 4), "INC-04", "PRDG-01")]
    for dd, inc, prdg in ppq_plan:
        groups.append(dict(start=dd, run_type="PPQ", inc=inc, prdg=prdg))
    groups.sort(key=lambda g: (g["start"], g["run_type"]))

    # drop PD groups that collide with DoE/ENG/PPQ dates
    fixed = {g["start"] for g in groups if g.get("doe") or g["run_type"] != "PD"}
    groups = [g for g in groups if g.get("doe") or g["run_type"] != "PD" or g["start"] not in fixed]

    # donors: low performers placed in two PD groups each (one PV1, one PV2)
    pd_plain = [g for g in groups if g["run_type"] == "PD" and not g.get("doe")]
    low_slots = {0: "HD-0107", 6: "HD-0113", len(pd_plain) - 9: "HD-0107", len(pd_plain) - 3: "HD-0113"}
    for idx, g in enumerate(pd_plain):
        g["donor"] = low_slots.get(idx)
    for g in groups:
        if not g.get("donor"):
            g["donor"] = str(rng.choice(normal_donors))
        if g["run_type"] == "PD":
            if g.get("doe"):
                g["n"], g["purpose"], g["mois"] = 4, "DoE-MOI", [2.5, 5.0, 10.0, 15.0]
            else:
                g["n"] = int(rng.choice([1, 2], p=[0.55, 0.45]))
                g["purpose"] = str(rng.choice(["Platform", "Platform", "Robustness"]))
        else:
            g["n"], g["purpose"] = 1, ("Engineering run" if g["run_type"] == "ENG" else "Process performance qualification")

    # ------------------------------------------------------------------
    # Simulate each batch
    # ------------------------------------------------------------------
    counters = {"PD": 0, "ENG": 0, "PPQ": 0}
    lp_counter = 0
    pd_inc_cycle = ["INC-PD-01", "INC-PD-02"]
    qc_rows = []
    for g in groups:
        lp_counter += 1
        lp_id = f"LP-26-{lp_counter:03d}"
        dnr = donors[g["donor"]]
        lp_vol = float(rng.uniform(220, 300))
        lp_tnc = float(rng.uniform(9, 18))  # x10^9
        lp_via = float(rng.uniform(95, 99))
        cd4_frac = float(rng.uniform(0.55, 0.70))
        coll = g["start"] - timedelta(days=1)
        add("leukopak", lp_id=lp_id, donor_id=g["donor"], collection_dt=coll,
            vendor=dnr["vendor"], ship_cond="2-8C", lp_vol_ml=round(lp_vol, 1))

        for k in range(g["n"]):
            rt = g["run_type"]
            counters[rt] += 1
            bid = (f"PD26-{counters['PD']:03d}" if rt == "PD" else f"{rt}26-{counters[rt]:02d}")
            pv = "PV1.0" if g["start"] < PV2_START else "PV2.0"
            gmp = rt in ("ENG", "PPQ")
            suite = "GMP Suite 2" if gmp else "PD Lab B2"
            add("batch_master", batch_id=bid, lp_id=lp_id, run_type=rt, proc_ver=pv,
                run_purpose=g["purpose"], doe_id=g.get("doe"), start_dt=g["start"], suite=suite,
                operator=f"OP-{int(rng.integers(1, 7)):02d}", batch_status="COMPLETE", comments=None)

            day0 = datetime.combine(g["start"], datetime.min.time())
            # ---- UO01 apheresis receipt
            alloc = lp_vol / g["n"]
            rcpt = day0 + timedelta(hours=7.5, minutes=int(rng.integers(0, 60)))
            cd3 = dnr["cd3"] + float(rng.normal(0, 1.0))
            add("uo01_aph_receipt", batch_id=bid, lp_id=lp_id, rcpt_ts=rcpt, alloc_vol_ml=round(alloc, 1),
                tnc_e9=round(lp_tnc / g["n"], 3), via_pct=round(lp_via, 1), cd3_pct=round(cd3, 1),
                cd4_pct=round(cd3 * cd4_frac, 1), cd8_pct=round(cd3 * (1 - cd4_frac) * 0.95, 1),
                cd19_pct=round(float(rng.uniform(5, 14)), 1), mono_pct=round(float(rng.uniform(14, 28)), 1),
                hold_hrs=round(float(rng.uniform(20, 30)), 1), temp_c=round(float(rng.uniform(3.2, 6.8)), 1))

            # ---- UO02 selection
            sel_ts = rcpt + timedelta(hours=2, minutes=int(rng.integers(0, 50)))
            tnc_pre = lp_tnc / g["n"]
            recov = float(rng.uniform(62, 80))
            purity = float(rng.uniform(92, 98))
            tnc_post = tnc_pre * cd3 / 100 * recov / 100 / (purity / 100)
            prdg = g.get("prdg", "PRDG-PD-01")
            sel_lot = lambda code: _lot_for(lot_windows[code], g["start"])  # noqa: E731
            add("uo02_tcell_sel", batch_id=bid, sel_ts=sel_ts, equip_id=prdg,
                bead_lot_cd4=sel_lot("BEAD-CD4"), bead_lot_cd8=sel_lot("BEAD-CD8"),
                tnc_pre_e9=round(tnc_pre, 3), tnc_post_e9=round(tnc_post, 3),
                via_pct=round(float(rng.uniform(93, 98)), 1), cd3_pct=round(purity, 1),
                cd4_cd8_ratio=round(cd4_frac / (1 - cd4_frac) * float(rng.normal(1, 0.05)), 2),
                recov_pct=round(recov, 1))

            # ---- UO03 activation
            act_ts = sel_ts + timedelta(hours=3, minutes=int(rng.integers(0, 60)))
            if pv == "PV1.0":
                seed_dens, seed_tgt, cyto1, cyto2 = float(rng.normal(1.0, 0.03)), 100.0, sel_lot("CYT-IL2"), None
            else:
                seed_dens, seed_tgt, cyto1, cyto2 = float(rng.normal(0.5, 0.02)), 60.0, sel_lot("CYT-IL7"), sel_lot("CYT-IL15")
            seed = min(tnc_post * 1000 * 0.9, seed_tgt + float(rng.normal(0, 3)))
            act_vol = seed / seed_dens
            add("uo03_activation", batch_id=bid, act_ts=act_ts, act_lot=sel_lot("ACT-TRANSACT"),
                media_lot=sel_lot("MED-TEXMACS"), cyto_lot_1=cyto1, cyto_lot_2=cyto2,
                vessel="G-Rex100M-CS" if gmp else "G-Rex100M", seed_dens_e6_ml=round(seed_dens, 2),
                seed_cells_e6=round(seed, 1), act_vol_ml=round(act_vol, 1))

            # ---- process settings
            hrs_post = float(rng.normal(24, 1.2))
            if g["purpose"] == "Robustness" and rng.random() < 0.6:
                hrs_post = float(rng.choice([18.0, 30.0, 40.0])) + float(rng.normal(0, 0.5))
            moi = g["mois"][k] if g.get("mois") else 5.0
            hvst_day = 10 if pv == "PV1.0" else 8
            if g["purpose"] == "Robustness" and rng.random() < 0.4:
                hvst_day += int(rng.choice([-1, 1]))
            if gmp:
                inc = g["inc"]
            else:
                inc = pd_inc_cycle[(counters["PD"] + k) % 2]

            # ---- growth simulation (hourly)
            td_ts = act_ts + timedelta(hours=hrs_post)
            hvst_ts = day0 + timedelta(days=hvst_day, hours=9, minutes=int(rng.integers(0, 90)))
            td_days = (1.50 if pv == "PV1.0" else 1.42) / dnr["growth"] * float(rng.normal(1, 0.035))
            mu = math.log(2) / (td_days * 24)
            v_base = float(rng.normal(94.0, 1.0)) - (2.5 if dnr["low"] else 0)
            exposed = inc == "INC-03"
            N, t = seed, act_ts
            traj = {}
            exc_drop = 0.0
            while t <= hvst_ts + timedelta(hours=1):
                h = (t - act_ts).total_seconds() / 3600
                traj[t.replace(minute=0, second=0)] = (N, exc_drop)
                if exposed and INC3_DOOR_OPEN <= t < INC3_RECOVERED:
                    rate = mu * 0.15          # ~33.6 C, low CO2: growth nearly stops
                    # viability hit, larger for older/denser cultures; decays after recovery
                    exc_drop = 8.0 + 18.0 * min(1.0, h / 24 / 7)
                elif exposed and INC3_RECOVERED <= t < INC3_RECOVERED + timedelta(hours=12):
                    rate = mu * 0.4
                elif h < 48:
                    rate = math.log(0.85) / 48
                else:
                    rate = mu
                N *= math.exp(rate)
                t += timedelta(hours=1)

            def state(ts):
                key = ts.replace(minute=0, second=0)
                n, drop = traj.get(key, list(traj.values())[-1])
                hrs = (ts - act_ts).total_seconds() / 3600
                days = hrs / 24
                v = v_base - 7 * math.exp(-((days - 2.0) ** 2) / 1.5)
                if drop > 0 and ts >= INC3_DOOR_OPEN:
                    v -= drop * math.exp(-max(0.0, (ts - INC3_RECOVERED).total_seconds() / 3600) / 72)
                return n, v

            # ---- UO04 transduction
            cells_td = state(td_ts)[0]
            vlot = _lot_for(vec_windows, td_ts.date())
            add("uo04_transduction", batch_id=bid, td_ts=td_ts, hrs_post_act=round(hrs_post, 1), vec_lot=vlot,
                moi_tgt=moi, cells_at_td_e6=round(cells_td, 1),
                vec_vol_ul=round(moi * cells_td * 1e6 / vec_ft[vlot] * 1000, 1), enh_lot="VF-2602")
            potency = vec_potency[vlot]
            if vlot == BAD_VECTOR_LOT and td_ts > FRZ_FAIL_START:
                potency *= 0.38
            moi_eff = moi * potency
            act_factor = math.exp(-(((hrs_post - 26) / 16) ** 2))
            k_te = 0.10 * dnr["te"] * act_factor
            te = 100 * (1 - math.exp(-k_te * moi_eff)) + float(rng.normal(0, 2.0))
            # copies per transduced (CAR+) cell rises with effective MOI; bulk = per-CAR+ x fraction CAR+
            vcn_car = (1 + 0.25 * moi_eff) * float(rng.lognormal(0, 0.10))
            vcn = vcn_car * max(te, 1.0) / 100

            # ---- UO05 expansion samples
            sample_days = [3, 5, 7, hvst_day - 1, hvst_day] if pv == "PV1.0" else [3, 5, 7, hvst_day]
            sample_days = sorted(set(sample_days))
            gluc_mass, lac_mass, vol = 3.0 * act_vol / 1000, 0.2 * act_vol / 1000, act_vol
            last = act_ts
            for dn in sample_days:
                s_ts = day0 + timedelta(days=dn, hours=8, minutes=int(rng.integers(30, 80)))
                if dn == hvst_day:
                    s_ts = hvst_ts - timedelta(minutes=30)
                n_s, v_s = state(s_ts)
                # nutrient consumption since last sample
                n_prev = state(last)[0]
                cell_hours = (n_prev + n_s) / 2 * (s_ts - last).total_seconds() / 3600
                used = min(gluc_mass - 0.05 * vol / 1000, 4.2e-6 * cell_hours)
                gluc_mass -= used
                lac_mass += 0.85 * used
                feed = 0.0
                if dn == 3:
                    feed = 500 - vol
                elif dn == 5:
                    feed = 1000 - vol
                add("uo05_expansion", batch_id=bid, day_no=dn, sample_ts=s_ts, equip_id=inc,
                    cult_vol_ml=round(vol, 1), vcd_e6_ml=round(n_s / vol, 3),
                    via_pct=round(v_s + float(rng.normal(0, 0.6)), 1), tvc_e6=round(n_s, 1),
                    gluc_g_l=round(gluc_mass / vol * 1000, 2), lac_g_l=round(lac_mass / vol * 1000, 2),
                    feed_vol_ml=round(feed, 1) if feed > 0 else 0.0,
                    car_pos_pct=round(te + float(rng.normal(-3, 2.5)), 1) if dn == 5 else None)
                if feed > 0:
                    gluc_mass += 3.0 * feed / 1000
                    vol += feed
                last = s_ts

            # ---- UO06 harvest
            n_h, v_h = state(hvst_ts)
            v_h += float(rng.normal(0, 0.6))
            wash = float(rng.uniform(86, 95))
            add("uo06_harvest", batch_id=bid, hvst_ts=hvst_ts, hvst_day=hvst_day, tvc_e9=round(n_h / 1000, 3),
                via_pct=round(v_h, 1), equip_id="LOVO-01" if gmp else "LOVO-PD-01",
                post_wash_tvc_e9=round(n_h / 1000 * wash / 100, 3), wash_recov_pct=round(wash, 1))

            # ---- UO07 formulation / fill / cryo
            ff_ts = hvst_ts + timedelta(hours=4, minutes=int(rng.integers(0, 60)))
            viable = n_h * wash / 100 * v_h / 100
            n_bags = int(min(5, max(1, math.ceil(viable / (30 * 70)))))
            add("uo07_form_fill", batch_id=bid, ff_ts=ff_ts, cryo_lot=sel_lot("CRYO-CS10"), tgt_conc_e6_ml=30.0,
                fill_vol_ml=70.0, n_bags=n_bags, equip_id="CRF-01" if gmp else "CRF-PD-01",
                crf_profile="CRF-P01", post_thaw_via_pct=round(v_h - float(rng.normal(5.5, 1.5)), 1))

            # ---- QC
            purpose = "RELEASE" if rt == "PPQ" else ("RELEASE-INFO" if rt == "ENG" else "CHAR")
            tscm = float(rng.normal(18, 3.5)) if pv == "PV1.0" else float(rng.normal(34, 4.0))
            ratio = cd4_frac / (1 - cd4_frac) * 0.85 * float(rng.normal(1, 0.06))
            ifng = max(200.0, 260 * te + float(rng.normal(0, 700)))
            q_dt = hvst_ts.date() + timedelta(days=int(rng.integers(1, 4)))
            tests = [
                ("VIAB-NC200", v_h - 0.5 + float(rng.normal(0, 0.6)), None, "%", 70, None, None),
                ("FC-CAR", te, None, "% of CD3+", 20, None, None),
                ("VCN-DDPCR", vcn, None, "copies/cell (all cells)", None, None, "Report"),
                ("VCN-PER-CAR", vcn_car, None, "copies/CAR+ cell", None, 5.0, None),
                ("FC-CD3", float(rng.uniform(95.5, 99.2)), None, "%", 80, None, None),
                ("FC-CD4CD8", ratio, None, "ratio", None, None, "Report"),
                ("FC-TSCM", tscm, None, "% of CD3+", None, None, "Report"),
                ("POT-IFNG", ifng, None, "pg/mL", 1000, None, None),
                ("ENDO-LAL", None, "<0.5", "EU/mL", None, 5.0, None),
                ("STER-BACT", None, "NO GROWTH", None, None, None, "No growth"),
                ("MYCO-PCR", None, "NOT DETECTED", None, None, None, "Not detected"),
                ("ID-CAR-PCR", None, "POSITIVE", None, None, None, "Positive"),
            ]
            for code, val, txt, uom, lo, hi, stxt in tests:
                if val is not None:
                    val = round(val, 2) if code in ("VCN-DDPCR", "VCN-PER-CAR", "FC-CD4CD8") else round(val, 1)
                if rt == "PD":
                    pf, stxt2 = None, (stxt or "Provisional target (PD, info only)")
                else:
                    ok = True
                    if val is not None and lo is not None and val < lo:
                        ok = False
                    if val is not None and hi is not None and val > hi:
                        ok = False
                    if rt == "PPQ":
                        pf = "PASS" if ok else "FAIL"
                    else:  # engineering runs: release panel for information, not a release decision
                        pf = "CONFORMS" if ok else "NONCONFORMING (INFO)"
                    stxt2 = stxt
                    if stxt == "Report":
                        pf = "REPORTED"
                qc_rows.append(dict(batch_id=bid, test_code=code, test_purpose=purpose,
                                    test_dt=q_dt + timedelta(days=12) if code == "STER-BACT" else q_dt,
                                    result_val=val, result_txt=txt, uom=uom, spec_lo=lo, spec_hi=hi,
                                    spec_txt=stxt2, pass_fail=pf))
    T["qc_rel_results"] = qc_rows

    # ------------------------------------------------------------------
    # EMS alarms (equipment_event) and historian
    # ------------------------------------------------------------------
    ev = []

    def event(equip, etype, code, start, ack, ack_by, end, desc):
        ev.append(dict(equip_id=equip, event_type=etype, alarm_code=code, start_ts=start, ack_ts=ack,
                       ack_by=ack_by, end_ts=end, event_desc=desc))

    # Pre-change: after-hours alarms escalated to on-call within minutes
    event("INC-02", "ALARM", "ALM-DOOR", datetime(2026, 1, 21, 23, 12), datetime(2026, 1, 21, 23, 26), "ONCALL-02",
          datetime(2026, 1, 21, 23, 31), "Door open alarm. On-call responded, door latched.")
    event("FRZ-80-01", "ALARM", "ALM-TEMP-HI", datetime(2026, 2, 7, 3, 40), datetime(2026, 2, 7, 3, 58), "ONCALL-01",
          datetime(2026, 2, 7, 4, 20), "High temp alarm during defrost cycle; cleared.")
    event("INC-04", "ALARM", "ALM-CO2-LO", datetime(2026, 2, 26, 14, 5), datetime(2026, 2, 26, 14, 9), "OP-03",
          datetime(2026, 2, 26, 14, 30), "CO2 low after cylinder changeover.")
    event("INC-01", "ALARM", "ALM-DOOR", datetime(2026, 3, 7, 1, 50), datetime(2026, 3, 7, 2, 11), "ONCALL-03",
          datetime(2026, 3, 7, 2, 15), "Door open alarm. On-call responded.")
    # Post-change: after-hours alarms acknowledged next morning only
    event("FRZ-80-02", "ALARM", "ALM-TEMP-HI", FRZ_ALARM, FRZ_FAIL_ACK, "WH-02", FRZ_REPAIRED,
          "High temperature alarm. Compressor not running. Contents relocated to FRZ-80-01.")
    event("INC-01", "ALARM", "ALM-CO2-LO", datetime(2026, 5, 23, 3, 5), datetime(2026, 5, 23, 8, 40), "OP-05",
          datetime(2026, 5, 23, 3, 25), "CO2 low, self-cleared.")
    event("INC-03", "ALARM", "ALM-DOOR", INC3_DOOR_OPEN, INC3_DOOR_CLOSED, "OP-04", INC3_DOOR_CLOSED,
          "Door open alarm.")
    event("INC-03", "ALARM", "ALM-TEMP-LO", INC3_DOOR_OPEN + timedelta(minutes=42), INC3_DOOR_CLOSED, "OP-04",
          INC3_RECOVERED, "Temperature low alarm.")
    event("INC-02", "ALARM", "ALM-DOOR", datetime(2026, 7, 7, 14, 12), datetime(2026, 7, 7, 14, 16), "OP-02",
          datetime(2026, 7, 7, 14, 17), "Door open > 60 s during vessel loading.")
    event("FRZ-80-01", "ALARM", "ALM-TEMP-HI", datetime(2026, 8, 15, 4, 2), datetime(2026, 8, 15, 9, 55), "WH-01",
          datetime(2026, 8, 15, 4, 30), "High temp alarm during defrost cycle; self-cleared.")
    # Maintenance / calibration
    for eq, dt_ in [("INC-01", datetime(2026, 4, 2, 10)), ("INC-02", datetime(2026, 4, 2, 13)),
                    ("INC-03", datetime(2026, 4, 3, 10)), ("INC-04", datetime(2026, 4, 3, 13))]:
        event(eq, "CALIBRATION", None, dt_, None, None, dt_ + timedelta(hours=2),
              "Quarterly temperature and CO2 sensor calibration. As-found within tolerance.")
    event("FRZ-80-02", "MATERIAL MOVE", None, FRZ_CONTENTS_MOVED, None, "WH-02", FRZ_CONTENTS_MOVED,
          "All contents relocated to FRZ-80-01. Unit powered down for repair.")
    event("FRZ-80-02", "MAINTENANCE", None, datetime(2026, 4, 21, 9), None, None, FRZ_REPAIRED,
          "Compressor replaced (like-for-like). Pull-down verified.")
    event("FRZ-80-02", "MATERIAL MOVE", None, datetime(2026, 4, 24, 14), None, "WH-02", datetime(2026, 4, 24, 14),
          "Contents returned from FRZ-80-01 after OQ re-execution (CC-26-014).")
    ev.sort(key=lambda r: r["start_ts"])
    for i, r in enumerate(ev, 1):
        r["event_id"] = f"EV-26-{i:04d}"
    T["equipment_event"] = ev

    hist = []
    hours = int((HIST_END - HIST_START).total_seconds() // 3600) + 1
    ts_list = [HIST_START + timedelta(hours=h) for h in range(hours)]
    for inc in ["INC-01", "INC-02", "INC-03", "INC-04"]:
        tag = inc.replace("-", "")
        temps = rng.normal(37.0, 0.06, hours)
        co2 = rng.normal(5.0, 0.04, hours)
        for i, ts in enumerate(ts_list):
            tv, cv = temps[i], co2[i]
            if inc == "INC-03" and INC3_DOOR_OPEN <= ts < INC3_RECOVERED + timedelta(hours=1):
                hrs_open = (min(ts, INC3_DOOR_CLOSED) - INC3_DOOR_OPEN).total_seconds() / 3600
                if ts < INC3_DOOR_CLOSED:
                    tv = 37.0 - 3.4 * (1 - math.exp(-hrs_open / 1.2)) + float(rng.normal(0, 0.05))
                    cv = 5.0 - 3.9 * (1 - math.exp(-hrs_open / 0.8)) + float(rng.normal(0, 0.05))
                else:
                    since = (ts - INC3_DOOR_CLOSED).total_seconds() / 3600
                    tv = 33.6 + 3.4 * (1 - math.exp(-since / 0.6))
                    cv = 1.1 + 3.9 * (1 - math.exp(-since / 0.4))
            q = "GOOD"
            if rng.random() < 0.0015:
                q, tv = "BAD", None
            hist.append(dict(tag=f"{tag}.TEMP.PV", ts=ts, val=None if tv is None else round(float(tv), 2), qual=q))
            hist.append(dict(tag=f"{tag}.CO2.PV", ts=ts, val=round(float(cv), 2), qual="GOOD"))
    for frz in ["FRZ-80-01", "FRZ-80-02"]:
        tag = frz.replace("-", "")
        temps = rng.normal(-80.0, 0.6, hours)
        for i, ts in enumerate(ts_list):
            tv = temps[i]
            if frz == "FRZ-80-02" and FRZ_FAIL_START <= ts < FRZ_REPAIRED + timedelta(hours=6):
                if ts < FRZ_REPAIRED:
                    since = (ts - FRZ_FAIL_START).total_seconds() / 3600
                    tv = -80 + 70 * (1 - math.exp(-since / 14))
                else:
                    since = (ts - FRZ_REPAIRED).total_seconds() / 3600
                    tv = max(-80.0, -10 - 70 * (1 - math.exp(-since / 1.5)))
            hist.append(dict(tag=f"{tag}.TEMP.PV", ts=ts, val=round(float(tv), 2), qual="GOOD"))
    T["hist_tag_data"] = hist
    return T
