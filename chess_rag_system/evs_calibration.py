"""Simple EVS calibration to align scores with tier thresholds."""

# Calibration anchors from baseline analysis
EVS_RAW_P50 = 73.3  # Current median
EVS_RAW_P90 = 98.6  # Current 90th percentile
EVS_TARGET_P50 = 82.0  # Target median
EVS_TARGET_P90 = 92.0  # Target 90th percentile

def calibrate_evs(raw_score: float) -> float:
    """Apply monotonic affine transformation to EVS scores.

    Maps median (73.3) to 82 and p90 (98.6) to 92.
    Preserves relative ordering of all scores.
    """
    # Calculate affine transformation: new = a * old + b
    # Using two points: (73.3, 82) and (98.6, 92)
    a = (EVS_TARGET_P90 - EVS_TARGET_P50) / (EVS_RAW_P90 - EVS_RAW_P50)
    b = EVS_TARGET_P50 - a * EVS_RAW_P50

    calibrated = a * raw_score + b

    # Clamp to valid range [0, 100]
    return max(0.0, min(100.0, calibrated))