"""
load_combos.py
ASCE 7-22 ASD Load Combinations
"""

def get_load_combinations(D=0, L=0, Lr=0, S=0, W=0):
    """
    Returns a list of evaluated load combinations.
    Each combination is a dict: {'name': str, 'load': float, 'CD': float}
    """
    combos = []
    
    # CD parameters
    CD_D = 0.90
    CD_L = 1.00
    CD_Lr = 1.25
    CD_S = 1.15
    CD_W = 1.60
    
    # 1. 1.0D
    combos.append({'name': '1.0D', 'load': 1.0*D, 'CD': CD_D})
    
    # 2. 1.0D + 1.0L
    combos.append({'name': '1.0D + 1.0L', 'load': 1.0*D + 1.0*L, 'CD': CD_L})
    
    # 3. 1.0D + 1.0Lr
    combos.append({'name': '1.0D + 1.0Lr', 'load': 1.0*D + 1.0*Lr, 'CD': CD_Lr})
    
    # 4. 1.0D + 1.0S
    combos.append({'name': '1.0D + 1.0S', 'load': 1.0*D + 1.0*S, 'CD': CD_S})
    
    # 5. 1.0D + 0.75L + 0.75Lr
    # For combination with L and Lr, the shortest duration applies to the whole combo
    combos.append({'name': '1.0D + 0.75L + 0.75Lr', 'load': 1.0*D + 0.75*L + 0.75*Lr, 'CD': CD_Lr})
    
    # 6. 1.0D + 0.75L + 0.75S
    combos.append({'name': '1.0D + 0.75L + 0.75S', 'load': 1.0*D + 0.75*L + 0.75*S, 'CD': CD_S})
    
    # 7. 1.0D + 0.6W
    combos.append({'name': '1.0D + 0.6W', 'load': 1.0*D + 0.6*W, 'CD': CD_W})
    
    # 8. 1.0D + 0.45W + 0.75L + 0.75Lr
    combos.append({'name': '1.0D + 0.45W + 0.75L + 0.75Lr', 'load': 1.0*D + 0.45*W + 0.75*L + 0.75*Lr, 'CD': CD_W})
    
    # 9. 1.0D + 0.45W + 0.75L + 0.75S
    combos.append({'name': '1.0D + 0.45W + 0.75L + 0.75S', 'load': 1.0*D + 0.45*W + 0.75*L + 0.75*S, 'CD': CD_W})
    
    return combos
