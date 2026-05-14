from dataclasses import dataclass, field
from typing import Any, Dict, Optional, Literal, List

@dataclass
class PostFootingInputs:
    # Footing dimensions
    B1: float = 2.5               # ft  — shorter width
    B2: float = 3.0               # ft  — longer width
    H: float = 12.0               # in  — thickness
    cover: float = 3.0            # in  — concrete cover
    depth: float = 3.0            # ft  — depth below grade

    # Column
    a1: float = 6.0               # in  — column width in B1 direction
    a2: float = 6.0               # in  — column width in B2 direction
    bar_no_col: str = "#4"

    # Material
    fc: float = 3000.0            # psi
    fy: float = 60000.0           # psi
    gamma_conc: float = 150.0     # pcf
    gamma_soil: float = 120.0     # pcf

    # Loading
    DL: float = 10_000.0          # lb
    LL: float = 5_000.0           # lb
    Mu_ftkips: float = 0.0        # ft-kips

    # Soil
    q_allow_ton: float = 2.0      # ton/ft^2  (2000 psf)
    surcharge_ft: float = 0.0     # ft of soil surcharge

    # Reinforcement: bar size (if None, auto-sized)
    bar_B1: Optional[str] = None  # bar size in B1 direction
    bar_B2: Optional[str] = None  # bar size in B2 direction
    bar_spacing_B1: Optional[float] = None  # provided spacing B1 (in)
    bar_spacing_B2: Optional[float] = None  # provided spacing B2 (in)

    # Location (for punching shear alpha_s)
    column_location: Literal["interior", "edge", "corner"] = "interior"


@dataclass
class SlabInputs:
    # Dimensions
    thickness_in: float = 4.0           # slab thickness (in)
    length_ft: float = 20.0             # longest dimension
    width_ft: float = 15.0              # shorter dimension

    # Reinforcement
    reinforcement_type: str = "wwf"     # "rebar", "wwf", "fiber", "none"
    rebar_size: Optional[str] = "#4"
    rebar_spacing_in: float = 18.0
    wwf_designation: Optional[str] = "6x6-W2.9xW2.9"
    fiber_type: Optional[str] = "macro_synthetic"

    # Sub-grade
    sub_base_type: str = "gravel"       # "gravel", "sand", "native"
    sub_base_depth_in: float = 4.0

    # Vapor barrier / moisture
    vapor_barrier_mils: int = 10
    interior_slab: bool = True

    # Loading
    residential_use: bool = True        # True = light residential, False = garage/light commercial
    point_load_lbs: float = 2000        # worst point load (furniture, etc.)

    # Exposure / environment
    exposure_class: str = "interior_dry"  # "interior_dry", "exterior", "freeze_thaw"
    sulfate_exposure: str = "S0"         # "S0", "S1", "S2", "S3"

    # Concrete
    fc_psi: float = 3000.0
    concrete_cover_in: float = 0.0       # top cover (0 for interior, 1.5 for exterior)

    # Options
    monolithic_with_footing: bool = False
    control_joint_spacing_ft: Optional[float] = None  # None = auto-compute
    thickened_edge: bool = False
    thickened_edge_width_in: float = 12.0
    thickened_edge_depth_in: float = 12.0


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
    stud_spacing: int = 16 

# ---------------------------------------------------------------- helpers
def _normalize_grade(g: str | None) -> str:
    """Schema grades ('No.1','SS','Stud') -> engine grades ('No. 1','SS','Stud')."""
    if not g:
        return "No. 2"
    g = g.strip()
    table = {"No.1": "No. 1", "No.2": "No. 2", "No.3": "No. 3"}
    return table.get(g, g)


def _lumber(item: Dict[str, Any], default_species="DF-L", default_grade="No. 2"):
    spec = item.get("lumber_spec") or {}
    species = spec.get("species") or default_species
    grade = _normalize_grade(spec.get("grade")) or default_grade
    return species, grade


def _support_species(item: Dict[str, Any]) -> str:
    """Map support_material enum to a species the engine knows for bearing checks."""
    sm = item.get("support_material")
    wood = {"DF-L", "SP", "SPF", "HF"}
    if sm in wood:
        return sm
    return "SPF"


def _wind_psf(env: Dict[str, Any]) -> float:
    """Wind pressure in psf. To be wired to wind analysis calculator once built."""
    return 0.0


def _parse_l_over_n(s: str | None) -> float | None:
    """'L/240' -> 240. Returns None if unparseable."""
    if not s:
        return None
    try:
        if "/" in s:
            return float(s.split("/")[1])
        return float(s)
    except Exception:
        return None


def _parse_pitch(pitch_str: str | None) -> float:
    """'6/12' or '4:12' -> rise value (6.0 or 4.0). Returns 0.0 if unparseable."""
    if not pitch_str:
        return 0.0
    try:
        if "/" in pitch_str:
            return float(pitch_str.split("/")[0])
        elif ":" in pitch_str:
            return float(pitch_str.split(":")[0])
        else:
            return float(pitch_str)
    except Exception:
        return 0.0


def _ewp(item: Dict[str, Any]):
    """Extract EWP species override and property overrides from schema item."""
    ewp = item.get("ewp_spec") or {}
    species_override = ewp.get("product_type")
    overrides = {
        k: ewp.get(k) for k in
        ("Fb_psi", "Fv_psi", "Fc_perp_psi", "E_psi", "E_min_psi")
        if ewp.get(k) is not None
    } or None
    return species_override, overrides


def _defl(item: Dict[str, Any]):
    """Extract deflection criteria denominators from schema item."""
    dc = item.get("deflection_criteria") or {}
    return (
        _parse_l_over_n(dc.get("live_load_limit")),
        _parse_l_over_n(dc.get("total_load_limit")),
    )


def _bearing(item: Dict[str, Any]):
    """Extract bearing lengths (default + optional left/right split)."""
    brg_default = float(item.get("available_support_bearing_in") or 3.5)
    brg_left = item.get("available_support_bearing_left_in")
    brg_right = item.get("available_support_bearing_right_in")
    brg_R1 = float(brg_left) if brg_left not in (None, "") else None
    brg_R2 = float(brg_right) if brg_right not in (None, "") else None
    return brg_default, brg_R1, brg_R2


def _footing_info(env: Dict[str, Any]):
    """Pull FootingProjectInfo fields from env."""
    fi = env.get("footing_project_info") or {}
    q_allow = float(fi.get("soil_bearing_pressure_psf") or 2000)
    fc_ftg = float(fi.get("concrete_fc_footings_psi") or 2500)
    fc_slab = float(fi.get("concrete_fc_slab_psi") or 2500)
    return q_allow, fc_ftg, fc_slab


# ================================================================
#  WALL  —  stud_calc.check_stud
# ================================================================
def map_stud_wall(item: Dict[str, Any], env: Dict[str, Any]) -> Dict[str, Any]:
    """schema.StudWall -> stud_calc.check_stud kwargs"""
    species, grade = _lumber(item)
    spacing = float(item.get("spacing_in") or 16)
    trib_w = float(item.get("tributary_width_ft") or 0)
    wall_dl_psf = float(item.get("wall_dead_load_psf") or 0)
    axial_lbs = float(item.get("axial_load_lbs") or 0)

    wall_len = float(item.get("wall_length_ft") or 0) or 1.0
    axial_dl_plf = (axial_lbs / wall_len) if axial_lbs else 0.0
    if trib_w and wall_dl_psf:
        axial_dl_plf += trib_w * wall_dl_psf

    return dict(
        name=item.get("zone") or "Stud",
        system="Wall",
        application="Stud",
        size=item.get("stud_size") or "2x6",
        species=species,
        grade=grade,
        length_ft=float(item.get("stud_height_ft") or 10),
        spacing_in=spacing,
        wind_psf=_wind_psf(env),
        D_plf=axial_dl_plf,
        L_plf=0.0,
        Lr_plf=0.0,
        S_plf=0.0,
        support_species=_support_species(item),
        unbraced_weak_ft=1.0,
        ecc_ratio=0.1667,
    )


# ================================================================
#  ROOF  —  horizontal_calc.check_horizontal
# ================================================================
def map_roof_rafter(item: Dict[str, Any], env: Dict[str, Any]) -> Dict[str, Any]:
    """schema.RoofRafter -> horizontal_calc.check_horizontal kwargs"""
    species, grade = _lumber(item)
    pitch = _parse_pitch(item.get("roof_pitch"))
    spacing = float(item.get("spacing_in") or 16)
    overhang_ft = float(item.get("overhang_in") or 0) / 12.0
    brg_default, brg_R1, brg_R2 = _bearing(item)
    sc = item.get("service_conditions") or None
    defl_LL, defl_TL = _defl(item)
    ewp_species, ewp_overrides = _ewp(item)
    if ewp_species:
        species = ewp_species

    return dict(
        name=item.get("zone") or "Rafter",
        system="Roof",
        application="Joist",
        size=item.get("size") or "2x10",
        species=species,
        grade=grade,
        plies=int(item.get("number_of_plies") or 1),
        clear_span_ft=float(item.get("clear_span_ft") or 12),
        spacing_in=spacing,
        trib_width_ft=spacing / 12.0,
        D_psf=float(item.get("roof_dead_load_psf") or 15),
        L_psf=0.0,
        Lr_psf=float(item.get("roof_live_load_psf") or 20),
        S_psf=float(item.get("roof_snow_load_psf") or 0),
        support_species=_support_species(item),
        bearing_area_length_in=brg_default,
        L_ol_ft=overhang_ft,
        L_or_ft=0.0,
        pitch=pitch,
        defl_LL_denom=defl_LL,
        defl_TL_denom=defl_TL,
        service_conditions=sc,
        ewp_overrides=ewp_overrides,
        bearing_R1_in=brg_R1,
        bearing_R2_in=brg_R2,
    )


def map_ceiling_joist(item: Dict[str, Any], env: Dict[str, Any]) -> Dict[str, Any]:
    """schema.CeilingJoist -> horizontal_calc.check_horizontal kwargs"""
    species, grade = _lumber(item)
    spacing = float(item.get("spacing_in") or 16)
    brg_default, brg_R1, brg_R2 = _bearing(item)
    sc = item.get("service_conditions") or None
    defl_LL, defl_TL = _defl(item)

    return dict(
        name=item.get("zone") or "Ceiling Joist",
        system="Ceiling",
        application="Joist",
        size=item.get("size") or "2x6",
        species=species,
        grade=grade,
        plies=int(item.get("number_of_plies") or 1),
        clear_span_ft=float(item.get("clear_span_ft") or 12),
        spacing_in=spacing,
        trib_width_ft=spacing / 12.0,
        D_psf=float(item.get("ceiling_dead_load_psf") or 5),
        L_psf=float(item.get("attic_live_load_psf") or 10),
        Lr_psf=0.0,
        S_psf=0.0,
        support_species=_support_species(item),
        bearing_area_length_in=brg_default,
        L_ol_ft=0.0,
        L_or_ft=0.0,
        pitch=0.0,
        defl_LL_denom=defl_LL,
        defl_TL_denom=defl_TL,
        service_conditions=sc,
        ewp_overrides=None,
        bearing_R1_in=brg_R1,
        bearing_R2_in=brg_R2,
    )


def map_ridge_beam(item: Dict[str, Any], env: Dict[str, Any]) -> Dict[str, Any]:
    """schema.RidgeBeam -> horizontal_calc.check_horizontal kwargs"""
    species, grade = _lumber(item)
    ewp_species, ewp_overrides = _ewp(item)
    if ewp_species:
        species = ewp_species
    brg_default, brg_R1, brg_R2 = _bearing(item)
    sc = item.get("service_conditions") or None
    defl_LL, defl_TL = _defl(item)
    trib = float(item.get("tributary_width_ft") or 6)

    return dict(
        name=item.get("zone") or "Ridge Beam",
        system="Roof",
        application="Beam",
        size=item.get("size") or "4x8",
        species=species,
        grade=grade,
        plies=int(item.get("number_of_plies") or 1),
        clear_span_ft=float(item.get("clear_span_ft") or 12),
        spacing_in=0,
        trib_width_ft=trib,
        D_psf=float(item.get("roof_dead_load_psf") or 15),
        L_psf=0.0,
        Lr_psf=float(item.get("roof_live_load_psf") or 20),
        S_psf=float(item.get("roof_snow_load_psf") or 0),
        support_species=_support_species(item),
        bearing_area_length_in=brg_default,
        L_ol_ft=0.0,
        L_or_ft=0.0,
        pitch=0.0,
        defl_LL_denom=defl_LL,
        defl_TL_denom=defl_TL,
        service_conditions=sc,
        ewp_overrides=ewp_overrides,
        bearing_R1_in=brg_R1,
        bearing_R2_in=brg_R2,
    )


def map_hip_valley_rafter(item: Dict[str, Any], env: Dict[str, Any]) -> Dict[str, Any]:
    """schema.HipValleyRafter -> horizontal_calc.check_horizontal kwargs"""
    species, grade = _lumber(item)
    ewp_species, ewp_overrides = _ewp(item)
    if ewp_species:
        species = ewp_species
    pitch = _parse_pitch(item.get("roof_pitch"))
    brg_default, brg_R1, brg_R2 = _bearing(item)
    sc = item.get("service_conditions") or None
    defl_LL, defl_TL = _defl(item)
    trib = float(item.get("tributary_width_ft") or 6)
    member_type = item.get("member_type") or "hip"

    return dict(
        name=item.get("zone") or f"{member_type.title()} Rafter",
        system="Roof",
        application="Beam",
        size=item.get("size") or "2x10",
        species=species,
        grade=grade,
        plies=int(item.get("number_of_plies") or 1),
        clear_span_ft=float(item.get("clear_span_ft") or 12),
        spacing_in=0,
        trib_width_ft=trib,
        D_psf=float(item.get("roof_dead_load_psf") or 15),
        L_psf=0.0,
        Lr_psf=float(item.get("roof_live_load_psf") or 20),
        S_psf=float(item.get("roof_snow_load_psf") or 0),
        support_species=_support_species(item),
        bearing_area_length_in=brg_default,
        L_ol_ft=0.0,
        L_or_ft=0.0,
        pitch=pitch,
        defl_LL_denom=defl_LL,
        defl_TL_denom=defl_TL,
        service_conditions=sc,
        ewp_overrides=ewp_overrides,
        bearing_R1_in=brg_R1,
        bearing_R2_in=brg_R2,
    )


def map_roof_drop_beam(item: Dict[str, Any], env: Dict[str, Any]) -> Dict[str, Any]:
    """schema.RoofDropBeam -> horizontal_calc.check_horizontal kwargs"""
    species, grade = _lumber(item)
    ewp_species, ewp_overrides = _ewp(item)
    if ewp_species:
        species = ewp_species
    pitch = _parse_pitch(item.get("roof_pitch"))
    brg_default, brg_R1, brg_R2 = _bearing(item)
    sc = item.get("service_conditions") or None
    defl_LL, defl_TL = _defl(item)
    trib = float(item.get("tributary_width_ft") or 6)

    return dict(
        name=item.get("zone") or "Roof Drop Beam",
        system="Roof",
        application="Beam",
        size=item.get("size") or "4x8",
        species=species,
        grade=grade,
        plies=int(item.get("number_of_plies") or 1),
        clear_span_ft=float(item.get("clear_span_ft") or 12),
        spacing_in=0,
        trib_width_ft=trib,
        D_psf=float(item.get("roof_dead_load_psf") or 15),
        L_psf=0.0,
        Lr_psf=float(item.get("roof_live_load_psf") or 20),
        S_psf=float(item.get("roof_snow_load_psf") or 0),
        support_species=_support_species(item),
        bearing_area_length_in=brg_default,
        L_ol_ft=0.0,
        L_or_ft=0.0,
        pitch=pitch,
        defl_LL_denom=defl_LL,
        defl_TL_denom=defl_TL,
        service_conditions=sc,
        ewp_overrides=ewp_overrides,
        bearing_R1_in=brg_R1,
        bearing_R2_in=brg_R2,
    )


def map_roof_flush_beam(item: Dict[str, Any], env: Dict[str, Any]) -> Dict[str, Any]:
    """schema.RoofFlushBeam -> horizontal_calc.check_horizontal kwargs"""
    species, grade = _lumber(item)
    ewp_species, ewp_overrides = _ewp(item)
    if ewp_species:
        species = ewp_species
    brg_default, brg_R1, brg_R2 = _bearing(item)
    sc = item.get("service_conditions") or None
    defl_LL, defl_TL = _defl(item)
    trib = float(item.get("tributary_width_ft") or 6)

    return dict(
        name=item.get("zone") or "Roof Flush Beam",
        system="Roof",
        application="Beam",
        size=item.get("size") or "4x8",
        species=species,
        grade=grade,
        plies=int(item.get("number_of_plies") or 1),
        clear_span_ft=float(item.get("clear_span_ft") or 12),
        spacing_in=0,
        trib_width_ft=trib,
        D_psf=float(item.get("roof_dead_load_psf") or 15),
        L_psf=0.0,
        Lr_psf=float(item.get("roof_live_load_psf") or 20),
        S_psf=float(item.get("roof_snow_load_psf") or 0),
        support_species=_support_species(item),
        bearing_area_length_in=brg_default,
        L_ol_ft=0.0,
        L_or_ft=0.0,
        pitch=0.0,
        defl_LL_denom=defl_LL,
        defl_TL_denom=defl_TL,
        service_conditions=sc,
        ewp_overrides=ewp_overrides,
        bearing_R1_in=brg_R1,
        bearing_R2_in=brg_R2,
    )


# ================================================================
#  FLOOR  —  horizontal_calc.check_horizontal
# ================================================================
def map_floor_joist(item: Dict[str, Any], env: Dict[str, Any]) -> Dict[str, Any]:
    """schema.FloorJoist -> horizontal_calc.check_horizontal kwargs"""
    species, grade = _lumber(item)
    ewp_species, ewp_overrides = _ewp(item)
    if ewp_species:
        species = ewp_species
    spacing = float(item.get("spacing_in") or 16)
    brg_default, brg_R1, brg_R2 = _bearing(item)
    sc = item.get("service_conditions") or None
    defl_LL, defl_TL = _defl(item)
    cantilever = float(item.get("cantilever_ft") or 0)

    return dict(
        name=item.get("zone") or "Floor Joist",
        system="Floor",
        application="Joist",
        size=item.get("size") or "2x10",
        species=species,
        grade=grade,
        plies=int(item.get("number_of_plies") or 1),
        clear_span_ft=float(item.get("clear_span_ft") or 12),
        spacing_in=spacing,
        trib_width_ft=spacing / 12.0,
        D_psf=float(item.get("dead_load_psf") or 10),
        L_psf=float(item.get("floor_live_load_psf") or 40),
        Lr_psf=0.0,
        S_psf=0.0,
        support_species=_support_species(item),
        bearing_area_length_in=brg_default,
        L_ol_ft=cantilever,
        L_or_ft=0.0,
        pitch=0.0,
        defl_LL_denom=defl_LL,
        defl_TL_denom=defl_TL,
        service_conditions=sc,
        ewp_overrides=ewp_overrides,
        bearing_R1_in=brg_R1,
        bearing_R2_in=brg_R2,
    )


def map_floor_drop_beam(item: Dict[str, Any], env: Dict[str, Any]) -> Dict[str, Any]:
    """schema.FloorDropBeam -> horizontal_calc.check_horizontal kwargs"""
    species, grade = _lumber(item)
    ewp_species, ewp_overrides = _ewp(item)
    if ewp_species:
        species = ewp_species
    brg_default, brg_R1, brg_R2 = _bearing(item)
    sc = item.get("service_conditions") or None
    defl_LL, defl_TL = _defl(item)
    trib = float(item.get("tributary_width_ft") or 6)

    return dict(
        name=item.get("zone") or "Floor Drop Beam",
        system="Floor",
        application="Beam",
        size=item.get("size") or "4x8",
        species=species,
        grade=grade,
        plies=int(item.get("number_of_plies") or 1),
        clear_span_ft=float(item.get("clear_span_ft") or 12),
        spacing_in=0,
        trib_width_ft=trib,
        D_psf=float(item.get("dead_load_psf") or 10),
        L_psf=float(item.get("floor_live_load_psf") or 40),
        Lr_psf=0.0,
        S_psf=0.0,
        support_species=_support_species(item),
        bearing_area_length_in=brg_default,
        L_ol_ft=0.0,
        L_or_ft=0.0,
        pitch=0.0,
        defl_LL_denom=defl_LL,
        defl_TL_denom=defl_TL,
        service_conditions=sc,
        ewp_overrides=ewp_overrides,
        bearing_R1_in=brg_R1,
        bearing_R2_in=brg_R2,
    )


def map_floor_flush_beam(item: Dict[str, Any], env: Dict[str, Any]) -> Dict[str, Any]:
    """schema.FloorFlushBeam -> horizontal_calc.check_horizontal kwargs"""
    species, grade = _lumber(item)
    ewp_species, ewp_overrides = _ewp(item)
    if ewp_species:
        species = ewp_species
    brg_default, brg_R1, brg_R2 = _bearing(item)
    sc = item.get("service_conditions") or None
    defl_LL, defl_TL = _defl(item)
    trib = float(item.get("tributary_width_ft") or 6)

    return dict(
        name=item.get("zone") or "Floor Flush Beam",
        system="Floor",
        application="Beam",
        size=item.get("size") or "4x8",
        species=species,
        grade=grade,
        plies=int(item.get("number_of_plies") or 1),
        clear_span_ft=float(item.get("clear_span_ft") or 12),
        spacing_in=0,
        trib_width_ft=trib,
        D_psf=float(item.get("dead_load_psf") or 10),
        L_psf=float(item.get("floor_live_load_psf") or 40),
        Lr_psf=0.0,
        S_psf=0.0,
        support_species=_support_species(item),
        bearing_area_length_in=brg_default,
        L_ol_ft=0.0,
        L_or_ft=0.0,
        pitch=0.0,
        defl_LL_denom=defl_LL,
        defl_TL_denom=defl_TL,
        service_conditions=sc,
        ewp_overrides=ewp_overrides,
        bearing_R1_in=brg_R1,
        bearing_R2_in=brg_R2,
    )


# ================================================================
#  HEADER  —  horizontal_calc.check_horizontal
# ================================================================
def map_header(item: Dict[str, Any], env: Dict[str, Any]) -> Dict[str, Any]:
    """schema.Header -> horizontal_calc.check_horizontal kwargs"""
    species, grade = _lumber(item)
    ewp_species, ewp_overrides = _ewp(item)
    if ewp_species:
        species = ewp_species
    sc = item.get("service_conditions") or None
    defl_LL, defl_TL = _defl(item)

    brg = float(item.get("available_bearing_in") or 3.5)
    trib = float(item.get("tributary_width_ft") or 2)
    span = float(item.get("header_clear_span_ft") or 4)

    D_psf = 0.0
    L_psf = float(item.get("floor_live_load_psf") or 0)
    Lr_psf = float(item.get("roof_load_on_header_psf") or 0)

    # Distribute point load as equivalent uniform dead load over the span
    point_load = float(item.get("point_load_lbs") or 0)
    if point_load and span > 0 and trib > 0:
        D_psf += (point_load / span) / trib

    return dict(
        name=item.get("zone") or item.get("opening_mark") or "Header",
        system="Wall",
        application="Header",
        size=item.get("header_size") or "4x12",
        species=species,
        grade=grade,
        plies=int(item.get("number_of_plies") or 2),
        clear_span_ft=span,
        spacing_in=0,
        trib_width_ft=trib,
        D_psf=D_psf,
        L_psf=L_psf,
        Lr_psf=Lr_psf,
        S_psf=0.0,
        support_species=_support_species(item),
        bearing_area_length_in=brg,
        L_ol_ft=0.0,
        L_or_ft=0.0,
        pitch=0.0,
        defl_LL_denom=defl_LL,
        defl_TL_denom=defl_TL,
        service_conditions=sc,
        ewp_overrides=ewp_overrides,
        bearing_R1_in=None,
        bearing_R2_in=None,
    )


# ================================================================
#  POST  —  post_calc.check_post
# ================================================================
def map_post(item: Dict[str, Any], env: Dict[str, Any]) -> Dict[str, Any]:
    """schema.StandalonePost -> post_calc.check_post kwargs"""
    sp = item.get("species") or "DF-L"
    gr = _normalize_grade(item.get("grade")) or "No. 2"

    trib = float(item.get("tributary_area_sf") or 0)
    point = float(item.get("point_load_lbs") or 0)

    roof_dl = float(item.get("roof_dead_load_psf") or 0)
    roof_ll = float(item.get("roof_live_load_psf") or 0)
    roof_sl = float(item.get("roof_snow_load_psf") or 0)
    floor_dl = float(item.get("floor_dead_load_psf") or 0)
    floor_ll = float(item.get("floor_live_load_psf") or 0)

    D_lbs = (roof_dl + floor_dl) * trib + point
    L_lbs = floor_ll * trib
    Lr_lbs = roof_ll * trib
    S_lbs = roof_sl * trib

    return dict(
        name=item.get("post_mark") or "Post",
        system="Post",
        application="Column",
        size=item.get("post_size") or "4x4",
        species=sp,
        grade=gr,
        length_ft=float(item.get("height_ft") or 8),
        D_lbs=D_lbs,
        L_lbs=L_lbs,
        Lr_lbs=Lr_lbs,
        S_lbs=S_lbs,
        support_species=_support_species(item),
        lat_wind_psf=0.0,
        lat_trib_ft=0.0,
        ecc_ratio=0.1667,
    )


# ================================================================
#  CONTINUOUS STRIP FOOTING  —  footing_calc.check_footing
# ================================================================
def map_continuous_footing(item: Dict[str, Any], env: Dict[str, Any]) -> Dict[str, Any]:
    """schema.ContinuousStripFooting -> footing_calc.check_footing kwargs"""
    width_in = float(item.get("width_in") or 12)
    depth_in = float(item.get("depth_in") or 8)

    rebar_num = item.get("transverse_rebar_size")
    rebar_size = f"#{rebar_num}" if rebar_num and not str(rebar_num).startswith("#") else (str(rebar_num or "#4"))
    rebar_spacing = float(item.get("transverse_rebar_spacing_in") or 12)
    cover = float(item.get("concrete_cover_in") or 3.0)

    q_allow, fc_ftg, _ = _footing_info(env)

    # Axial loads from load takedown — provided via env or item overrides
    axial_D = float(item.get("axial_D_kips") or env.get("axial_D_kips", 0) or 2.0)
    axial_L = float(item.get("axial_L_kips") or env.get("axial_L_kips", 0) or 1.0)
    axial_S = float(item.get("axial_S_kips") or env.get("axial_S_kips", 0) or 0)

    return dict(
        name=item.get("footing_mark") or "Strip Footing",
        footing_type="continuous",
        size_x_ft=width_in / 12.0,
        size_y_ft=1.0,
        thickness_in=depth_in,
        axial_D_kips=axial_D,
        axial_L_kips=axial_L,
        axial_S_kips=axial_S,
        q_allow_psf=q_allow,
        f_prime_c=fc_ftg,
        rebar_size=rebar_size,
        rebar_spacing_in=rebar_spacing,
        cover_in=cover,
    )


# ================================================================
#  PAD FOOTING  —  post_footing_calc.check_post_footing
# ================================================================
def map_pad_footing(item: Dict[str, Any], env: Dict[str, Any]) -> Dict[str, Any]:
    """schema.PadFooting -> post_footing_calc.check_post_footing kwargs"""

    width_in = float(item.get("width_in") or 24)
    length_in = float(item.get("length_in") or 24)
    depth_in = float(item.get("depth_in") or 12)
    cover = float(item.get("concrete_cover_in") or 3.0)

    post_size = item.get("post_size") or "4x4"
    try:
        parts = post_size.lower().replace("x", " ").split()
        a1 = float(parts[0]) - 0.5
        a2 = float(parts[1]) - 0.5 if len(parts) > 1 else a1
    except Exception:
        a1 = a2 = 3.5

    q_allow, fc_ftg, _ = _footing_info(env)

    rebar_raw = item.get("rebar_size")
    rebar_str = f"#{rebar_raw}" if rebar_raw and not str(rebar_raw).startswith("#") else (str(rebar_raw or "#4"))
    rebar_spacing = float(item.get("rebar_spacing_in") or 12)

    DL = float(item.get("axial_DL_lbs") or env.get("axial_DL_lbs", 0) or 5000)
    LL = float(item.get("axial_LL_lbs") or env.get("axial_LL_lbs", 0) or 3000)

    inp = PostFootingInputs(
        B1=width_in / 12.0,
        B2=length_in / 12.0,
        H=depth_in,
        cover=cover,
        a1=a1,
        a2=a2,
        fc=fc_ftg,
        q_allow_ton=q_allow / 2000.0,
        DL=DL,
        LL=LL,
        bar_B1=rebar_str,
        bar_B2=rebar_str,
        bar_spacing_B1=rebar_spacing,
        bar_spacing_B2=rebar_spacing,
    )
    return dict(inp=inp)


# ================================================================
#  SLAB ON GRADE  —  slab_calc.check_slab
# ================================================================
def map_slab(item: Dict[str, Any], env: Dict[str, Any]) -> Dict[str, Any]:
    """schema.SlabOnGrade -> slab_calc.check_slab kwargs"""
    
    thickness = float(item.get("thickness_in") or 4.0)
    reinf_type = item.get("reinforcement_type") or "wwf"

    rebar_raw = item.get("rebar_size")
    rebar_str = f"#{rebar_raw}" if rebar_raw and not str(rebar_raw).startswith("#") else (str(rebar_raw or "#4"))
    rebar_spacing = float(item.get("rebar_spacing_in") or 18)
    wwf = item.get("wwf_designation") or "6x6-W2.9xW2.9"

    sub_desc = (item.get("sub_base_description") or "").lower()
    if "sand" in sub_desc:
        sub_base = "sand"
    elif "native" in sub_desc:
        sub_base = "native"
    else:
        sub_base = "gravel"

    sub_depth = float(item.get("sub_base_depth_in") or 4)
    vapor = int(item.get("vapor_barrier_mils") or 10)
    mono = bool(item.get("monolithic_with_footing"))

    _, _, fc_slab = _footing_info(env)

    inp = SlabInputs(
        thickness_in=thickness,
        reinforcement_type=reinf_type,
        rebar_size=rebar_str,
        rebar_spacing_in=rebar_spacing,
        wwf_designation=wwf,
        sub_base_type=sub_base,
        sub_base_depth_in=sub_depth,
        vapor_barrier_mils=vapor,
        fc_psi=fc_slab,
        monolithic_with_footing=mono,
    )
    return dict(inp=inp)


# ================================================================
#  SHEAR WALL  —  shear_wall_calc.check_shear_wall
# ================================================================
def map_shear_wall(item: Dict[str, Any], env: Dict[str, Any]) -> Dict[str, Any]:
    """schema.ShearWall -> shear_wall_calc.check_shear_wall kwargs

    Lateral demands (Vs, Vw) and seismic parameters (SDS) are expected in env
    from the lateral load analysis — they are not part of the per-wall schema.
    """
    
    wall_height = float(item.get("wall_height_ft") or 8)
    pier_length = float(item.get("pier_length_ft") or 4)

    # Sheathing thickness: schema stores float (0.4375), engine wants string ("7/16")
    thickness_raw = item.get("sheathing_thickness_in")
    _thickness_map = {0.4375: "7/16", 0.46875: "15/32"}
    if isinstance(thickness_raw, (int, float)):
        panel_thickness = _thickness_map.get(float(thickness_raw), "15/32")
    else:
        panel_thickness = str(thickness_raw or "15/32")

    faces = (item.get("sheathing_faces") or "one_side").lower()
    both_sides = "two" in faces

    edge_nail = int(item.get("edge_nail_spacing_in") or 6)
    nail_size = item.get("nail_size") or "10d"
    fastener = "10d" if "10" in nail_size else "8d"

    hd_model = item.get("holdown_model") or "HDU2"
    stud_size = item.get("stud_size") or "2x6"
    stud_spacing = int(item.get("stud_spacing_in") or 16)

    Vs = float(env.get("Vs_lbs", 0))
    Vw = float(env.get("Vw_lbs", 0))
    sds = float(env.get("SDS", 0.5))

    inp = ShearWallInputs(
        Vs=Vs,
        Vw=Vw,
        wall_length_total=pier_length,
        wall_height=wall_height,
        nail_edge_spacing=edge_nail,
        sheathing_both_sides=both_sides,
        panel_thickness=panel_thickness,
        fastener_type=fastener,
        holdown_model=hd_model,
        chord_studs=f"(2) {stud_size}",
        sill_plate_type="(1)-2x",
        stud_spacing=stud_spacing,
        SDS=sds,
        panels=[pier_length],
        sum_Li=pier_length,
        bs_perf=pier_length,
    )
    return dict(inp=inp)


# ================================================================
#  Registry — extend when new engines come online
# ================================================================
MAPPERS = {
    # Wall
    "stud_wall":            map_stud_wall,
    # Roof
    "roof_rafter":          map_roof_rafter,
    "ceiling_joist":        map_ceiling_joist,
    "ridge_beam":           map_ridge_beam,
    "hip_valley_rafter":    map_hip_valley_rafter,
    "roof_drop_beam":       map_roof_drop_beam,
    "roof_flush_beam":      map_roof_flush_beam,
    # Floor
    "floor_joist":          map_floor_joist,
    "floor_drop_beam":      map_floor_drop_beam,
    "floor_flush_beam":     map_floor_flush_beam,
    # Header
    "header":               map_header,
    # Post
    "post":                 map_post,
    # Foundations
    "continuous_footing":   map_continuous_footing,
    "pad_footing":          map_pad_footing,
    "slab":                 map_slab,
    # Lateral
    "shear_wall":           map_shear_wall,
}