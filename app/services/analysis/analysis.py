from typing import Any, Callable

from services.calculators.footing_calc import check_footing
from services.calculators.horizontal_calc import check_horizontal
from services.calculators.post_calc import check_post
from services.calculators.post_footing_calc import check_post_footing
from services.calculators.shear_wall_calc import check_shear_wall
from services.calculators.slab_calc import check_slab
from services.calculators.stud_wall_calc import check_stud
from services.mapping.mapping import MAPPERS


AnalysisRunner = Callable[..., dict[str, Any]]


ANALYSIS_PLAN: tuple[dict[str, Any], ...] = (
    {
        "system_key": "roof_system",
        "collection_key": "roof_rafters",
        "mapper_key": "roof_rafter",
        "runner": check_horizontal,
    },
    {
        "system_key": "roof_system",
        "collection_key": "ceiling_joists",
        "mapper_key": "ceiling_joist",
        "runner": check_horizontal,
    },
    {
        "system_key": "roof_system",
        "collection_key": "ridge_beams",
        "mapper_key": "ridge_beam",
        "runner": check_horizontal,
    },
    {
        "system_key": "roof_system",
        "collection_key": "hip_valley_rafters",
        "mapper_key": "hip_valley_rafter",
        "runner": check_horizontal,
    },
    {
        "system_key": "roof_system",
        "collection_key": "roof_drop_beams",
        "mapper_key": "roof_drop_beam",
        "runner": check_horizontal,
    },
    {
        "system_key": "roof_system",
        "collection_key": "roof_flush_beams",
        "mapper_key": "roof_flush_beam",
        "runner": check_horizontal,
    },
    {
        "system_key": "floor_system",
        "collection_key": "floor_joists",
        "mapper_key": "floor_joist",
        "runner": check_horizontal,
    },
    {
        "system_key": "floor_system",
        "collection_key": "floor_drop_beams",
        "mapper_key": "floor_drop_beam",
        "runner": check_horizontal,
    },
    {
        "system_key": "floor_system",
        "collection_key": "floor_flush_beams",
        "mapper_key": "floor_flush_beam",
        "runner": check_horizontal,
    },
    {
        "system_key": "wall",
        "collection_key": "stud_walls",
        "mapper_key": "stud_wall",
        "runner": check_stud,
    },
    {
        "system_key": "wall",
        "collection_key": "headers",
        "mapper_key": "header",
        "runner": check_horizontal,
    },
    {
        "system_key": "post",
        "collection_key": "standalone_posts",
        "mapper_key": "post",
        "runner": check_post,
    },
    {
        "system_key": "footing",
        "collection_key": "continuous_strip_footings",
        "mapper_key": "continuous_footing",
        "runner": check_footing,
    },
    {
        "system_key": "footing",
        "collection_key": "pad_footings",
        "mapper_key": "pad_footing",
        "runner": check_post_footing,
    },
    {
        "system_key": "footing",
        "collection_key": "slab_on_grade",
        "mapper_key": "slab",
        "runner": check_slab,
    },
    {
        "system_key": "shear_wall",
        "collection_key": "shear_walls",
        "mapper_key": "shear_wall",
        "runner": check_shear_wall,
    },
)


def run_structural_analysis(extracted_data: dict[str, Any]) -> dict[str, Any]:
    env = _build_analysis_env(extracted_data)
    items: list[dict[str, Any]] = []
    systems: dict[str, dict[str, Any]] = {}

    for plan in ANALYSIS_PLAN:
        system_key = plan["system_key"]
        collection_key = plan["collection_key"]
        source_items = _get_collection(extracted_data, system_key, collection_key)

        for index, source_item in enumerate(source_items, start=1):
            item = _run_one_analysis(plan, source_item, env, index)
            items.append(item)
            system_bucket = systems.setdefault(
                system_key,
                {"total": 0, "passing": 0, "failing": 0, "errors": 0, "items": []},
            )
            system_bucket["items"].append(item)
            system_bucket["total"] += 1
            if item["status"] == "PASS":
                system_bucket["passing"] += 1
            elif item["status"] == "ERROR":
                system_bucket["errors"] += 1
            else:
                system_bucket["failing"] += 1

    summary = {
        "total_items": len(items),
        "passing": sum(1 for item in items if item["status"] == "PASS"),
        "failing": sum(1 for item in items if item["status"] == "FAIL"),
        "errors": sum(1 for item in items if item["status"] == "ERROR"),
        "overall": "PASS",
    }
    if summary["errors"]:
        summary["overall"] = "ERROR"
    elif summary["failing"]:
        summary["overall"] = "FAIL"

    return {
        "summary": summary,
        "systems": systems,
        "items": items,
    }


def _run_one_analysis(
    plan: dict[str, Any],
    source_item: dict[str, Any],
    env: dict[str, Any],
    index: int,
) -> dict[str, Any]:
    system_key = plan["system_key"]
    collection_key = plan["collection_key"]
    mapper_key = plan["mapper_key"]
    label = _label_for_item(source_item, mapper_key, index)

    try:
        mapper = MAPPERS[mapper_key]
        kwargs = mapper(source_item, env)
        raw = plan["runner"](**kwargs)
        normalized = _normalize_result(
            raw,
            source_system=system_key,
            source_collection=collection_key,
            source_type=mapper_key,
            label=label,
            index=index,
        )
        return normalized
    except Exception as exc:
        return {
            "id": f"{mapper_key}-{index}",
            "source_system": system_key,
            "source_collection": collection_key,
            "source_type": mapper_key,
            "label": label,
            "system": _display_system(system_key),
            "application": mapper_key.replace("_", " ").title(),
            "size": _first_string(source_item, ("size", "stud_size", "header_size", "post_size")),
            "status": "ERROR",
            "max_utilization": None,
            "checks": [],
            "error": str(exc),
            "raw": None,
        }


def _normalize_result(
    raw: dict[str, Any],
    *,
    source_system: str,
    source_collection: str,
    source_type: str,
    label: str,
    index: int,
) -> dict[str, Any]:
    checks = _extract_checks(raw)
    status = _status_from_raw(raw, checks)
    max_utilization = _max_utilization(checks)

    return {
        "id": f"{source_type}-{index}",
        "source_system": source_system,
        "source_collection": source_collection,
        "source_type": source_type,
        "label": raw.get("name") or label,
        "system": raw.get("system") or _display_system(source_system),
        "application": raw.get("application") or source_type.replace("_", " ").title(),
        "size": raw.get("size"),
        "plies": raw.get("plies"),
        "status": status,
        "max_utilization": max_utilization,
        "checks": checks,
        "error": None,
        "raw": raw,
    }


def _extract_checks(raw: dict[str, Any]) -> list[dict[str, Any]]:
    if isinstance(raw.get("results"), dict):
        checks = []
        for check_name, check in raw["results"].items():
            if not isinstance(check, dict):
                continue
            utilization = _to_float(check.get("Result"))
            checks.append(
                {
                    "name": check_name,
                    "actual": check.get("Actual"),
                    "allowed": check.get("Allowed"),
                    "utilization": utilization,
                    "combo": check.get("Combo"),
                    "ldf": check.get("LDF"),
                    "status": "FAIL" if utilization is not None and utilization > 100 else "PASS",
                }
            )
        return checks

    checks = []
    for key, value in raw.items():
        if not isinstance(value, dict):
            continue
        status = value.get("status") or value.get("check")
        utilization = _to_float(value.get("utilization"))
        csi = _to_float(value.get("CSI"))
        if utilization is None and csi is not None:
            utilization = csi * 100
        if status or utilization is not None:
            checks.append(
                {
                    "name": key.replace("_", " ").title(),
                    "actual": _first_existing(value, ("Actual", "Vu_lb", "q_max_psf", "provided_in", "T_chord_lbs")),
                    "allowed": _first_existing(value, ("Allowed", "phi_Vc_lb", "net_bc_psf", "min_required_in", "Ft_adj_psi")),
                    "utilization": utilization,
                    "combo": value.get("Combo"),
                    "ldf": value.get("LDF"),
                    "status": _normalize_status(status, utilization),
                }
            )
    return checks


def _status_from_raw(raw: dict[str, Any], checks: list[dict[str, Any]]) -> str:
    summary = raw.get("summary")
    if isinstance(summary, dict):
        overall = summary.get("overall")
        if isinstance(overall, str):
            if overall.upper() in {"PASS", "OK"}:
                return "PASS"
            if overall.upper() in {"FAIL", "NG"}:
                return "FAIL"

    if any(check["status"] == "FAIL" for check in checks):
        return "FAIL"
    return "PASS"


def _normalize_status(status: Any, utilization: float | None = None) -> str:
    if isinstance(status, str):
        upper = status.upper()
        if upper in {"PASS", "OK"}:
            return "PASS"
        if upper in {"FAIL", "NG"}:
            return "FAIL"
    if isinstance(status, bool):
        return "PASS" if status else "FAIL"
    if utilization is not None and utilization > 100:
        return "FAIL"
    return "PASS"


def _max_utilization(checks: list[dict[str, Any]]) -> float | None:
    utilizations = [
        check["utilization"]
        for check in checks
        if isinstance(check.get("utilization"), (int, float))
    ]
    if not utilizations:
        return None
    return round(max(utilizations), 2)


def _build_analysis_env(extracted_data: dict[str, Any]) -> dict[str, Any]:
    footing = extracted_data.get("footing") or {}
    footing_info = footing.get("project_info") if isinstance(footing, dict) else {}
    hazard = extracted_data.get("hazard_lookup_result") or {}
    seismic = hazard.get("seismic") if isinstance(hazard, dict) else {}
    return {
        "footing_project_info": footing_info or {},
        "SDS": _to_float((seismic or {}).get("sds")) or 0.5,
        "Vs_lbs": _to_float(extracted_data.get("Vs_lbs")) or 0,
        "Vw_lbs": _to_float(extracted_data.get("Vw_lbs")) or 0,
    }


def _get_collection(
    extracted_data: dict[str, Any],
    system_key: str,
    collection_key: str,
) -> list[dict[str, Any]]:
    system = extracted_data.get(system_key) or {}
    if not isinstance(system, dict):
        return []
    collection = system.get(collection_key) or []
    return collection if isinstance(collection, list) else []


def _label_for_item(item: dict[str, Any], source_type: str, index: int) -> str:
    return (
        _first_string(
            item,
            (
                "zone",
                "post_mark",
                "footing_mark",
                "sw_mark",
                "bwl_id",
                "opening_mark",
                "location_description",
            ),
        )
        or f"{source_type.replace('_', ' ').title()} {index}"
    )


def _display_system(system_key: str) -> str:
    return {
        "roof_system": "Roof",
        "floor_system": "Floor",
        "wall": "Wall",
        "post": "Post",
        "footing": "Foundation",
        "shear_wall": "Lateral",
    }.get(system_key, system_key.replace("_", " ").title())


def _first_string(item: dict[str, Any], keys: tuple[str, ...]) -> str | None:
    for key in keys:
        value = item.get(key)
        if value not in (None, ""):
            return str(value)
    return None


def _first_existing(item: dict[str, Any], keys: tuple[str, ...]) -> Any:
    for key in keys:
        if key in item and item[key] not in (None, ""):
            return item[key]
    return None


def _to_float(value: Any) -> float | None:
    try:
        if value is None or value == "":
            return None
        return float(value)
    except (TypeError, ValueError):
        return None
