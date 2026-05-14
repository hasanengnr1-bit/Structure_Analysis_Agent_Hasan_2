"""
stud_calc.py
Wall stud calculations for combined axial + lateral wind, including bearing limits and IBC exceptions.
"""
from services.calculators.utils.adjustments import cp_factor
from services.calculators.utils.lumber import get_section_props, get_ref_values, get_CF


def check_stud(name, system, application, size, species, grade, length_ft, spacing_in, wind_psf, D_plf=0, L_plf=0, Lr_plf=0, S_plf=0, support_species="SPF", unbraced_weak_ft=1.0, ecc_ratio=0.1667):
    props = get_section_props(size, 1)
    refs = get_ref_values(species, grade)
    length_in = length_ft * 12
    
    # Tributary loads
    wind_plf = wind_psf * (spacing_in / 12)
    axial_D = D_plf * (spacing_in / 12)
    axial_L = L_plf * (spacing_in / 12)
    axial_Lr = Lr_plf * (spacing_in / 12)
    axial_S = S_plf * (spacing_in / 12)
    
    # Self-Weight Calculation strictly using Material Density
    density = refs.get("Density", 35.0)
    self_weight_lbs = density * (props["A"] / 144.0) * length_ft
    axial_D += self_weight_lbs
    
    # Slenderness
    # Axis 1 (strong axis, le = length) checks in-plane unbraced length
    le_d1 = length_in / props["d"]
    # Axis 2 (weak axis), stud is fully braced by sheathing typically
    le_d2 = (unbraced_weak_ft * 12) / props["b"] if unbraced_weak_ft > 0 else 0 
    slenderness = max(le_d1, le_d2)
    
    results = {}
    results["Slenderness"] = {"Actual": slenderness, "Allowed": 50, "Result": (slenderness/50)*100, "LDF": "-", "Combo": "-"}
    
    CF_fc = get_CF(size, "Fc", species, grade)
    CF_fb = get_CF(size, "Fb", species, grade)
    CF_fv = get_CF(size, "Fv", species, grade)
    # Studs repetitively spaced unless custom
    Cr = 1.15 if spacing_in <= 24 and spacing_in > 0 else 1.0 
    E_prime = refs["E"]
    Emin_prime = refs["Emin"]
    
    Fce = 0.822 * Emin_prime / (slenderness**2) if slenderness > 0 else float('inf')

    # Plate Bearing Setup
    support_refs = get_ref_values(support_species, "No. 2")
    base_Fc_perp = support_refs.get("Fc_p", 425) 
    # Cb = (lb + 0.375)/lb for bearing length < 6". Stud bearing = width 'b'
    Cb = (props["b"] + 0.375) / props["b"] if props["b"] < 6 else 1.0
    allowed_Fc_perp = base_Fc_perp * Cb
    bearing_area = props["A"] # Stud rests entirely on plate

    # Track maximums
    max_comp_util, res_comp = 0, None
    max_mom_util, res_mom = 0, None
    max_comb_util, res_comb = 0, None
    max_brg_util, res_brg = 0, None
    max_shear_util, res_shear = 0, None
    res_lat_react = None

    # Load Combinations mapped explicitly for axial vs lateral split
    CD_D, CD_L, CD_Lr, CD_S, CD_W = 0.90, 1.00, 1.25, 1.15, 1.60
    c_list = [
        {'name': '1.0D', 'P': 1.0*axial_D, 'W': 0, 'CD': CD_D},
        {'name': '1.0D + 1.0L', 'P': 1.0*axial_D + 1.0*axial_L, 'W': 0, 'CD': CD_L},
        {'name': '1.0D + 1.0Lr', 'P': 1.0*axial_D + 1.0*axial_Lr, 'W': 0, 'CD': CD_Lr},
        {'name': '1.0D + 1.0S', 'P': 1.0*axial_D + 1.0*axial_S, 'W': 0, 'CD': CD_S},
        {'name': '1.0D + 0.75L + 0.75Lr', 'P': 1.0*axial_D + 0.75*axial_L + 0.75*axial_Lr, 'W': 0, 'CD': CD_Lr},
        {'name': '1.0D + 0.75L + 0.75S', 'P': 1.0*axial_D + 0.75*axial_L + 0.75*axial_S, 'W': 0, 'CD': CD_Lr},
        {'name': '1.0D + 0.6W', 'P': 1.0*axial_D, 'W': 0.6*wind_plf, 'CD': CD_W},
        {'name': '1.0D + 0.45W + 0.75L + 0.75Lr', 'P': 1.0*axial_D + 0.75*axial_L + 0.75*axial_Lr, 'W': 0.45*wind_plf, 'CD': CD_W},
        {'name': '1.0D + 0.45W + 0.75L + 0.75S', 'P': 1.0*axial_D + 0.75*axial_L + 0.75*axial_S, 'W': 0.45*wind_plf, 'CD': CD_W}
    ]

    for combo in c_list:
        P = combo["P"]
        W_plf = combo["W"]
        
        # Compression Buckling Capacity
        Fc_star = refs["Fc"] * combo["CD"] * CF_fc
        CP = cp_factor(slenderness, Emin_prime, Fc_star)
        allowed_Fc = Fc_star * CP
        allowed_P = allowed_Fc * props["A"]
        
        util_comp = P / allowed_P if allowed_P > 0 else 0
        if util_comp > max_comp_util:
            max_comp_util = util_comp
            res_comp = {"Actual": P, "Allowed": allowed_P, "Result": util_comp*100, "LDF": combo["CD"], "Combo": combo["name"]}
            
        # Plate Bearing capacity
        allowed_brg = allowed_Fc_perp * bearing_area
        util_brg = P / allowed_brg if allowed_brg > 0 else 0
        if util_brg > max_brg_util:
            max_brg_util = util_brg
            res_brg = {"Actual": P, "Allowed": allowed_brg, "Result": util_brg*100, "LDF": "-", "Combo": combo["name"]}

        # Lateral Shear at stud end (d from support)
        lat_react = (W_plf * length_ft) / 2
        if W_plf > 0:
            act_lat_shear = lat_react - (W_plf * (props["d"]/12.0))
            if act_lat_shear < 0: act_lat_shear = 0
            
            allowed_Fv = refs["Fv"] * combo["CD"] * CF_fv
            allowed_V = allowed_Fv * props["A"] / 1.5
            util_shear = act_lat_shear / allowed_V if allowed_V > 0 else 0
            if util_shear >= max_shear_util:
                max_shear_util = util_shear
                res_shear = {"Actual": act_lat_shear, "Allowed": allowed_V, "Result": util_shear*100, "LDF": combo["CD"], "Combo": combo["name"]}
                res_lat_react = {"Actual": lat_react, "Allowed": allowed_Fc_perp * props["A"], "Result": (lat_react / (allowed_Fc_perp * props["A"])) * 100, "LDF": combo["CD"], "Combo": combo["name"]}

        # Total Bending
        lat_M_ft_lbs = (W_plf * (length_ft**2)) / 8
        ecc_M_ft_lbs = P * (ecc_ratio * props["d"] / 12.0)
        M_ft_lbs = lat_M_ft_lbs + ecc_M_ft_lbs
        
        fb = (M_ft_lbs * 12) / props["S"]
        
        Fb_star = refs["Fb"] * combo["CD"] * CF_fb * Cr 
        allowed_M_ft_lbs = (Fb_star * props["S"]) / 12
        
        util_mom = M_ft_lbs / allowed_M_ft_lbs if allowed_M_ft_lbs > 0 else 0
        if util_mom > max_mom_util:
            max_mom_util = util_mom
            res_mom = {"Actual": M_ft_lbs, "Allowed": allowed_M_ft_lbs, "Result": util_mom*100, "LDF": combo["CD"], "Combo": combo["name"]}
            
        # Combined Bending/Compression (NDS Eq 3.9-3)
        fc = P / props["A"]
        if allowed_Fc > 0 and Fce > fc and Fb_star > 0:
            util_interact = (fc / allowed_Fc)**2 + (fb / (Fb_star * (1.0 - (fc/Fce))))
        else:
            util_interact = 0
            
        if util_interact > max_comb_util:
            max_comb_util = util_interact
            res_comb = {"Actual": util_interact, "Allowed": 1.0, "Result": util_interact*100, "LDF": combo["CD"], "Combo": combo["name"]}
    
    results["Axial Compression (lbs)"] = res_comp
    results["Plate Bearing (lbs)"] = res_brg
    if res_lat_react:
        results["Lateral Reaction (lbs)"] = res_lat_react
        results["Lateral Shear (lbs)"] = res_shear
    results["Lateral Moment (ft-lbs)"] = res_mom
    results["Bending/Compression"] = res_comb
    
    # Total Deflection measured under 42% Load per IBC footnote 'f'
    max_W = wind_plf * 0.42 
    defl = (5 * (max_W/12) * length_in**4) / (384 * E_prime * props["I"]) if max_W > 0 else 0
    allowed_defl = length_in / 360  # Default L/360 for Studs per Wall criteria
    results["Total Deflection (in)"] = {"Actual": defl, "Allowed": allowed_defl, "Result": (defl/allowed_defl)*100, "LDF": "-", "Combo": "1.0 D + 0.6 W"}
    
    return {"name": name, "system": system, "application": application, "size": size, "plies": 1, "results": results}
