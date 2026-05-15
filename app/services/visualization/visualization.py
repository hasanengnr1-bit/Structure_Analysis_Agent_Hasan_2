from typing import Any


def _dump(value: Any) -> Any:
    if hasattr(value, "model_dump"):
        return value.model_dump()
    return value


def _items(data: dict[str, Any], key: str) -> list[dict[str, Any]]:
    value = data.get(key) or []
    return value if isinstance(value, list) else []


def _append(
    overlays: list[dict[str, Any]],
    *,
    item_type: str,
    system: str,
    label: str,
    level: str | None = None,
    size: str | None = None,
    location_description: str | None = None,
    span_ft: float | None = None,
    spacing_in: float | None = None,
    note: str = "",
) -> None:
    overlays.append(
        {
            "item_type": item_type,
            "system": system,
            "label": label,
            "level": level,
            "size": size,
            "location_description": location_description,
            "span_ft": span_ft,
            "spacing_in": spacing_in,
            "note": note,
        }
    )


def _add_roof(overlays: list[dict[str, Any]], roof: dict[str, Any]) -> None:
    for item in _items(roof, "roof_rafters"):
        _append(
            overlays,
            item_type="rafter_run",
            system="roof",
            label=item.get("zone") or "Roof rafters",
            size=item.get("size"),
            location_description=item.get("zone"),
            span_ft=item.get("clear_span_ft"),
            spacing_in=item.get("spacing_in"),
            note=item.get("clear_span_note") or "",
        )

    for key, item_type in (
        ("ridge_beams", "ridge_beam"),
        ("hip_valley_rafters", "hip_valley_rafter"),
        ("roof_drop_beams", "roof_drop_beam"),
        ("roof_flush_beams", "roof_flush_beam"),
        ("ceiling_joists", "ceiling_joist_run"),
    ):
        for item in _items(roof, key):
            _append(
                overlays,
                item_type=item_type,
                system="roof",
                label=item.get("zone") or item_type.replace("_", " ").title(),
                size=item.get("size"),
                location_description=item.get("zone"),
                span_ft=item.get("clear_span_ft"),
                spacing_in=item.get("spacing_in"),
                note=item.get("clear_span_note") or item.get("tributary_width_note") or "",
            )


def _add_floor(overlays: list[dict[str, Any]], floor: dict[str, Any]) -> None:
    for item in _items(floor, "floor_joists"):
        _append(
            overlays,
            item_type="floor_joist_run",
            system="floor",
            label=item.get("zone") or "Floor joists",
            size=item.get("size"),
            location_description=item.get("zone"),
            span_ft=item.get("clear_span_ft"),
            spacing_in=item.get("spacing_in"),
            note=item.get("clear_span_note") or "",
        )

    for key, item_type in (
        ("floor_drop_beams", "floor_drop_beam"),
        ("floor_flush_beams", "floor_flush_beam"),
    ):
        for item in _items(floor, key):
            _append(
                overlays,
                item_type=item_type,
                system="floor",
                label=item.get("zone") or item_type.replace("_", " ").title(),
                size=item.get("size"),
                location_description=item.get("zone"),
                span_ft=item.get("clear_span_ft"),
                note=item.get("clear_span_note") or item.get("tributary_width_note") or "",
            )


def _add_walls(overlays: list[dict[str, Any]], wall: dict[str, Any]) -> None:
    for item in _items(wall, "stud_walls"):
        _append(
            overlays,
            item_type="stud_wall",
            system="wall",
            label=item.get("zone") or "Stud wall",
            size=item.get("stud_size"),
            location_description=item.get("zone"),
            span_ft=item.get("wall_length_ft"),
            spacing_in=item.get("spacing_in"),
            note=item.get("wall_length_note") or item.get("stud_note") or "",
        )

    for item in _items(wall, "headers"):
        _append(
            overlays,
            item_type="header",
            system="wall",
            label=item.get("opening_mark") or item.get("zone") or "Header",
            size=item.get("header_size"),
            location_description=item.get("zone"),
            span_ft=item.get("header_clear_span_ft"),
            note=item.get("rough_opening_note") or item.get("header_note") or "",
        )


def _add_foundation(overlays: list[dict[str, Any]], footing: dict[str, Any]) -> None:
    for item in _items(footing, "continuous_strip_footings"):
        _append(
            overlays,
            item_type="continuous_footing",
            system="foundation",
            label=item.get("footing_mark") or "Strip footing",
            location_description=item.get("location_description"),
            span_ft=item.get("length_ft"),
            note=item.get("width_note") or item.get("footing_note") or "",
        )

    for item in _items(footing, "pad_footings"):
        _append(
            overlays,
            item_type="pad_footing",
            system="foundation",
            label=item.get("footing_mark") or "Pad footing",
            size=_format_rect(item.get("width_in"), item.get("length_in"), "in"),
            location_description=item.get("location_description"),
            note=item.get("dimension_note") or item.get("footing_note") or "",
        )


def _add_posts(overlays: list[dict[str, Any]], post: dict[str, Any]) -> None:
    for item in _items(post, "standalone_posts"):
        _append(
            overlays,
            item_type="post",
            system="post",
            label=item.get("post_mark") or "Post",
            size=item.get("post_size"),
            location_description=item.get("location_description"),
            span_ft=item.get("height_ft"),
            note=item.get("height_note") or item.get("post_note") or "",
        )


def _add_shear(overlays: list[dict[str, Any]], shear: dict[str, Any]) -> None:
    for item in _items(shear, "braced_wall_lines"):
        _append(
            overlays,
            item_type="braced_wall_line",
            system="lateral",
            label=item.get("bwl_id") or "Braced wall line",
            level=item.get("story_level"),
            span_ft=item.get("bwl_total_length_ft"),
            note=item.get("bwl_note") or "",
        )

    for item in _items(shear, "shear_walls"):
        _append(
            overlays,
            item_type="shear_wall",
            system="lateral",
            label=item.get("sw_mark") or "Shear wall",
            level=item.get("story_level"),
            size=item.get("stud_size"),
            location_description=item.get("bwl_id"),
            span_ft=item.get("pier_length_ft"),
            spacing_in=item.get("stud_spacing_in"),
            note=item.get("sw_note") or "",
        )


def _format_rect(width: Any, length: Any, unit: str) -> str | None:
    if width is None and length is None:
        return None
    if width is None:
        return f"? x {length} {unit}"
    if length is None:
        return f"{width} x ? {unit}"
    return f"{width} x {length} {unit}"


def build_visualization_payload(
    extracted_data: dict[str, Any],
    context: Any = None,
) -> dict[str, Any]:
    """
    Build the visualizer payload mostly from already extracted schemas.

    The optional context is the small drawing-only LLM extraction containing
    footprint, elevation, ridge, and roof-plane geometry.
    """
    data = _dump(extracted_data) or {}
    context_data = _dump(context)
    overlays: list[dict[str, Any]] = []
    source_systems: list[str] = []

    if data.get("roof_system"):
        source_systems.append("roof_system")
        _add_roof(overlays, data["roof_system"])
    if data.get("floor_system"):
        source_systems.append("floor_system")
        _add_floor(overlays, data["floor_system"])
    if data.get("wall"):
        source_systems.append("wall")
        _add_walls(overlays, data["wall"])
    if data.get("footing"):
        source_systems.append("footing")
        _add_foundation(overlays, data["footing"])
    if data.get("post"):
        source_systems.append("post")
        _add_posts(overlays, data["post"])
    if data.get("shear_wall"):
        source_systems.append("shear_wall")
        _add_shear(overlays, data["shear_wall"])

    return {
        "context": context_data,
        "overlays": overlays,
        "source_systems": source_systems,
        "visualizer_note": (
            "Overlays are derived from existing extraction schemas. Context "
            "contains only drawing geometry needed for visual comparison."
        ),
    }
