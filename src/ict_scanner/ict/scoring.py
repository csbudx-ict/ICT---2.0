def calculate_confluence_score(
    htf_aligned: bool,
    pool_type: str,
    displacement_atr: float,
    pd_aligned: bool,
    in_ote: bool,
    has_ob: bool,
    in_killzone: bool,
    rr2: float
) -> float:
    score = 0.0
    
    if htf_aligned:
        score += 20
        
    if pool_type in ["PDH", "PDL", "EQH", "EQL"]:
        score += 15 # Major pool
    elif pool_type == "SWING":
        score += 10 # Minor pool
        
    if displacement_atr >= 1.5:
        score += 15
        
    if pd_aligned:
        score += 10
        
    if in_ote:
        score += 10
        
    if has_ob:
        score += 10
        
    if in_killzone:
        score += 10
        
    if rr2 >= 3.0:
        score += 5
        
    score += 5 # Assume clear target for this automated part
    
    return min(100.0, score)
