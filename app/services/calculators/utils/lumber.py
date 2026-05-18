"""
lumber.py
Reference values, section properties, and CF lookup for multiple species and grades.
"""

import re

# Section properties for sawn lumber (b, d, A, S, I)
SECTION_PROPS = {
    "2x4": {"b": 1.5, "d": 3.5, "A": 5.25, "S": 3.063, "I": 5.359},
    "2x6": {"b": 1.5, "d": 5.5, "A": 8.25, "S": 7.563, "I": 20.80},
    "2x8": {"b": 1.5, "d": 7.25, "A": 10.875, "S": 13.14, "I": 47.63},
    "2x10": {"b": 1.5, "d": 9.25, "A": 13.875, "S": 21.39, "I": 98.93},
    "2x12": {"b": 1.5, "d": 11.25, "A": 16.875, "S": 31.64, "I": 177.98},
    "4x4": {"b": 3.5, "d": 3.5, "A": 12.25, "S": 7.146, "I": 12.505},
}

# Base reference values (psi) for 2x4 sizes
# ADDED Fc_perp (Fc_p)
REF_VALUES = {
    "DF-L": {
        "Select Structural": {"Fb": 1500, "Fv": 180, "Fc": 1700, "Fc_p": 625, "E": 1900000, "Emin": 690000, "Density": 36.7},
        "No. 1": {"Fb": 1000, "Fv": 180, "Fc": 1500, "Fc_p": 625, "E": 1700000, "Emin": 620000, "Density": 36.7},
        "No. 2": {"Fb": 900, "Fv": 180, "Fc": 1350, "Fc_p": 625, "E": 1600000, "Emin": 580000, "Density": 36.7},
        "Stud": {"Fb": 700, "Fv": 180, "Fc": 850, "Fc_p": 625, "E": 1400000, "Emin": 510000, "Density": 36.7},
    },
    "SP": { 
        "Select Structural": {"Fb": 2400, "Fv": 175, "Fc": 1800, "Fc_p": 565, "E": 1800000, "Emin": 660000, "Density": 37.6},
        "No. 1": {"Fb": 1500, "Fv": 175, "Fc": 1550, "Fc_p": 565, "E": 1600000, "Emin": 580000, "Density": 37.6},
        "No. 2": {"Fb": 1100, "Fv": 175, "Fc": 1450, "Fc_p": 565, "E": 1400000, "Emin": 510000, "Density": 37.6},
        "Stud": {"Fb": 750, "Fv": 175, "Fc": 900, "Fc_p": 565, "E": 1200000, "Emin": 440000, "Density": 37.6},
    },
    "SPF": { 
        "Select Structural": {"Fb": 1250, "Fv": 135, "Fc": 1400, "Fc_p": 425, "E": 1500000, "Emin": 550000, "Density": 29.3},
        "No. 1": {"Fb": 875, "Fv": 135, "Fc": 1150, "Fc_p": 425, "E": 1400000, "Emin": 510000, "Density": 29.3},
        "No. 2": {"Fb": 875, "Fv": 135, "Fc": 1150, "Fc_p": 425, "E": 1400000, "Emin": 510000, "Density": 29.3},
        "Stud": {"Fb": 675, "Fv": 135, "Fc": 725, "Fc_p": 425, "E": 1200000, "Emin": 440000, "Density": 29.3},
    },
    "HF": { 
        "Select Structural": {"Fb": 1300, "Fv": 150, "Fc": 1500, "Fc_p": 405, "E": 1600000, "Emin": 580000, "Density": 29.4},
        "No. 1": {"Fb": 975, "Fv": 150, "Fc": 1350, "Fc_p": 405, "E": 1500000, "Emin": 550000, "Density": 29.4},
        "No. 2": {"Fb": 850, "Fv": 150, "Fc": 1300, "Fc_p": 405, "E": 1300000, "Emin": 470000, "Density": 29.4},
        "Stud": {"Fb": 675, "Fv": 150, "Fc": 850, "Fc_p": 405, "E": 1200000, "Emin": 440000, "Density": 29.4},
    },
    "1.55E LSL": {
        "1.55E": {"Fb": 2325, "Fv": 310, "Fc": 1750, "Fc_p": 675, "E": 1550000, "Emin": 787000, "Density": 45.0}
    },
    "2.0E LVL": {
        "2.0E": {"Fb": 2600, "Fv": 285, "Fc": 2500, "Fc_p": 750, "E": 2000000, "Emin": 1016000, "Density": 42.0}
    }
}

def normalize_species(species: str) -> str:
    s = str(species).lower().strip()
    if s in ["df", "dfl", "df-l", "doug fir"]: return "DF-L"
    if s in ["sp", "southern pine"]: return "SP"
    if s in ["spf", "spruce pine fir"]: return "SPF"
    if s in ["hf", "hem fir", "hem-fir"]: return "HF"
    return species

def normalize_grade(grade: str) -> str:
    g = str(grade).lower().strip()
    if g in ["1", "no1", "no 1", "no. 1", "#1"]: return "No. 1"
    if g in ["2", "no2", "no 2", "no. 2", "#2"]: return "No. 2"
    if g in ["ss", "select", "select structural"]: return "Select Structural"
    if g in ["stud"]: return "Stud"
    if "1.55" in g: return "1.55E"
    if "2.0" in g: return "2.0E"
    return grade

def normalize_member_size(size: str | None, *, strip_plies: bool = False) -> str | None:
    """Normalize extracted member dimensions to calculator-friendly notation.

    Extraction models may return plan-style callouts such as 2" X 10",
    2 in x 10 in, 2-2x10, or (3) 2" x 12". The calculators need the
    cross-section portion in compact form, e.g. 2x10 or 1.75x16. By default
    we preserve a leading ply marker for callers that need it, such as the
    shear wall chord lookup. Section-property lookup passes strip_plies=True.
    """
    if size is None:
        return None
    s = str(size).strip()
    if not s:
        return s
    s = s.replace("×", "x").replace("X", "x")
    s = re.sub(r"(?<=\d)\s*(?:\"|“|”|″)", "", s)
    s = re.sub(r"(?<=\d)\s*(?:inches|inch|in\.?)\b", "", s, flags=re.IGNORECASE)
    s = re.sub(r"\s*x\s*", "x", s)
    s = re.sub(r"\s+", " ", s).strip()
    s = re.sub(r"^\((\d+)\)\s*", r"(\1) ", s)
    s = re.sub(r"^(\d+)\s*-\s*(?=\d+(?:\.\d+)?x)", r"(\1) ", s)
    if strip_plies:
        s = re.sub(r"^\(\d+\)\s*", "", s).strip()
    return s


def _section_size_and_plies(size: str, plies: int) -> tuple[str, int]:
    normalized = normalize_member_size(size) or ""
    effective_plies = int(plies or 1)
    ply_match = re.match(r"^\((\d+)\)\s*(.+)$", normalized)
    if ply_match:
        if effective_plies <= 1:
            effective_plies = int(ply_match.group(1))
        normalized = ply_match.group(2).strip()
    return normalize_member_size(normalized, strip_plies=True) or normalized, effective_plies

def get_CF(size: str, stress_type: str, species: str, grade: str) -> float:
    """Size Factor (CF) per NDS Supplement Tables."""
    size = normalize_member_size(size, strip_plies=True)
    species = normalize_species(species)
    grade = normalize_grade(grade)
    
    if grade == "Stud":
        return 1.0
        
    if species == "SP":
        sp_cf_fb = {"2x4": 1.0, "2x6": 0.90, "2x8": 0.84, "2x10": 0.68, "2x12": 0.65, "4x4": 1.0}
        sp_cf_fc = {"2x4": 1.0, "2x6": 0.95, "2x8": 0.93, "2x10": 0.90, "2x12": 0.86, "4x4": 1.0}
        if stress_type == "Fb": return sp_cf_fb.get(size, 1.0)
        elif stress_type == "Fc": return sp_cf_fc.get(size, 1.0)
        return 1.0
    else:
        cf_fb = {"2x4": 1.5, "2x6": 1.3, "2x8": 1.2, "2x10": 1.1, "2x12": 1.0, "4x4": 1.5}
        cf_fc = {"2x4": 1.15, "2x6": 1.1, "2x8": 1.05, "2x10": 1.0, "2x12": 0.9, "4x4": 1.15}
        if stress_type == "Fb": return cf_fb.get(size, 1.0)
        elif stress_type == "Fc": return cf_fc.get(size, 1.0)
        return 1.0

def get_section_props(size: str, plies: int = 1):
    size, plies = _section_size_and_plies(size, plies)
    try:
        # Check standard dictionary first
        base = SECTION_PROPS[size]
    except KeyError:
        # Dynamic float string parsing for EWP (e.g. '1.75x16')
        s = size.lower().replace(" ", "")
        if "x" in s:
            try:
                b_str, d_str = s.split("x")
                b_float, d_float = float(b_str), float(d_str)
                base = {
                    "b": b_float,
                    "d": d_float,
                    "A": b_float * d_float,
                    "S": (b_float * (d_float**2)) / 6,
                    "I": (b_float * (d_float**3)) / 12
                }
            except Exception:
                raise ValueError(f"Unknown custom size format: {size}. Use e.g. 1.75x16")
        else:
            raise ValueError(f"Size '{size}' not found and not a valid format.")

    return {
        "b": base["b"] * plies,
        "d": base["d"],
        "A": base["A"] * plies,
        "S": base["S"] * plies,
        "I": base["I"] * plies
    }

def get_ref_values(species: str, grade: str):
    species = normalize_species(species)
    grade = normalize_grade(grade)
    if species not in REF_VALUES or grade not in REF_VALUES[species]:
        raise ValueError(f"Material '{species}' grade '{grade}' not found in library.")
    return REF_VALUES[species][grade].copy()
