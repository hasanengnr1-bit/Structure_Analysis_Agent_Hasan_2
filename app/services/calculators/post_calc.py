"""
post_calc.py
Pure axial column calculations including slenderness, combined loading, and plate bearing limits.
"""
from services.calculators.utils.adjustments import cp_factor
from services.calculators.utils.lumber import get_section_props, get_ref_values, get_CF

def check_post(name, system, application, size, species, grade, length_ft, D_lbs=0, L_lbs=0, Lr_lbs=0, S_lbs=0, support_species="SPF", lat_wind_psf=0, lat_trib_ft=0, ecc_ratio=0.1667):
    props = get_section_props(size, 1) # single sawn post
    refs = get_ref_values(species, grade)
    length_in = length_ft * 12
    
    # Self-Weight Calculation
    density = refs.get("Density", 35.0)
    self_weight_lbs = density * (props["A"] / 144.0) * length_ft
    D_lbs += self_weight_lbs
    
    # Slenderness
    le_d1 = length_in / props["d"]
    le_d2 = length_in / props["b"]
    slenderness = max(le_d1, le_d2)
    
    CF_fc = get_CF(size, "Fc", species, grade)
    CF_fb = get_CF(size, "Fb", species, grade)
    CF_fv = get_CF(size, "Fv", species, grade)
    Emin_prime = refs["Emin"]
    
    # Support Plate Bearing Setup
    support_refs = get_ref_values(support_species, "No. 2")
    allowed_Fc_perp = support_refs.get("Fc_p", 425) 
    bearing_area = props["A"]
    
    results = {}
    results["Slenderness"] = {"Actual": slenderness, "Allowed": 50, "Result": (slenderness/50)*100, "LDF": "-", "Combo": "-"}
    
    # Track maximums
    max_comp_util, res_comp = 0, None
    max_brg_util, res_brg = 0, None
    max_shear_util, res_shear = 0, None
    max_interact_util, res_interact = 0, None
    
    # For reporting lateral moment explicitly
    max_lat_moment_util, res_lat_moment = 0, None
    res_lat_react = None
    
    CD_D, CD_L, CD_Lr, CD_S, CD_W = 0.90, 1.00, 1.25, 1.15, 1.60
    c_list = [
        {'name': '1.0D', 'P': 1.0*D_lbs, 'CD': CD_D, 'w_fact': 0},
        {'name': '1.0D + 1.0L', 'P': 1.0*D_lbs + 1.0*L_lbs, 'CD': CD_L, 'w_fact': 0},
        {'name': '1.0D + 1.0Lr', 'P': 1.0*D_lbs + 1.0*Lr_lbs, 'CD': CD_Lr, 'w_fact': 0},
        {'name': '1.0D + 1.0S', 'P': 1.0*D_lbs + 1.0*S_lbs, 'CD': CD_S, 'w_fact': 0},
        {'name': '1.0D + 0.75L + 0.75Lr', 'P': 1.0*D_lbs + 0.75*L_lbs + 0.75*Lr_lbs, 'CD': CD_Lr, 'w_fact': 0},
        {'name': '1.0D + 0.75L + 0.75S', 'P': 1.0*D_lbs + 0.75*L_lbs + 0.75*S_lbs, 'CD': CD_Lr, 'w_fact': 0},
        {'name': '1.0D + 0.6W', 'P': 1.0*D_lbs, 'CD': CD_W, 'w_fact': 0.6}
    ]

    w_wind_plf = lat_wind_psf * lat_trib_ft

    for combo in c_list:
        P = combo["P"]
        W_multi = combo["w_fact"]
        
        # Buckling
        Fc_star = refs["Fc"] * combo["CD"] * CF_fc
        CP = cp_factor(slenderness, Emin_prime, Fc_star)
        allowed_Fc = Fc_star * CP
        allowed_P = allowed_Fc * props["A"]
        
        util_comp = P / allowed_P if allowed_P > 0 else 0
        if util_comp > max_comp_util:
            max_comp_util = util_comp
            res_comp = {"Actual": P, "Allowed": allowed_P, "Result": util_comp*100, "LDF": combo["CD"], "Combo": combo["name"]}
            
        # Plate Bearing
        allowed_brg = allowed_Fc_perp * bearing_area
        util_brg = P / allowed_brg if allowed_brg > 0 else 0
        if util_brg > max_brg_util:
            max_brg_util = util_brg
            res_brg = {"Actual": P, "Allowed": allowed_brg, "Result": util_brg*100, "LDF": "-", "Combo": combo["name"]}
            
        # Lateral Shear & Moment
        wind_plf_factored = w_wind_plf * W_multi
        lat_react = (wind_plf_factored * length_ft) / 2
        lat_M_ft_lbs = (wind_plf_factored * (length_ft**2)) / 8
        ecc_M_ft_lbs = P * (ecc_ratio * props["d"] / 12.0)
        total_M_ft_lbs = lat_M_ft_lbs + ecc_M_ft_lbs
        
        if W_multi > 0:
            act_lat_shear = lat_react - (wind_plf_factored * (props["d"]/12.0))
            if act_lat_shear < 0: act_lat_shear = 0
            
            allowed_Fv = refs["Fv"] * combo["CD"] * CF_fv
            allowed_V = allowed_Fv * props["A"] / 1.5
            util_shear = act_lat_shear / allowed_V if allowed_V > 0 else 0
            if util_shear >= max_shear_util:
                max_shear_util = util_shear
                res_shear = {"Actual": act_lat_shear, "Allowed": allowed_V, "Result": util_shear*100, "LDF": combo["CD"], "Combo": combo["name"]}
                res_lat_react = {"Actual": lat_react, "Allowed": allowed_Fc_perp * bearing_area, "Result": (lat_react / (allowed_Fc_perp * bearing_area)) * 100, "LDF": combo["CD"], "Combo": combo["name"]}
                
        # NDS Eq 3.9-3 Interaction
        fc = P / props["A"]
        FcE = (0.822 * Emin_prime) / (slenderness**2)
        
        fb = (total_M_ft_lbs * 12) / props["S"]
        Fb_star = refs["Fb"] * combo["CD"] * CF_fb
        
        if allowed_Fc > 0 and FcE > fc and Fb_star > 0:
            util_interact = (fc / allowed_Fc)**2 + (fb / (Fb_star * (1.0 - (fc/FcE))))
        else:
            util_interact = 0
            
        if util_interact > max_interact_util:
            max_interact_util = util_interact
            res_interact = {"Actual": util_interact, "Allowed": 1.0, "Result": util_interact*100, "LDF": combo["CD"], "Combo": combo["name"]}
        
        # Track raw Moment
        allowed_M_ft_lbs = (Fb_star * props["S"]) / 12
        util_M = total_M_ft_lbs / allowed_M_ft_lbs if allowed_M_ft_lbs > 0 else 0
        if util_M > max_lat_moment_util:
            max_lat_moment_util = util_M
            res_lat_moment = {"Actual": total_M_ft_lbs, "Allowed": allowed_M_ft_lbs, "Result": util_M*100, "LDF": combo["CD"], "Combo": combo["name"]}

    results["Axial Compression (lbs)"] = res_comp
    results["Plate Bearing (lbs)"] = res_brg
    if res_lat_react:
        results["Lateral Reaction (lbs)"] = res_lat_react
        results["Lateral Shear (lbs)"] = res_shear
    if res_lat_moment:
        results["Lateral Moment (ft-lbs)"] = res_lat_moment
    if res_interact:
        results["Bending/Compression"] = res_interact

    return {"name": name, "system": system, "application": application, "size": size, "plies": 1, "results": results}
