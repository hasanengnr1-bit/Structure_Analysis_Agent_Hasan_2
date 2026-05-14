"""
footing_calc.py
Analysis and design of concrete footings (Isolated Post and Continuous Wall).
Includes ASD soil bearing and LRFD concrete/rebar checks.
"""

## Continuous_strip footing

import math
from services.calculators.utils.rebar_data import get_rebar_area, get_rebar_diam

def check_footing(name, footing_type, size_x_ft, size_y_ft, thickness_in, axial_D_kips, axial_L_kips=0, axial_S_kips=0, q_allow_psf=2000, f_prime_c=3000, rebar_size="#4", rebar_spacing_in=12, cover_in=3.0):
    """
    Check structural integrity of a concrete footing.
    - Isolated: size_x x size_y footing.
    - Continuous: size_y is 1'-0" strip length.
    """
    # 1. Inputs & Geometry
    D = axial_D_kips * 1000
    L = axial_L_kips * 1000
    S = axial_S_kips * 1000
    fy = 60000 # Grade 60 Rebar
    
    # Footing Area
    if footing_type.lower() == "continuous":
        area_sqft = size_x_ft * 1.0
        width_in = size_x_ft * 12
        length_in = 12.0
    else:
        area_sqft = size_x_ft * size_y_ft
        width_in = size_x_ft * 12
        length_in = size_y_ft * 12

    # Concrete Weight (approx 150 pcf)
    self_weight = (area_sqft * (thickness_in / 12.0)) * 150.0
    
    # 2. ASD Soil Bearing Check
    total_load_asd = D + L + S + self_weight
    q_applied = total_load_asd / area_sqft if area_sqft > 0 else 0
    
    res_soil = {
        "Actual": round(q_applied, 1),
        "Allowed": q_allow_psf,
        "Result": (q_applied / q_allow_psf) * 100,
        "LDF": "-",
        "Combo": "D+L+S+Self"
    }

    # 3. Factored Loads (LRFD) for Concrete Design
    # Using simple 1.2D + 1.6L + 0.5S common combo
    Pu = (1.2 * D) + (1.6 * L) + (0.5 * S)
    qu = Pu / area_sqft if area_sqft > 0 else 0 # Factored Soil Pressure (Net)
    
    # 4. Geometry for Shear/Flexure
    # Effective depth d
    db = get_rebar_diam(rebar_size)
    d = thickness_in - cover_in - (db / 2.0)
    if d <= 0: d = 1.0 # Minimum sanity
    
    # Assume post/wall size (standard min 4x4 post or 6" wall if not specified)
    # We can add these as inputs later, but for now use defaults
    bp = 5.5 # 6x6 post approx width
    wp = 6.0 # Wall width
    
    results = {}
    results["Soil Bearing (psf)"] = res_soil

    # 5. One-Way Shear
    # Distance from face to edge
    if footing_type.lower() == "continuous":
        proj = (width_in - wp) / 2.0
    else:
        # For square isolated footings, assume square post in center
        proj = (width_in - bp) / 2.0
        
    critical_v1 = proj - d
    if critical_v1 < 0: critical_v1 = 0
    
    Vu1 = (qu/144.0) * (critical_v1 * length_in)
    # Phi Vc = 0.75 * 2 * sqrt(f'c) * b * d
    phi = 0.75
    Vc1 = phi * 2 * math.sqrt(f_prime_c) * length_in * d
    
    results["One-way Shear (lbs)"] = {
        "Actual": round(Vu1, 1),
        "Allowed": round(Vc1, 1),
        "Result": (Vu1 / Vc1) * 100 if Vc1 > 0 else 0,
        "LDF": "-",
        "Combo": "1.2D+1.6L"
    }

    # 6. Two-Way (Punching) Shear (Isolated only)
    if footing_type.lower() != "continuous":
        # Critical perimeter bo
        bo = 4 * (bp + d)
        Area_punch = (bp + d)**2
        Vu2 = qu * (area_sqft - (Area_punch/144.0))
        
        # Phi Vc = 0.75 * 4 * sqrt(f'c) * bo * d
        Vc2 = phi * 4 * math.sqrt(f_prime_c) * bo * d
        
        results["Punching Shear (lbs)"] = {
            "Actual": round(Vu2, 1),
            "Allowed": round(Vc2, 1),
            "Result": (Vu2 / Vc2) * 100 if Vc2 > 0 else 0,
            "LDF": "-",
            "Combo": "1.2D+1.6L"
        }

    # 7. Flexure / Rebar Design
    # Moment at face of support
    Mu = (qu/144.0) * (proj**2 / 2.0) * length_in # in-lbs
    
    # As provided
    As_provided = (get_rebar_area(rebar_size) * (12.0 / rebar_spacing_in)) * (length_in / 12.0)
    
    # Capacity Mn
    # a = As * fy / (0.85 * f'c * b)
    a = (As_provided * fy) / (0.85 * f_prime_c * length_in)
    phi_f = 0.9
    Mn = As_provided * fy * (d - a/2.0)
    phiMn = phi_f * Mn
    
    # Min As check (ACI 10.5.1 approx or T&S)
    As_min = 0.0018 * length_in * thickness_in
    
    results["Flexural Capacity (in-lbs)"] = {
        "Actual": round(Mu, 1),
        "Allowed": round(phiMn, 1),
        "Result": (Mu / phiMn) * 100 if phiMn > 0 else 0,
        "LDF": "-",
        "Combo": "1.2D+1.6L"
    }
    
    if As_provided < As_min:
        results["Flexural Capacity (in-lbs)"]["Actual"] = f"{round(Mu, 1)} (As_provided={round(As_provided, 2)} < As_min={round(As_min, 2)} in2)"

    return {
        "name": name, 
        "system": "Foundation", 
        "application": f"{footing_type} Footing", 
        "size": f"{size_x_ft}x{size_y_ft}x{thickness_in}in", 
        "results": results,
        "plies": 1 # To match report format
    }
