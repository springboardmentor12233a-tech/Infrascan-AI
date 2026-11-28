"""Crack & defect geometry calculation in pixels (and mm only when calibrated)."""


def compute_box_geometry(
    x1: float,
    y1: float,
    x2: float,
    y2: float,
    img_width: int,
    img_height: int,
    px_per_mm: float | None = None,
) -> dict:
    """
    Compute bounding-box geometry in pixels.
    Only converts to millimetres if a positive px_per_mm calibration factor is provided.
    """
    w_px = max(0.0, x2 - x1)
    h_px = max(0.0, y2 - y1)
    area_px = w_px * h_px
    orientation = "Horizontal" if w_px > h_px * 1.3 else ("Vertical" if h_px > w_px * 1.3 else "Diagonal/Mixed")

    result = {
        "width_px": round(w_px, 1),
        "height_px": round(h_px, 1),
        "area_px": round(area_px, 1),
        "coverage_pct": round((area_px / max(1, img_width * img_height)) * 100.0, 2),
        "orientation": orientation,
        "calibrated": bool(px_per_mm and px_per_mm > 0),
    }

    if px_per_mm and px_per_mm > 0:
        result["width_mm"] = round(w_px / px_per_mm, 2)
        result["height_mm"] = round(h_px / px_per_mm, 2)
        result["area_mm2"] = round(area_px / (px_per_mm ** 2), 2)

    return result

