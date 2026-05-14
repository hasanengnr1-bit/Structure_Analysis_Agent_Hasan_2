"""
shear_wall_calc.py
Shear Wall Calculator — SDPWS / NDS / ASCE 7-16.

Implements:
  - PERF (Perforated) — per SDPWS §4.3.5.3, with Co adjustment
  - SEGMENT — per SDPWS §4.3.2, each full-height pier checked
  - FTAO — Force Transfer Around Openings, identical to SEGMENT per workbook
           (full FTAO drag-strut analysis to be built separately)

Based on SWL_First_Floor.xlsx formulas.

Run:   python shear_wall_calc.py
Import: from shear_wall_calc import check_shear_wall
"""

import math
from dataclasses import dataclass, field
from typing import Literal, Optional, List


# ============================================================
# §3 — Lookup Tables
# ============================================================

# SDPWS Table 4.3A — Nominal unit shear capacity (plf)
V_SEISMIC = {
    ("7/16", 6): 480,  ("7/16", 4): 700,  ("7/16", 3): 900,
    ("15/32", 6): 520, ("15/32", 4): 760, ("15/32", 3): 980,
}
V_WIND = {
    ("7/16", 6): 670,  ("7/16", 4): 980,  ("7/16", 3): 1260,
    ("15/32", 6): 730, ("15/32", 4): 1065, ("15/32", 3): 1370,
}

# Anchor bolt Z-parallel (lbs) — key: (ab_dia, sill_type)
AB_Z_PARA = {
    # ab_dia: {(1)-2x, (1)-3x, (2)-2x, (3)-2x}
    0.500:  [530,  680,  680,  690],
    0.625:  [780,  940,  940,  1070],
    0.750:  [1100, 1240, 1240, 1470],
    0.875:  [1280, 1600, 1600, 1840],
    1.000:  [1460, 2030, 2030, 2260],
}
AB_Z_PERP = {
    0.500:  [290, 340, 340, 400],
    0.625:  [320, 460, 460, 520],
    0.750:  [350, 580, 580, 660],
    0.875:  [370, 610, 610, 820],
    1.000:  [410, 680, 680, 950],
}
SILL_TYPE_MAP = {"(1)-2x": 0, "(1)-3x": 1, "(2)-2x": 2, "(3)-2x": 3}

# Chord cross-sectional area A (in²) — AD29:AE42
CHORD_AREA = {
    "(1) 2x6": 8.25,  "(2) 2x6": 16.5,  "(3) 2x6": 24.75, "(4) 2x6": 33.0,
    "4x4": 12.25, "4x6": 19.25, "6x6": 30.25, "6x8": 39.875,
    "(1) 2x4": 5.25,  "(2) 2x4": 10.5,  "(3) 2x4": 15.75,
    "(1) 2x8": 10.875, "(2) 2x8": 21.75, "(3) 2x8": 32.625,
}

# Holdown deflection da (in) — AG30:AU40
# Columns: (1)2x6, (2)2x6, (3)2x6, (4)2x6, 4x4, 4x6, 6x6, 6x8, (1)2x4, (2)2x4, (3)2x4, (1)2x8, (2)2x8, (3)2x8
DA_COLUMNS = ["(1) 2x6", "(2) 2x6", "(3) 2x6", "(4) 2x6", "4x4", "4x6", "6x6", "6x8",
             "(1) 2x4", "(2) 2x4", "(3) 2x4", "(1) 2x8", "(2) 2x8", "(3) 2x8"]
DA_TABLE = {
    "DTT2Z":    [0.105, 0.128, 0.128, 0.128, 0.128, 0.128, 0.128, 0.128, 0.105, 0.128, 0.128, 0.105, 0.128, 0.128],
    "HDU2":     [None,  0.088, 0.088, 0.088, 0.088, 0.088, 0.088, 0.088, None,  0.088, 0.088, None,  0.088, 0.088],
    "HDU4":     [None,  0.114, 0.114, 0.114, 0.114, 0.114, 0.114, 0.114, None,  0.114, 0.114, None,  0.114, 0.114],
    "HDU5":     [None,  0.115, 0.115, 0.115, 0.115, 0.115, 0.115, 0.115, None,  0.115, 0.115, None,  0.115, 0.115],
    "HDU8":     [None,  0.084, 0.113, 0.113, 0.116, 0.116, 0.113, 0.113, None,  0.084, 0.113, None,  0.084, 0.113],
    "HDU11":    [None,  None,  None,  0.137, None,  0.137, 0.137, 0.137, None,  None,  None,  None,  None,  None],
    "HDU14":    [None,  None,  None,  0.177, None,  0.122, 0.177, 0.177, None,  None,  None,  None,  None,  None],
    "STHD10":   [None,  0.146, 0.146, 0.146, 0.146, 0.146, 0.146, 0.146, None,  0.146, 0.146, None,  0.146, 0.146],
    "STHD10RJ": [None,  0.146, 0.146, 0.146, 0.146, 0.146, 0.146, 0.146, None,  0.146, 0.146, None,  0.146, 0.146],
    "STHD14":   [None,  0.164, 0.164, 0.164, 0.164, 0.164, 0.164, 0.164, None,  0.164, 0.164, None,  0.164, 0.164],
    "STHD14RJ": [None,  0.164, 0.164, 0.164, 0.164, 0.164, 0.164, 0.164, None,  0.164, 0.164, None,  0.164, 0.164],
}

# Holdown allowable tension (lbs) — P5:U11
HOLDOWN_ALLOWABLE = {
    # model: (ab_dia, wood_thk, tension_SPF_HF, tension_DF_SP, min_stud_thk)
    "DTT2Z":  (0.500, 3, 1835, 2145, 3),
    "HDU2":   (0.625, 3, 2215, 3075, 3),
    "HDU4":   (0.625, 3, 3285, 4565, 3),
    "HDU5":   (0.625, 3, 4065, 5645, 3),
    "HDU8":   (0.875, 4.5, 5665, 7870, 4.5),
    "HDU11":  (1.000, 5.5, 6865, 9535, 5.5),
    "HDU14":  (1.000, 5.5, 10350, 14445, 5.5),
}

# Framing clips — Z22:AC26
CLIPS = {
    "A35":  {"allowable": 600,  "direction": "F1", "note": "Provide full depth blocking with A35 clips to top plt. per plan."},
    "A34":  {"allowable": 445,  "direction": "F1", "note": "Provide full depth blocking with A34 clips to top plt. per plan."},
    "LTP4": {"allowable": 575,  "direction": "G",  "note": "Provide positive connection btw. sheathing with LTP4 clips per plan."},
    "LTP5": {"allowable": 535,  "direction": "G",  "note": "Provide positive connection btw. sheathing with LTP5 clips per plan."},
    "H1":   {"allowable": 415,  "direction": "F1", "note": "Provide full depth blocking with H1 ties to top plt. per plan."},
}

# Plate bearing Fc_perp (psi) — P50:R51
PLATE_FC_PERP = {"DF": 625, "HF": 405}

# Chord properties — DF No. 2 (P55:Y68)
# size: (Ft, Fc, CFT, CFC, Emin, E, dx, lb)
CHORD_PROPS = {
    "(1) 2x6": (575, 1350, 1.3, 1.1, 580000, 1600000, 5.5, 1.5),
    "(2) 2x6": (575, 1350, 1.3, 1.1, 580000, 1600000, 5.5, 3.0),
    "(3) 2x6": (575, 1350, 1.3, 1.1, 580000, 1600000, 5.5, 4.5),
    "(4) 2x6": (575, 1350, 1.3, 1.1, 580000, 1600000, 5.5, 6.0),
    "4x4":     (575, 1350, 1.5, 1.15, 580000, 1600000, 3.5, 3.5),
    "4x6":     (575, 1350, 1.3, 1.1, 580000, 1600000, 5.5, 3.5),
    "6x6":     (475, 700,  1.0, 1.0,  470000, 1300000, 5.5, 5.5),
    "6x8":     (475, 700,  1.0, 1.0,  470000, 1300000, 5.5, 7.25),
    "(1) 2x4": (575, 1350, 1.5, 1.15, 580000, 1600000, 3.5, 1.5),
    "(2) 2x4": (575, 1350, 1.5, 1.15, 580000, 1600000, 3.5, 3.0),
    "(3) 2x4": (575, 1350, 1.5, 1.15, 580000, 1600000, 3.5, 4.5),
    "(1) 2x8": (575, 1350, 1.2, 1.05, 580000, 1600000, 7.25, 1.5),
    "(2) 2x8": (575, 1350, 1.2, 1.05, 580000, 1600000, 7.25, 3.0),
    "(3) 2x8": (575, 1350, 1.2, 1.05, 580000, 1600000, 7.25, 4.5),
}

# Deflection constants — Q40:Q42
EN_BASE = 616
EN_EXP = 3.018
STRUCT_I_FACTOR = 1.2
GT_STIFFNESS = 83500   # plf, SDPWS Table C4.2.2A
E_CHORD = 1600000       # psi


def _cb(lb):
    """Cb = (lb + 0.375) / lb if lb < 6 else 1"""
    if lb < 6:
        return (lb + 0.375) / lb
    return 1.0


# ============================================================
# §1 / §2 — Inputs
# ============================================================
@dataclass
class ShearWallInputs:
    # Loads & geometry
    Vs: float = 2295              # Seismic shear at top of wall (lbs)
    Vw: float = 2815              # Wind shear at top of wall (lbs)
    wall_length_total: float = 46  # Total wall length (ft)
    wall_height: float = 12       # Wall height (ft)
    wall_type: str = "PERF"       # "PERF" / "FTAO" / "SEGMENT"
    Co: float = 0.97              # PERF adjustment factor
    sum_Li: float = 19            # Sum of full-height segment lengths (ft)
    bs_perf: float = 9.75         # Min panel length (ft, PERF)

    # Sheathing & nailing
    nail_edge_spacing: int = 4    # 3, 4, or 6 in
    sheathing_both_sides: bool = False
    panel_thickness: str = "15/32"  # "7/16" or "15/32"
    fastener_type: str = "10d"

    # Holdown & chord
    holdown_model: str = "HDU2"
    chord_studs: str = "(2) 2x6"
    chord_species: str = "DF No. 2"

    # Sill plate
    sill_plate_type: str = "(1)-2x"
    ab_diameter: float = 0.625

    # Out-of-plane
    WDL: float = 12              # psf wall dead weight
    SDS: float = 0.625
    Ie: float = 1.0
    ka: float = 1.0
    rho: float = 1.0
    Ww: float = 18.54            # psf wind MWFRS
    Ltrib: float = 4.5           # ft tributary height

    # Collector / clips
    La: float = 8                # ft available wall length for AB
    clip_model: str = "A35"
    Lac: float = 28              # ft available collector length
    clip_spacing: float = 24     # in o/c

    # Panels (up to 5)
    panels: List[float] = field(default_factory=lambda: [9.75, 7.14, 7.5, 2.0, 5.0])

    # Bearing / chord
    top_sill_species: str = "HF"  # "DF" or "HF"
    WDL_plf: float = 95
    WLL_plf: float = 40
    WSL_plf: float = 0
    PDL: float = 0               # Point DL at chord (lbs)
    PLL: float = 0
    PSL: float = 0
    PW: float = 0                # Point wind at chord (lbs)
    PS: float = 0                # Point seismic at chord (lbs)
    stud_spacing: int = 16       # in


# ============================================================
# §4 — Calculation Engine
# ============================================================
def check_shear_wall(inp: ShearWallInputs):
    """Run all shear wall checks. Returns structured dict."""
    h = inp.wall_height
    is_perf = inp.wall_type == "PERF"

    # ---- Helpers ----
    key_panel = (inp.panel_thickness, inp.nail_edge_spacing)

    def _lookup_panel(table):
        """Lookup nominal unit shear for (thickness, spacing)."""
        return table.get(key_panel, 0)

    def _lookup_ab(table):
        idx = SILL_TYPE_MAP.get(inp.sill_plate_type, 0)
        row = table.get(inp.ab_diameter)
        if row is None:
            dias = sorted(table.keys())
            for i in range(len(dias) - 1):
                if dias[i] <= inp.ab_diameter <= dias[i + 1]:
                    lo = table[dias[i]][idx]; hi = table[dias[i + 1]][idx]
                    return lo + (hi - lo) * (inp.ab_diameter - dias[i]) / (dias[i + 1] - dias[i])
            for d in dias:
                if d >= inp.ab_diameter:
                    return table[d][idx]
            return table[dias[-1]][idx]
        return row[idx]

    def _da_lookup(holdown, chord):
        row = DA_TABLE.get(holdown)
        if row is None:
            return None
        try:
            idx = DA_COLUMNS.index(chord)
        except ValueError:
            return None
        return row[idx]

    # ============================================================
    # §4.1 — Governing shear & geometry
    # ============================================================
    shear_design = max(inp.Vs, inp.Vw)

    swl_length_segments = sum(b for b in inp.panels if b > 0)
    panel_count = sum(1 for b in inp.panels if b > 0)

    if is_perf:
        unit_shear_v = shear_design / (inp.Co * inp.sum_Li) if (inp.Co * inp.sum_Li) > 0 else 0
    else:
        unit_shear_v = shear_design / swl_length_segments if swl_length_segments > 0 else 0

    # Per-panel unit shear for individual checks
    if is_perf:
        vs = inp.Vs / (inp.Co * inp.sum_Li) if (inp.Co * inp.sum_Li) > 0 else 0
        vw = inp.Vw / (inp.Co * inp.sum_Li) if (inp.Co * inp.sum_Li) > 0 else 0
    else:
        vs = inp.Vs / swl_length_segments if swl_length_segments > 0 else 0
        vw = inp.Vw / swl_length_segments if swl_length_segments > 0 else 0

    # ============================================================
    # §4.2 — Allowables & code checks
    # ============================================================
    v_seismic_nominal = _lookup_panel(V_SEISMIC)
    v_wind_nominal = _lookup_panel(V_WIND)

    # Aspect-ratio reduction
    bs_min = inp.bs_perf if is_perf else min((b for b in inp.panels if b > 0), default=0)
    AR_max = h / bs_min if bs_min > 0 else 0
    AR_reduction = (2.0 * bs_min) / h if AR_max > 2 else None
    AR_check_ok = AR_max < 3.5

    v_seismic_adj = v_seismic_nominal
    if AR_reduction is not None:
        v_seismic_adj = AR_reduction * v_seismic_nominal

    half_factor = 1.0 if inp.sheathing_both_sides else 0.5
    v_allow_seismic = half_factor * v_seismic_adj
    v_allow_wind = half_factor * v_wind_nominal

    seismic_shear_ok = v_allow_seismic > vs
    wind_shear_ok = v_allow_wind > vw

    # ============================================================
    # §4.3 — Sill plate & anchor bolt design
    # ============================================================
    Z_para = _lookup_ab(AB_Z_PARA)
    Z_perp = _lookup_ab(AB_Z_PERP)
    CD = 1.6
    Z_para_adj = Z_para * CD
    Z_perp_adj = Z_perp * CD

    # Out-of-plane forces
    Vs_perp = 0.7 * inp.rho * 0.4 * inp.SDS * inp.ka * inp.Ie * inp.WDL * h * inp.wall_length_total * 0.5
    Vw_perp = 0.6 * inp.Ww * inp.Ltrib * inp.wall_length_total
    V_perp = max(Vs_perp, Vw_perp)
    perp_governs = "Wind" if Vs_perp < Vw_perp else "Seismic"

    num_bolts_perp = V_perp / Z_perp_adj if Z_perp_adj > 0 else 0
    spacing_perp = inp.La / num_bolts_perp if num_bolts_perp > 0 else 999

    num_bolts_para = shear_design / Z_para_adj if Z_para_adj > 0 else 0
    spacing_para = inp.La / num_bolts_para if num_bolts_para > 0 else 999

    # ============================================================
    # §4.4 — Collector clip design
    # ============================================================
    clip_data = CLIPS.get(inp.clip_model, CLIPS["A35"])
    F_allow_clip = clip_data["allowable"]
    unit_shear_collector = shear_design / inp.Lac if inp.Lac > 0 else 0
    required_spacing_ft = F_allow_clip / unit_shear_collector if unit_shear_collector > 0 else 999
    clip_spacing_ok = inp.clip_spacing <= required_spacing_ft * 12

    # ============================================================
    # §4.5 — Per-panel deflection (4-term SDPWS §4.3.2)
    # ============================================================
    vu = vs * 1.4   # strength-level seismic plf
    A_chord = CHORD_AREA.get(inp.chord_studs, 16.5)
    da_val = _da_lookup(inp.holdown_model, inp.chord_studs)

    if da_val is None and _da_lookup(inp.holdown_model, inp.chord_studs) is None:
        holdown_error = "Studs do not meet min. wood member thickness for selected holdown"
    else:
        holdown_error = None

    # en — nail slip per SDPWS Table C4.2.2D
    if inp.sheathing_both_sides:
        v_nail = (vu * inp.nail_edge_spacing) / (12.0 * 2.0)
    else:
        v_nail = (vu * inp.nail_edge_spacing) / 12.0
    en = STRUCT_I_FACTOR * (v_nail / EN_BASE) ** EN_EXP if v_nail > 0 else 0

    # Per-panel deflection
    panel_results = []
    for bi in inp.panels:
        if bi <= 0:
            panel_results.append(None)
            continue

        b_safe = max(bi, 0.001)
        delta_b = (8.0 * vu * h ** 3) / (E_CHORD * A_chord * b_safe)
        delta_v = (vu * h) / (2.0 * GT_STIFFNESS) if inp.sheathing_both_sides else (vu * h) / GT_STIFFNESS
        delta_n = 0.75 * h * en

        if is_perf:
            delta_a = (h * da_val) / inp.sum_Li if (da_val and inp.sum_Li > 0) else 0
        else:
            delta_a = (h * da_val) / bi if (da_val and bi > 0) else 0

        delta_total = delta_b + delta_v + delta_n + delta_a

        # AR-based per-panel reduction
        AR_i = h / b_safe
        reduction_i = (2.0 * b_safe / h) if AR_i > 2 else 1.0
        v_allow_i = v_seismic_nominal * reduction_i
        bx_allow_i = v_allow_i * bi

        panel_results.append({
            "b_ft": bi,
            "delta_b": delta_b,
            "delta_v": delta_v,
            "delta_n": delta_n,
            "delta_a": delta_a,
            "delta_total": delta_total,
            "AR_i": AR_i,
            "v_allow_i": v_allow_i,
            "bx_allow_i": bx_allow_i,
        })

    # ============================================================
    # §4.6 — Aggregated deflection & drift
    # ============================================================
    valid_deltas = [p["delta_total"] for p in panel_results if p is not None]
    delta_max = max(valid_deltas) if valid_deltas else 0

    total_bx_allow = sum(p["bx_allow_i"] for p in panel_results if p is not None)
    sum_bi = sum(b for b in inp.panels if b > 0)

    v_allow_avg = v_seismic_adj if is_perf else (total_bx_allow / sum_bi if sum_bi > 0 else 0)

    Cd_deflection = 4.0
    delta_amplified = delta_max * Cd_deflection
    delta_limit = 0.02 * 12.0 * h
    drift_ok = delta_limit > delta_amplified

    # ============================================================
    # §4.8 — Chord uplift / compression
    # ============================================================
    if is_perf:
        L_eff = inp.Co * inp.sum_Li
        Pw_chord = inp.Vw * h / L_eff if L_eff > 0 else 0
        Ps_chord = inp.Vs * h / L_eff if L_eff > 0 else 0
    else:
        L_eff = swl_length_segments
        Pw_chord = inp.Vw * h / L_eff if L_eff > 0 else 0
        Ps_chord = inp.Vs * h / L_eff if L_eff > 0 else 0

    T_chord = max(Pw_chord + inp.PW, Ps_chord + inp.PS)

    # Compression combos (ASCE 7-10)
    WDL_stud = inp.WDL_plf * (inp.stud_spacing / 12.0)
    WLL_stud = inp.WLL_plf * (inp.stud_spacing / 12.0)
    WSL_stud = inp.WSL_plf * (inp.stud_spacing / 12.0)

    C_D_W = WDL_stud + inp.PDL + Pw_chord + inp.PW
    C_D_W_L = (WDL_stud + inp.PDL
               + 0.75 * WLL_stud + 0.75 * inp.PLL
               + 0.75 * WSL_stud + 0.75 * inp.PSL
               + 0.75 * Pw_chord + 0.75 * inp.PW)
    C_D_E = WDL_stud + inp.PDL + Ps_chord + inp.PS
    C_D_E_L = (WDL_stud + inp.PDL
               + 0.75 * WLL_stud + 0.75 * inp.PLL
               + 0.75 * WSL_stud + 0.75 * inp.PSL
               + 0.75 * Ps_chord + 0.75 * inp.PS)
    C_chord = max(C_D_W, C_D_W_L, C_D_E, C_D_E_L)

    # ============================================================
    # §4.9 — Sill plate bearing
    # ============================================================
    Fc_perp_base = PLATE_FC_PERP.get(inp.top_sill_species, 405)
    chord_prop = CHORD_PROPS.get(inp.chord_studs, CHORD_PROPS["(2) 2x6"])
    lb = chord_prop[7]
    Cb_val = _cb(lb)
    Fc_perp_adj = Fc_perp_base * 1.0 * 1.0 * Cb_val  # CM=1, Ct=1
    Ab = CHORD_AREA.get(inp.chord_studs, 16.5)
    fc_perp = C_chord / Ab if Ab > 0 else 0
    CSI_bearing = fc_perp / Fc_perp_adj if Fc_perp_adj > 0 else 0
    bearing_ok = CSI_bearing <= 1.0

    # ============================================================
    # §4.10 — Chord tension (NDS)
    # ============================================================
    Ft = chord_prop[0]
    CFT = chord_prop[2]
    Ft_adj = 1.0 * 1.0 * 1.0 * CD * Ft * CFT  # CM=Ci=Ct=1
    ft_actual = T_chord / Ab if Ab > 0 else 0
    CSI_tension = ft_actual / Ft_adj if Ft_adj > 0 else 0
    tension_ok = CSI_tension <= 1.0

    # ============================================================
    # §4.11 — Chord compression (NDS column buckling)
    # ============================================================
    Fc = chord_prop[1]
    CFC = chord_prop[3]
    Emin = chord_prop[4]
    dx = chord_prop[6]

    le_over_d = ((h * 12.0) - 4.5) / dx if dx > 0 else 1
    Emin_adj = Emin * 1.0 * 1.0 * 1.0  # CM=Ci=Ct=1

    FcE = (0.822 * Emin_adj) / (le_over_d ** 2) if le_over_d > 0 else 0
    Fc_star = Fc * CFC * CD * 1.0 * 1.0 * 1.0  # Ci=Ct=CM=1
    c_nds = 0.8  # sawn lumber

    if Fc_star > 0 and FcE > 0:
        ratio = FcE / Fc_star
        term_val = (1.0 + ratio) / (2.0 * c_nds)
        disc = term_val ** 2 - (ratio / c_nds)
        if disc > 0:
            Cp = term_val - math.sqrt(disc)
        else:
            Cp = 0
    else:
        Cp = 0

    Fc_adj = Fc_star * Cp
    fc_actual = C_chord / Ab if Ab > 0 else 0
    CSI_compression = fc_actual / Fc_adj if Fc_adj > 0 else 999
    compression_ok = CSI_compression <= 1.0

    # ============================================================
    # §4.12 — Bottom-plate nailing
    # ============================================================
    Z_nail = 141    # NDS Table 11Q, 16d in DF G=0.5
    Z_nail_adj = Z_nail * CD
    nail_spacing_in = 12.0 * Z_nail_adj / unit_shear_v if unit_shear_v > 0 else 999

    # ============================================================
    # §4.7 — Checksums
    # ============================================================
    b_sum = sum(inp.panels)
    diff = b_sum - sum_bi  # should be 0

    # ============================================================
    # §4.13 — Note strings
    # ============================================================
    apa_grade = "(APA Grade 24/16)" if inp.panel_thickness == "7/16" else "(APA Grade 32/16)"
    both_str = " Sheath both sides of shearwall." if inp.sheathing_both_sides else ""
    thick_note = (" Members and blocking at adjoining panel edges shall be min. 3\" nominal "
                  "or double 2\" nominal with staggered nailing at all panel edges.") if v_wind_nominal > 700 else ""
    sheathing_callout = (f"Use {inp.panel_thickness}\" OSB/PLY {apa_grade} w/ {inp.fastener_type} nails @ "
                         f"{inp.nail_edge_spacing}\" o/c edges, 12\" o/c field, blocking required.{both_str}{thick_note}")

    sill_text = "plate" if inp.sill_plate_type in ("(1)-2x", "(1)-3x") else "plates"
    sill_callout = f"Use {inp.sill_plate_type} HF No. 2 pressure treated {sill_text} at foundation."

    governs = "Wind" if inp.Vw > inp.Vs else "Seismic"

    return {
        "governs": governs,
        "shear_design_lbs": round(shear_design, 1),
        "unit_shear_v_plf": round(unit_shear_v, 4),
        "L_eff_ft": round(L_eff, 3),
        "seismic_shear": {
            "vs_plf": round(vs, 4),
            "v_allow_seismic_plf": round(v_allow_seismic, 1),
            "v_nominal_plf": v_seismic_nominal,
            "aspect_ratio": round(AR_max, 4),
            "ar_reduction": round(AR_reduction, 4) if AR_reduction else None,
            "ar_check": "OK" if AR_check_ok else "NG",
            "shear_check": "OK" if seismic_shear_ok else "NG",
        },
        "wind_shear": {
            "vw_plf": round(vw, 4),
            "v_allow_wind_plf": round(v_allow_wind, 1),
            "v_nominal_plf": v_wind_nominal,
            "shear_check": "OK" if wind_shear_ok else "NG",
        },
        "anchor_bolts": {
            "Z_para_lbs": round(Z_para, 1),
            "Z_perp_lbs": round(Z_perp, 1),
            "Z_para_adj_lbs": round(Z_para_adj, 1),
            "Z_perp_adj_lbs": round(Z_perp_adj, 1),
            "V_perp_lbs": round(V_perp, 1),
            "perp_governs": perp_governs,
            "num_para": round(num_bolts_para, 2),
            "spacing_para_ft": round(spacing_para, 3),
            "num_perp": round(num_bolts_perp, 2),
            "spacing_perp_ft": round(spacing_perp, 3),
        },
        "collector": {
            "clip_model": inp.clip_model,
            "F_allow_lbs": F_allow_clip,
            "unit_shear_plf": round(unit_shear_collector, 2),
            "req_spacing_ft": round(required_spacing_ft, 3),
            "provided_spacing_in": inp.clip_spacing,
            "check": "OK" if clip_spacing_ok else "Spacing of ties or angles is inadequate.",
        },
        "deflection": {
            "panel_details": panel_results,
            "delta_max_in": round(delta_max, 4),
            "delta_amplified_in": round(delta_amplified, 4),
            "delta_limit_in": round(delta_limit, 3),
            "drift_check": "OK" if drift_ok else "NG",
            "en_in": round(en, 6),
            "da_in": da_val if da_val else "NS",
            "holdown_error": holdown_error,
        },
        "chord": {
            "T_chord_lbs": round(T_chord, 1),
            "C_chord_lbs": round(C_chord, 1),
            "Ab_in2": Ab,
            "tension": {
                "ft_actual_psi": round(ft_actual, 1),
                "Ft_adj_psi": round(Ft_adj, 0),
                "CSI": round(CSI_tension, 4),
                "check": "OK" if tension_ok else "NG",
            },
            "bearing": {
                "fc_perp_psi": round(fc_perp, 2),
                "Fc_perp_adj_psi": round(Fc_perp_adj, 1),
                "CSI": round(CSI_bearing, 4),
                "check": "OK" if bearing_ok else "NG",
            },
            "compression": {
                "fc_actual_psi": round(fc_actual, 2),
                "Fc_adj_psi": round(Fc_adj, 2),
                "le_over_d": round(le_over_d, 2),
                "Cp": round(Cp, 4),
                "CSI": round(CSI_compression, 4),
                "check": "OK" if compression_ok else "NG",
            },
        },
        "bottom_plate_nailing": {
            "Z_per_nail_lbs": round(Z_nail_adj, 1),
            "spacing_calc_in": round(nail_spacing_in, 3),
        },
        "notes": {
            "sheathing_callout": sheathing_callout,
            "sill_callout": sill_callout,
            "governs": governs,
        },
        "summary": {
            "overall": "PASS" if all([
                seismic_shear_ok, wind_shear_ok, AR_check_ok, drift_ok,
                tension_ok, bearing_ok, compression_ok, clip_spacing_ok,
            ]) else "FAIL",
        },
    }


# ============================================================
# Legacy convenience wrapper (backward-compatible with old API)
# ============================================================
def check_shear_wall_legacy(name, method, wall_height_ft, wall_length_ft,
                            openings, v_demand_lbs):
    """Legacy wrapper for backward compatibility with old test code."""
    # Build panels from openings
    panels = [wall_length_ft]
    if openings:
        panels = _segments_from_openings(wall_length_ft, openings)

    is_perf = method.lower() == "perforated"
    l_sum_segments = sum(panels)
    sum_li = l_sum_segments
    max_op_h = max((o.get('h', 0) for o in openings), default=0)
    bs_min_val = min(panels) if panels else wall_length_ft

    co_val = 1.0
    if is_perf:
        alpha = l_sum_segments / wall_length_ft if wall_length_ft > 0 else 1.0
        co_val = alpha / (2.0 - alpha) if alpha < 1.0 else 1.0

    inp = ShearWallInputs(
        Vs=v_demand_lbs, Vw=v_demand_lbs,
        wall_length_total=wall_length_ft,
        wall_height=wall_height_ft,
        wall_type="PERF" if is_perf else "SEGMENT",
        Co=co_val,
        sum_Li=sum_li,
        bs_perf=bs_min_val,
        panels=panels,
        panel_thickness="7/16",
        nail_edge_spacing=6,
        sheathing_both_sides=False,
        holdown_model="HDU2",
        chord_studs="(2) 2x6",
        sill_plate_type="(1)-2x",
        ab_diameter=0.625,
        Ww=30, Ltrib=5, La=wall_length_ft, Lac=wall_length_ft,
        top_sill_species="DF",
        WDL_plf=100, WLL_plf=100,
    )
    result = check_shear_wall(inp)
    # Flatten for legacy output format
    return {
        "name": name,
        "method": method,
        "results": {
            "Unit Shear (plf)": {
                "Actual": round(result["unit_shear_v_plf"], 1),
                "Allowed": round(result["seismic_shear"]["v_allow_seismic_plf"], 1),
                "Result": round(result["unit_shear_v_plf"] / result["seismic_shear"]["v_allow_seismic_plf"] * 100, 1) if result["seismic_shear"]["v_allow_seismic_plf"] > 0 else 0,
                "LDF": "-",
                "Combo": result["governs"],
            },
            "Hold-down Tension (lbs)": {
                "Actual": round(result["chord"]["T_chord_lbs"], 1),
                "Allowed": 5000,
                "Result": round(result["chord"]["T_chord_lbs"] / 5000 * 100, 1),
                "LDF": "-",
                "Combo": result["governs"],
            },
            "Lateral Defl. (in)": {
                "Actual": round(result["deflection"]["delta_amplified_in"], 3),
                "Allowed": round(result["deflection"]["delta_limit_in"], 3),
                "Result": round(result["deflection"]["delta_amplified_in"] / result["deflection"]["delta_limit_in"] * 100, 1) if result["deflection"]["delta_limit_in"] > 0 else 0,
                "LDF": "-",
                "Combo": "Seismic",
            },
        },
        "result": result,
    }


def _segments_from_openings(total_len, openings):
    """Compute segment lengths from opening positions (ordered x, w, h)."""
    sorted_ops = sorted(openings, key=lambda o: o.get("x", 0))
    segments = []
    cursor = 0
    for op in sorted_ops:
        x = op.get("x", 0)
        w = op.get("w", 0)
        if x > cursor:
            segments.append(x - cursor)
        cursor = x + w
    if cursor < total_len:
        segments.append(total_len - cursor)
    return [s for s in segments if s > 0]


# ============================================================
# Test (workbook validation case)
# ============================================================
if __name__ == "__main__":
    inp = ShearWallInputs()
    result = check_shear_wall(inp)

    print("=" * 60)
    print("SHEAR WALL CALCULATOR — Workbook Validation")
    print("=" * 60)

    g = result["governs"]
    s = result["seismic_shear"]
    w = result["wind_shear"]
    ab = result["anchor_bolts"]
    d = result["deflection"]
    c = result["chord"]
    n = result["notes"]

    print(f"\n  Wall type: {inp.wall_type} | {g} governs (Vs={inp.Vs}, Vw={inp.Vw})")
    print(f"  Shear design: {result['shear_design_lbs']} lbs (expect 2815)")
    print(f"  Unit shear v: {result['unit_shear_v_plf']} plf (expect 152.74)")
    print(f"  L_eff: {result['L_eff_ft']} ft")

    print(f"\n  SEISMIC: vs={s['vs_plf']} plf | v_allow={s['v_allow_seismic_plf']} plf | {s['shear_check']}")
    print(f"  AR_max={s['aspect_ratio']} | AR_check={s['ar_check']}")
    print(f"  WIND:    vw={w['vw_plf']} plf | v_allow={w['v_allow_wind_plf']} plf | {w['shear_check']}")

    print(f"\n  ANCHOR BOLTS: {ab['perp_governs']} governs ({ab['V_perp_lbs']} lbs)")
    print(f"  Para: {ab['num_para']} bolts @ {ab['spacing_para_ft']} ft")
    print(f"  Perp: {ab['num_perp']} bolts @ {ab['spacing_perp_ft']} ft")

    print(f"\n  DEFLECTION: max={d['delta_max_in']} in, amplified={d['delta_amplified_in']} in")
    print(f"  Limit={d['delta_limit_in']} in | Drift={d['drift_check']}")
    if d['holdown_error']:
        print(f"  HOLDOWN ERROR: {d['holdown_error']}")

    print(f"\n  CHORD: T={c['T_chord_lbs']} lbs, C={c['C_chord_lbs']} lbs")
    print(f"  Tension:   {c['tension']['check']} (CSI={c['tension']['CSI']})")
    print(f"  Bearing:   {c['bearing']['check']} (CSI={c['bearing']['CSI']})")
    print(f"  Compression: {c['compression']['check']} (CSI={c['compression']['CSI']}, Cp={c['compression']['Cp']})")

    print(f"\n  OVERALL: {result['summary']['overall']}")
    print(f"\n  {n['sheathing_callout'][:100]}...")
