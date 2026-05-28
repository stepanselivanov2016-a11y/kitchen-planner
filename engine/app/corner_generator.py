from itertools import permutations, product

from app.kitchen_constants import *
from app.kitchen_options import *
from app.length_optimizer import *
from app.lower_modules import *
from app.wall_modules import (
    apply_wall_facade_grouping,
    build_wall_modules,
    get_hood_width_for_hob,
    place_upper_built_in_microwave,
)


CORNER_MODULE_WIDTH_MM = 600
CORNER_FALSE_PANEL_WIDTH_MM = 50


def _copy_for_straight_generation(module_options: dict, total_length_mm: int) -> dict:
    options = copy_module_options(module_options)
    room = options.setdefault("room", {})
    room["layout_shape"] = "straight"
    room["wall_length_mm"] = total_length_mm

    return options


def _clean_corner_source_module(module: dict) -> dict:
    copied = {**module}

    for key in (
        "x_mm",
        "side_x_mm",
        "side",
        "countertop_role",
        "countertop_free_mm",
        "countertop_occupied_by",
        "countertop_occupied_x_mm",
        "countertop_occupied_width_mm",
    ):
        copied.pop(key, None)

    return copied


def _is_tall_like_module(module: dict) -> bool:
    return module.get("type") in {"tall", "appliance_tall", "freestanding_solo", "profile_handle"}


def _is_full_height_end_module(module: dict) -> bool:
    return module.get("type") in {"tall", "appliance_tall", "freestanding_solo"} or module.get("name") in {
        "built_in_fridge",
        "freestanding_fridge_in_carcass",
        "freestanding_fridge_solo",
        "corner_tall",
    }


def _is_fridge_module(module: dict) -> bool:
    return module.get("name") in {
        "built_in_fridge",
        "freestanding_fridge_in_carcass",
        "freestanding_fridge_solo",
    }


def _is_profile_handle_module(module: dict) -> bool:
    return module.get("type") == "profile_handle"


def _effective_corner_microwave_type(straight_layout: dict, requested_type: str) -> str:
    module_names = {
        module.get("name")
        for module in straight_layout.get("modules", [])
    }

    if module_names & {"oven_microwave_column", "microwave_column"}:
        return "none"

    if straight_layout.get("upper_microwave_placement"):
        return "upper_built_in"

    if straight_layout.get("solo_microwave_placement"):
        return "solo"

    return requested_type


def _order_external_tall_modules(
    modules: list[dict],
    *,
    corner_at_start: bool,
) -> list[dict]:
    if not modules:
        return []

    profiles = [module for module in modules if _is_profile_handle_module(module)]
    columns = [module for module in modules if not _is_profile_handle_module(module)]

    if len(columns) <= 1:
        return list(modules)

    fridges = [module for module in columns if _is_fridge_module(module)]
    other_columns = [module for module in columns if not _is_fridge_module(module)]
    ordered_columns = (
        other_columns + fridges
        if corner_at_start
        else fridges + other_columns
    )

    result = []
    profile_index = 0

    for index, module in enumerate(ordered_columns):
        result.append(module)

        if index >= len(ordered_columns) - 1:
            continue

        if profile_index < len(profiles):
            result.append(profiles[profile_index])
            profile_index += 1

    result.extend(profiles[profile_index:])

    return result


def _group_corner_source_modules(modules: list[dict]) -> dict[str, list[dict]]:
    groups = {
        "sink": [],
        "cooking": [],
        "tall": [],
        "other": [],
    }

    for module in modules:
        clean = _clean_corner_source_module(module)

        if module.get("name") == "sink" or module.get("name", "").startswith("dishwasher_"):
            groups["sink"].append(clean)
        elif module.get("supports_hob") or module.get("countertop_occupied_by") == "hob":
            groups["cooking"].append(clean)
        elif _is_tall_like_module(module):
            groups["tall"].append(clean)
        else:
            groups["other"].append(clean)

    return groups


def _modules_width(modules: list[dict]) -> int:
    return sum(module.get("width_mm", 0) for module in modules)


def _assign_x_to_side_modules(
    modules: list[dict],
    *,
    side: str,
    start_x: int,
    base_module_height_mm: int,
    kitchen_height_mm: int,
) -> list[dict]:
    x_mm = start_x
    result = []

    for module in modules:
        copied = {**module}
        copied["x_mm"] = x_mm
        copied["side_x_mm"] = x_mm
        copied["side"] = side
        mark_countertop_role(copied)

        if copied["type"] == "base":
            copied["height_mm"] = base_module_height_mm
        elif copied["type"] in {"tall", "appliance_tall"}:
            copied["height_mm"] = kitchen_height_mm
        elif copied["type"] == "profile_handle":
            copied["height_mm"] = kitchen_height_mm - PLINTH_HEIGHT_MM

        result.append(copied)
        x_mm += copied["width_mm"]

    return result


def _split_corner_side_modules(
    modules: list[dict],
    *,
    corner_at_start: bool,
) -> tuple[list[dict], list[dict]]:
    if not modules:
        return [], []

    if corner_at_start:
        split_index = len(modules)

        while split_index > 0 and _is_tall_like_module(modules[split_index - 1]):
            split_index -= 1

        return modules[:split_index], modules[split_index:]

    split_index = 0

    while split_index < len(modules) and _is_tall_like_module(modules[split_index]):
        split_index += 1

    return modules[split_index:], modules[:split_index]


def _assign_corner_side_modules(
    modules: list[dict],
    *,
    side: str,
    side_width_mm: int,
    corner_at_start: bool,
    base_module_height_mm: int,
    kitchen_height_mm: int,
) -> list[dict]:
    middle_modules, external_tall_modules = _split_corner_side_modules(
        modules,
        corner_at_start=corner_at_start,
    )
    result = []

    if corner_at_start:
        result.extend(
            _assign_x_to_side_modules(
                middle_modules,
                side=side,
                start_x=CORNER_MODULE_WIDTH_MM + CORNER_FALSE_PANEL_WIDTH_MM,
                base_module_height_mm=base_module_height_mm,
                kitchen_height_mm=kitchen_height_mm,
            )
        )
        result.extend(
            _assign_x_to_side_modules(
                external_tall_modules,
                side=side,
                start_x=max(
                    CORNER_MODULE_WIDTH_MM
                    + CORNER_FALSE_PANEL_WIDTH_MM
                    + _modules_width(middle_modules),
                    side_width_mm
                    + CORNER_FALSE_PANEL_WIDTH_MM
                    - _modules_width(external_tall_modules),
                ),
                base_module_height_mm=base_module_height_mm,
                kitchen_height_mm=kitchen_height_mm,
            )
        )
    else:
        result.extend(
            _assign_x_to_side_modules(
                external_tall_modules,
                side=side,
                start_x=0,
                base_module_height_mm=base_module_height_mm,
                kitchen_height_mm=kitchen_height_mm,
            )
        )
        result.extend(
            _assign_x_to_side_modules(
                middle_modules,
                side=side,
                start_x=max(
                    _modules_width(external_tall_modules),
                    side_width_mm
                    - CORNER_MODULE_WIDTH_MM
                    - _modules_width(middle_modules),
                ),
                base_module_height_mm=base_module_height_mm,
                kitchen_height_mm=kitchen_height_mm,
            )
        )

    return result


def _make_corner_false_panel(
    *,
    side: str,
    x_mm: int,
    base_module_height_mm: int,
) -> dict:
    return {
        "type": "base",
        "name": "corner_false_panel",
        "width_mm": CORNER_FALSE_PANEL_WIDTH_MM,
        "height_mm": base_module_height_mm,
        "x_mm": x_mm,
        "side_x_mm": x_mm,
        "side": side,
        "corner_false_panel": True,
        "countertop_role": "none",
        "countertop_free_mm": 0,
    }


def _has_projection_tall_module(modules: list[dict]) -> bool:
    return any(
        _is_full_height_end_module(module)
        for module in modules
        if not module.get("corner_module")
    )


def _corner_display_module_depth(
    other_side_modules: list[dict],
    *,
    wall_cabinets_enabled: bool,
) -> int:
    if _has_projection_tall_module(other_side_modules):
        return 600

    if wall_cabinets_enabled:
        return round_up_to_step(WALL_CABINET_DEPTH_MM)

    return 0


def _corner_upper_display_module_depth(
    *,
    wall_cabinets_enabled: bool,
) -> int:
    if wall_cabinets_enabled:
        return WALL_CABINET_DEPTH_MM

    return 0


def _corner_wall_blocked_ranges(
    *,
    side_width_mm: int,
    corner_at_start: bool,
    upper_display_depth_mm: int,
) -> list[tuple[int, int]]:
    if upper_display_depth_mm <= 0:
        return []

    if corner_at_start:
        false_panel_start = min(upper_display_depth_mm, side_width_mm)
    else:
        false_panel_start = max(
            0,
            side_width_mm - upper_display_depth_mm - CORNER_FALSE_PANEL_WIDTH_MM,
        )

    false_panel_width = max(
        0,
        min(CORNER_FALSE_PANEL_WIDTH_MM, side_width_mm - false_panel_start),
    )
    return (
        [(false_panel_start, false_panel_width)]
        if false_panel_width > 0
        else []
    )


def _suppress_corner_upper_openings(
    wall_modules: list[dict],
    *,
    side_width_mm: int,
    corner_at_start: bool,
    upper_display_depth_mm: int,
) -> list[dict]:
    if upper_display_depth_mm <= 0:
        return wall_modules

    corner_depth_mm = round_up_to_step(upper_display_depth_mm)
    if corner_at_start:
        corner_start = 0
        corner_end = min(corner_depth_mm, side_width_mm)
    else:
        corner_start = max(0, side_width_mm - corner_depth_mm)
        corner_end = side_width_mm

    marked_modules = []
    for module in wall_modules:
        if module.get("tier") not in {"upper", "hood", "mezzanine"}:
            marked_modules.append(module)
            continue

        module_start = int(module.get("x_mm", 0))
        module_end = module_start + int(module.get("width_mm", 0))
        if module_start >= corner_start and module_end <= corner_end:
            module = {**module, "suppress_opening_marks": True}

        marked_modules.append(module)

    return marked_modules


def _standard_internal_gap_width(gap_mm: int) -> int:
    if gap_mm in GENERATED_DRAWER_WIDTHS:
        return gap_mm

    return min(
        GENERATED_DRAWER_WIDTHS,
        key=lambda width: (
            abs(width - gap_mm),
            abs(width - PREFERRED_DRAWER_WIDTH_MM),
            -width,
        ),
    )


def _make_corner_module_for_side(
    *,
    side: str,
    x_mm: int,
    kitchen_height_mm: int,
    as_tall: bool,
) -> dict:
    module = {
        "type": "tall" if as_tall else "base",
        "name": "corner_tall" if as_tall else "corner_base",
        "width_mm": CORNER_MODULE_WIDTH_MM,
        "height_mm": kitchen_height_mm,
        "x_mm": x_mm,
        "side_x_mm": x_mm,
        "side": side,
        "corner_module": True,
        "countertop_role": "none" if as_tall else "blocked",
    }

    return module


def _normalize_internal_gap_widths(
    modules: list[dict],
    *,
    side_width_mm: int,
) -> tuple[list[dict], int, list[dict]]:
    sorted_modules = sorted(modules, key=lambda module: module.get("x_mm", 0))
    adjustments = []
    effective_side_width_mm = side_width_mm

    for previous, current in zip(sorted_modules, sorted_modules[1:]):
        previous_end = previous.get("x_mm", 0) + previous.get("width_mm", 0)
        gap_mm = current.get("x_mm", 0) - previous_end

        if gap_mm <= 0:
            continue

        gap_widths = choose_drawer_widths_for_remaining_space(gap_mm)
        if sum(gap_widths) == gap_mm:
            continue

        standard_gap_mm = _standard_internal_gap_width(gap_mm)
        delta_mm = standard_gap_mm - gap_mm

        if delta_mm == 0:
            continue

        current_x = current.get("x_mm", 0)

        for module in sorted_modules:
            if module.get("x_mm", 0) >= current_x:
                module["x_mm"] += delta_mm
                module["side_x_mm"] = module["x_mm"]

        effective_side_width_mm += delta_mm
        adjustments.append(
            {
                "from_mm": gap_mm,
                "to_mm": standard_gap_mm,
                "delta_mm": delta_mm,
            }
        )

    return sorted_modules, effective_side_width_mm, adjustments


def _insert_internal_gap_fillers(
    modules: list[dict],
    *,
    side: str,
    base_module_height_mm: int,
    kitchen_height_mm: int,
) -> list[dict]:
    sorted_modules = sorted(modules, key=lambda module: module.get("x_mm", 0))
    result = []

    for index, module in enumerate(sorted_modules):
        if index > 0:
            previous = sorted_modules[index - 1]
            previous_end = previous.get("x_mm", 0) + previous.get("width_mm", 0)
            gap_mm = module.get("x_mm", 0) - previous_end

            if gap_mm > 0:
                gap_widths = choose_drawer_widths_for_remaining_space(gap_mm)
                current_x = previous_end

                for drawer_width in gap_widths:
                    result.append(
                        {
                            "type": "base",
                            "name": "drawer_3",
                            "width_mm": drawer_width,
                            "height_mm": base_module_height_mm,
                            "x_mm": current_x,
                            "side_x_mm": current_x,
                            "side": side,
                            "is_generated_filler": True,
                            "filler_reason": "corner_internal_gap",
                            "countertop_role": "free_worktop",
                            "countertop_free_mm": drawer_width,
                        }
                    )
                    current_x += drawer_width

        result.append(module)

    return result


def _build_corner_side_detail(
    *,
    side: str,
    side_width_mm: int,
    side_modules_without_corner: list[dict],
    corner_at_start: bool,
    corner_is_tall: bool,
    base_module_height_mm: int,
    kitchen_height_mm: int,
    cabinet_top_height_mm: int,
    countertop_material_key: str,
    countertop_thickness_mm: int,
    wall_cabinet_bottom_mm: int,
    wall_cabinets_enabled: bool,
    mezzanine_enabled: bool,
    hob: dict,
    hob_width: int,
    hood_width: int,
    microwave_type: str,
    upper_built_in_microwave_present: bool = False,
    upper_cabinet_opening: str = "hinged",
    corner_display_depth_mm: int = 0,
    corner_upper_display_depth_mm: int = 0,
    warnings: list[str],
) -> dict:
    modules = _assign_corner_side_modules(
        side_modules_without_corner,
        side=side,
        side_width_mm=side_width_mm,
        corner_at_start=corner_at_start,
        base_module_height_mm=base_module_height_mm,
        kitchen_height_mm=cabinet_top_height_mm,
    )
    effective_side_width_mm = side_width_mm + CORNER_FALSE_PANEL_WIDTH_MM
    corner_x = (
        0
        if corner_at_start
        else effective_side_width_mm - CORNER_MODULE_WIDTH_MM
    )
    corner_module = _make_corner_module_for_side(
        side=side,
        x_mm=corner_x,
        kitchen_height_mm=cabinet_top_height_mm,
        as_tall=corner_is_tall,
    )
    false_panel_x = (
        CORNER_MODULE_WIDTH_MM
        if corner_at_start
        else effective_side_width_mm
        - CORNER_MODULE_WIDTH_MM
        - CORNER_FALSE_PANEL_WIDTH_MM
    )
    false_panel = _make_corner_false_panel(
        side=side,
        x_mm=false_panel_x,
        base_module_height_mm=base_module_height_mm,
    )
    modules = (
        [corner_module, false_panel] + modules
        if corner_at_start
        else modules + [false_panel, corner_module]
    )
    modules = sorted(modules, key=lambda module: module.get("x_mm", 0))
    modules, effective_side_width_mm, width_adjustments = _normalize_internal_gap_widths(
        modules,
        side_width_mm=effective_side_width_mm,
    )
    modules = _insert_internal_gap_fillers(
        modules,
        side=side,
        base_module_height_mm=base_module_height_mm,
        kitchen_height_mm=kitchen_height_mm,
    )

    hob_objects, hob_placement = place_hob_on_worktop(
        modules=modules,
        hob=hob,
        warnings=warnings,
    )
    sink_module = next((module for module in modules if module.get("name") == "sink"), None)
    cooking_module = next(
        (
            module
            for module in modules
            if module.get("countertop_occupied_by") == "hob" or module.get("supports_hob")
        ),
        None,
    )
    wall_modules = build_wall_modules(
        modules=modules,
        wall_length_mm=effective_side_width_mm,
        kitchen_height_mm=kitchen_height_mm,
        wall_cabinet_bottom_mm=wall_cabinet_bottom_mm,
        wall_cabinets_enabled=wall_cabinets_enabled,
        mezzanine_enabled=mezzanine_enabled,
        cooking_module=cooking_module,
        hob_width=hob_width,
        hob_placement=hob_placement,
        hood_width=hood_width,
        sink_module=sink_module,
        microwave_type=microwave_type,
        upper_built_in_microwave_present=upper_built_in_microwave_present,
        ceiling_filler_height_mm=kitchen_height_mm - cabinet_top_height_mm,
        upper_cabinet_opening=upper_cabinet_opening,
        blocked_wall_ranges=_corner_wall_blocked_ranges(
            side_width_mm=effective_side_width_mm,
            corner_at_start=corner_at_start,
            upper_display_depth_mm=corner_upper_display_depth_mm,
        ),
    )
    wall_modules = apply_wall_facade_grouping(
        wall_modules,
        upper_cabinet_opening=upper_cabinet_opening,
    )
    wall_modules = _suppress_corner_upper_openings(
        wall_modules,
        side_width_mm=effective_side_width_mm,
        corner_at_start=corner_at_start,
        upper_display_depth_mm=corner_upper_display_depth_mm,
    )

    upper_microwave_placement = None
    if (
        microwave_type == "upper_built_in"
        and any(
            module.get("reserved_for") == "built_in_microwave"
            for module in wall_modules
        )
    ):
        upper_microwave_placement = place_upper_built_in_microwave(
            wall_modules=wall_modules,
            microwave={},
            warnings=warnings,
            sink_module=sink_module,
        )

    return {
        "wall_length_mm": effective_side_width_mm,
        "original_wall_length_mm": side_width_mm,
        "width_adjustments": width_adjustments,
        "corner_position": "left" if corner_at_start else "right",
        "modules": modules,
        "wall_modules": wall_modules,
        "front_objects": hob_objects,
        "plinth_modules": build_plinth_modules(modules),
        "countertop_modules": build_countertop_modules(
            modules=modules,
            material_key=countertop_material_key,
            thickness_mm=countertop_thickness_mm,
        ),
        "wall_panel_modules": build_wall_panel_modules(
            modules=modules,
            countertop_thickness_mm=countertop_thickness_mm,
        ),
        "hob_placement": hob_placement,
        "upper_microwave_placement": upper_microwave_placement,
    }


def _module_corner_clearance(module: dict, *, side_width_mm: int, corner_at_start: bool) -> int:
    if module.get("countertop_occupied_by") == "hob":
        module_start = module.get("countertop_occupied_x_mm", module.get("x_mm", 0))
        module_width = module.get("countertop_occupied_width_mm", module.get("width_mm", 0))
    else:
        module_start = module.get("x_mm", 0)
        module_width = module.get("width_mm", 0)

    module_end = module_start + module_width
    corner_buffer_width = CORNER_MODULE_WIDTH_MM + CORNER_FALSE_PANEL_WIDTH_MM

    if corner_at_start:
        return max(0, module_start - corner_buffer_width)

    return max(0, side_width_mm - corner_buffer_width - module_end)


def _corner_worktop_distance(
    side_1: dict,
    side_2: dict,
    side_1_width_mm: int,
    side_2_width_mm: int,
) -> int:
    sink_side = None
    hob_side = None
    sink_module = None
    hob_module = None

    for side_key, side in (("side_1", side_1), ("side_2", side_2)):
        for module in side.get("modules", []):
            if module.get("name") == "sink":
                sink_side = side_key
                sink_module = module
            if module.get("countertop_occupied_by") == "hob":
                hob_side = side_key
                hob_module = module

    if not sink_module or not hob_module:
        return 0

    if sink_side == hob_side:
        return calculate_free_worktop_between_sink_and_hob(side_1["modules"] if sink_side == "side_1" else side_2["modules"])

    sides = {
        "side_1": (side_1, side_1_width_mm),
        "side_2": (side_2, side_2_width_mm),
    }
    sink_layout, sink_side_width = sides[sink_side]
    hob_layout, hob_side_width = sides[hob_side]

    return (
        _module_corner_clearance(
            sink_module,
            side_width_mm=sink_side_width,
            corner_at_start=sink_layout.get("corner_position") == "left",
        )
        + _module_corner_clearance(
            hob_module,
            side_width_mm=hob_side_width,
            corner_at_start=hob_layout.get("corner_position") == "left",
        )
    )


def _score_corner_candidate(
    *,
    side_1: dict,
    side_2: dict,
    side_1_width_mm: int,
    side_2_width_mm: int,
    corner_is_tall: bool,
    water_output_side: str,
) -> tuple:
    has_full_height_modules = any(
        _is_full_height_end_module(module)
        for module in side_1["modules"] + side_2["modules"]
        if not module.get("corner_module")
    )
    side_1_payload = [
        module for module in side_1["modules"] if not module.get("corner_module")
    ]
    side_2_payload = [
        module for module in side_2["modules"] if not module.get("corner_module")
    ]
    side_1_external_module = (
        side_1_payload[-1]
        if side_1.get("corner_position") == "left" and side_1_payload
        else side_1_payload[0] if side_1_payload else None
    )
    side_2_external_module = (
        side_2_payload[-1]
        if side_2.get("corner_position") == "left" and side_2_payload
        else side_2_payload[0] if side_2_payload else None
    )
    side_1_ends_with_full_height = bool(
        side_1_external_module and _is_full_height_end_module(side_1_external_module)
    )
    side_2_ends_with_full_height = bool(
        side_2_external_module and _is_full_height_end_module(side_2_external_module)
    )
    full_height_end_penalty = int(
        has_full_height_modules
        and not (side_1_ends_with_full_height or side_2_ends_with_full_height)
    )
    side_1_payload_end = max(
        (
            module["x_mm"] + module["width_mm"]
            for module in side_1["modules"]
            if not module.get("corner_module")
        ),
        default=0,
    )
    side_2_payload_end = max(
        (
            module["x_mm"] + module["width_mm"]
            for module in side_2["modules"]
            if not module.get("corner_module")
        ),
        default=CORNER_MODULE_WIDTH_MM,
    )
    side_1_used = max((module["x_mm"] + module["width_mm"] for module in side_1["modules"]), default=0)
    side_2_used = max((module["x_mm"] + module["width_mm"] for module in side_2["modules"]), default=0)
    internal_gap = _internal_module_gap(side_1["modules"]) + _internal_module_gap(side_2["modules"])
    overflow = (
        max(
            0,
            side_1_payload_end
            - (
                side_1_width_mm
                if side_1.get("corner_position") == "left"
                else side_1_width_mm - CORNER_MODULE_WIDTH_MM
            ),
        )
        + max(
            0,
            side_2_payload_end
            - (
                side_2_width_mm
                if side_2.get("corner_position") == "left"
                else side_2_width_mm - CORNER_MODULE_WIDTH_MM
            ),
        )
    )
    free_worktop = _corner_worktop_distance(
        side_1,
        side_2,
        side_1_width_mm,
        side_2_width_mm,
    )
    worktop_penalty = 0

    if free_worktop < WORKTOP_MIN_MM:
        worktop_penalty = WORKTOP_MIN_MM - free_worktop
    elif free_worktop > WORKTOP_MAX_MM:
        worktop_penalty = free_worktop - WORKTOP_MAX_MM

    missing_hob = int(not (side_1.get("hob_placement") or side_2.get("hob_placement")))
    sink_module = next(
        (module for module in side_1["modules"] if module.get("name") == "sink"),
        None,
    )
    missing_front_sink = int(sink_module is None)
    if sink_module:
        if water_output_side == "right":
            sink_position_penalty = abs(
                (sink_module["x_mm"] + sink_module["width_mm"])
                - (side_1_width_mm - CORNER_MODULE_WIDTH_MM)
            )
        else:
            sink_position_penalty = abs(sink_module["x_mm"] - CORNER_MODULE_WIDTH_MM)
    else:
        sink_position_penalty = 9999

    side_1_near_corner_gap = 0
    if side_1_payload:
        if side_1.get("corner_position") == "left":
            side_1_near_corner_gap = max(
                0,
                min(module["x_mm"] for module in side_1_payload) - CORNER_MODULE_WIDTH_MM,
            )
        else:
            side_1_near_corner_gap = max(
                0,
                side_1_width_mm
                - CORNER_MODULE_WIDTH_MM
                - max(module["x_mm"] + module["width_mm"] for module in side_1_payload),
            )

    side_2_near_corner_gap = 0
    if side_2_payload:
        if side_2.get("corner_position") == "left":
            side_2_near_corner_gap = max(
                0,
                min(module["x_mm"] for module in side_2_payload) - CORNER_MODULE_WIDTH_MM,
            )
        else:
            side_2_near_corner_gap = max(
                0,
                side_2_width_mm
                - CORNER_MODULE_WIDTH_MM
                - max(module["x_mm"] + module["width_mm"] for module in side_2_payload),
            )

    missing_microwave = int(
        any(
            module.get("reserved_for") == "built_in_microwave"
            for module in side_1.get("wall_modules", []) + side_2.get("wall_modules", [])
        )
        is False
    )

    return (
        overflow,
        missing_front_sink,
        missing_hob,
        sink_position_penalty,
        internal_gap,
        side_1_near_corner_gap + side_2_near_corner_gap,
        full_height_end_penalty,
        worktop_penalty,
        int(corner_is_tall),
        abs((side_1_width_mm - side_1_used) - (side_2_width_mm - side_2_used)),
        side_1_used + side_2_used,
        missing_microwave,
    )


def _build_corner_candidate_orders(
    groups: dict[str, list[dict]],
    side_1_capacity: int,
    side_2_capacity: int,
    *,
    side_1_corner_at_start: bool,
    side_2_corner_at_start: bool,
):
    sink_group = groups["sink"]
    cooking_group = groups["cooking"]
    tall_group = groups["tall"]
    other_modules = groups["other"]

    for sink_side in ("side_1", "side_2"):
        for cooking_side in ("side_1", "side_2"):
            tall_options = [
                ("side_1", tall_group, []),
                ("side_2", [], tall_group),
            ]
            if len(tall_group) >= 2 and not any(
                module.get("type") == "profile_handle"
                for module in tall_group
            ):
                split_index = len(tall_group) // 2
                tall_options.append(("split", tall_group[:split_index], tall_group[split_index:]))

            for _, side_1_tall, side_2_tall in tall_options:
                side_1_tall = _order_external_tall_modules(
                    side_1_tall,
                    corner_at_start=side_1_corner_at_start,
                )
                side_2_tall = _order_external_tall_modules(
                    side_2_tall,
                    corner_at_start=side_2_corner_at_start,
                )
                side_groups = {"side_1": [], "side_2": []}
                side_groups[sink_side].append(("sink", sink_group))
                side_groups[cooking_side].append(("cooking", cooking_group))

                base_side_1_width = _modules_width(side_1_tall) + sum(_modules_width(group) for _, group in side_groups["side_1"])
                base_side_2_width = _modules_width(side_2_tall) + sum(_modules_width(group) for _, group in side_groups["side_2"])

                for assignment in product(("side_1", "side_2", "skip"), repeat=len(other_modules)):
                    side_1_other = [
                        module
                        for module, target_side in zip(other_modules, assignment)
                        if target_side == "side_1"
                    ]
                    side_2_other = [
                        module
                        for module, target_side in zip(other_modules, assignment)
                        if target_side == "side_2"
                    ]

                    if base_side_1_width + _modules_width(side_1_other) > side_1_capacity:
                        continue

                    if base_side_2_width + _modules_width(side_2_other) > side_2_capacity:
                        continue

                    side_1_order_groups = side_groups["side_1"] + [
                        (f"other_{index}", [module])
                        for index, module in enumerate(side_1_other)
                    ]
                    side_2_order_groups = side_groups["side_2"] + [
                        (f"other_{index}", [module])
                        for index, module in enumerate(side_2_other)
                    ]

                    for side_1_order in permutations(side_1_order_groups):
                        for side_2_order in permutations(side_2_order_groups):
                            side_1_middle = [
                                module
                                for _, group in side_1_order
                                for module in group
                            ]
                            side_2_middle = [
                                module
                                for _, group in side_2_order
                                for module in group
                            ]
                            side_1_modules = (
                                side_1_middle + side_1_tall
                                if side_1_corner_at_start
                                else side_1_tall + side_1_middle
                            )
                            side_2_modules = (
                                side_2_middle + side_2_tall
                                if side_2_corner_at_start
                                else side_2_tall + side_2_middle
                            )
                            yield side_1_modules, side_2_modules


def _has_tall_adjacent_to_corner(
    modules: list[dict],
    *,
    side: str,
    side_width_mm: int,
    corner_at_start: bool,
) -> bool:
    for module in modules:
        if not _is_tall_like_module(module):
            continue

        module_start = module.get("x_mm", 0)
        module_end = module_start + module.get("width_mm", 0)

        if (
            corner_at_start
            and module_start == CORNER_MODULE_WIDTH_MM + CORNER_FALSE_PANEL_WIDTH_MM
        ):
            return True

        if (
            not corner_at_start
            and module_end
            == side_width_mm - CORNER_MODULE_WIDTH_MM - CORNER_FALSE_PANEL_WIDTH_MM
        ):
            return True

    return False


def _internal_module_gap(modules: list[dict]) -> int:
    sorted_modules = sorted(modules, key=lambda module: module.get("x_mm", 0))
    gap_mm = 0

    for previous, current in zip(sorted_modules, sorted_modules[1:]):
        previous_end = previous.get("x_mm", 0) + previous.get("width_mm", 0)
        gap_mm += max(0, current.get("x_mm", 0) - previous_end)

    return gap_mm


def _touches_or_overlaps_corner(
    *,
    x_mm: int,
    width_mm: int,
    side_width_mm: int,
    corner_at_start: bool,
) -> bool:
    start = x_mm
    end = x_mm + width_mm
    corner_start = 0 if corner_at_start else side_width_mm - CORNER_MODULE_WIDTH_MM
    corner_end = corner_start + CORNER_MODULE_WIDTH_MM

    return start <= corner_end and end >= corner_start


def _has_forbidden_corner_base_neighbor(
    side_layout: dict,
    *,
    side_width_mm: int,
    corner_at_start: bool,
) -> bool:
    has_corner_base = any(
        module.get("corner_module") and module.get("name") == "corner_base"
        for module in side_layout.get("modules", [])
    )

    if not has_corner_base:
        return False

    for module in side_layout.get("modules", []):
        if module.get("corner_module"):
            continue

        module_name = module.get("name", "")
        if module_name != "oven_under_counter" and not module_name.startswith("dishwasher_"):
            continue

        if _touches_or_overlaps_corner(
            x_mm=module.get("x_mm", 0),
            width_mm=module.get("width_mm", 0),
            side_width_mm=side_width_mm,
            corner_at_start=corner_at_start,
        ):
            return True

    for module in side_layout.get("wall_modules", []):
        if module.get("name") != "built_in_microwave" and module.get("reserved_for") != "built_in_microwave":
            continue

        if _touches_or_overlaps_corner(
            x_mm=module.get("x_mm", 0),
            width_mm=module.get("width_mm", 0),
            side_width_mm=side_width_mm,
            corner_at_start=corner_at_start,
        ):
            return True

    return False


def _make_corner_module(side: str, kitchen_height_mm: int) -> dict:
    return {
        "type": "base",
        "name": "corner_base",
        "width_mm": CORNER_MODULE_WIDTH_MM,
        "height_mm": kitchen_height_mm,
        "x_mm": 0 if side == "side_2" else None,
        "side_x_mm": 0 if side == "side_2" else None,
        "side": side,
        "corner_module": True,
        "countertop_role": "blocked",
    }


def generate_corner_layout(
    normalized_spec: dict,
    module_options: dict | None = None,
    *,
    straight_layout_builder,
) -> dict:
    module_options = module_options or {}
    room = module_options.get("room", {})
    side_1_width_mm = to_int(
        room.get("side_1_width_mm", room.get("wall_length_mm")),
        normalized_spec.get("wall_length_mm", 3000),
    )
    side_2_width_mm = to_int(room.get("side_2_width_mm"), 2400)
    corner_width_mm = CORNER_MODULE_WIDTH_MM
    side_1_capacity = max(0, side_1_width_mm - corner_width_mm)
    side_2_capacity = max(0, side_2_width_mm - corner_width_mm)
    total_linear_width = side_1_capacity + side_2_capacity
    corner_position = "left" if room.get("entry_side") == "left" else "right"
    side_1_corner_at_start = corner_position == "left"
    side_2_corner_at_start = corner_position == "right"

    straight_options = _copy_for_straight_generation(
        module_options,
        total_linear_width,
    )
    straight_layout = straight_layout_builder(
        normalized_spec={**normalized_spec, "shape": "straight", "wall_length_mm": total_linear_width},
        module_options=straight_options,
    )

    kitchen_height_mm = straight_layout.get("kitchen_height_mm", 2700)
    ceiling_filler_height_mm = straight_layout.get("ceiling_filler_height_mm", 0)
    cabinet_top_height_mm = kitchen_height_mm - ceiling_filler_height_mm
    base_module_height_mm = straight_layout.get("base_module_height_mm", 720)
    countertop_material_key = straight_layout.get("countertop_material", "chipboard_plastic")
    countertop_thickness_mm = straight_layout.get("countertop_thickness_mm", 38)
    wall_cabinet_bottom_mm = (
        PLINTH_HEIGHT_MM
        + base_module_height_mm
        + straight_layout.get("lower_profile_handle_height_mm", LOWER_PROFILE_HANDLE_HEIGHT_MM)
        + countertop_thickness_mm
        + WALL_PANEL_HEIGHT_MM
    )
    required = module_options.get("required", {})
    hood = required.get("hood", {})
    hob = required.get("hob", {})
    microwave = required.get("microwave", {})
    microwave_type = _effective_corner_microwave_type(
        straight_layout,
        microwave.get("type", "solo"),
    )
    upper_cabinet_opening = straight_layout.get(
        "upper_cabinet_opening",
        room.get("upper_cabinet_opening", "hinged"),
    )
    upper_cabinet_opening = "lift" if upper_cabinet_opening == "lift" else "hinged"
    upper_built_in_microwave_present = microwave_type == "upper_built_in"
    hob_width = to_int(hob.get("cabinet_width_mm", hob.get("width_mm")), 600)
    hood_width = get_hood_width_for_hob(hob_width)

    if get_locked_options(module_options).get("hood.width_mm"):
        hood_width = to_int(hood.get("width_mm"), hood_width)

    groups = _group_corner_source_modules(straight_layout.get("modules", []))
    best_candidate = None
    best_score = None

    for side_1_candidate_modules, side_2_candidate_modules in _build_corner_candidate_orders(
        groups,
        side_1_capacity,
        side_2_capacity,
        side_1_corner_at_start=side_1_corner_at_start,
        side_2_corner_at_start=side_2_corner_at_start,
    ):
        side_1_has_sink = any(
            module.get("name") == "sink"
            for module in side_1_candidate_modules
        )
        side_2_has_sink = any(
            module.get("name") == "sink"
            for module in side_2_candidate_modules
        )
        microwave_side = "side_1" if side_1_has_sink or not side_2_has_sink else "side_2"
        side_1_microwave_type = microwave_type if microwave_side == "side_1" else "none"
        side_2_microwave_type = microwave_type if microwave_side == "side_2" else "none"
        wall_cabinets_enabled = straight_layout.get("wall_cabinets_enabled", True)
        mezzanine_enabled = straight_layout.get("mezzanine_enabled", True)
        side_1_display_depth_mm = _corner_display_module_depth(
            side_2_candidate_modules,
            wall_cabinets_enabled=wall_cabinets_enabled,
        )
        side_2_display_depth_mm = _corner_display_module_depth(
            side_1_candidate_modules,
            wall_cabinets_enabled=wall_cabinets_enabled,
        )
        side_1_upper_display_depth_mm = _corner_upper_display_module_depth(
            wall_cabinets_enabled=wall_cabinets_enabled,
        )
        side_2_upper_display_depth_mm = _corner_upper_display_module_depth(
            wall_cabinets_enabled=wall_cabinets_enabled,
        )
        candidate_warnings = []
        side_1 = _build_corner_side_detail(
            side="side_1",
            side_width_mm=side_1_width_mm,
            side_modules_without_corner=side_1_candidate_modules,
            corner_at_start=side_1_corner_at_start,
            corner_is_tall=False,
            base_module_height_mm=base_module_height_mm,
            kitchen_height_mm=kitchen_height_mm,
            cabinet_top_height_mm=cabinet_top_height_mm,
            countertop_material_key=countertop_material_key,
            countertop_thickness_mm=countertop_thickness_mm,
            wall_cabinet_bottom_mm=wall_cabinet_bottom_mm,
            wall_cabinets_enabled=wall_cabinets_enabled,
            mezzanine_enabled=mezzanine_enabled,
            hob=hob,
            hob_width=hob_width,
            hood_width=hood_width,
            microwave_type=side_1_microwave_type,
            upper_built_in_microwave_present=upper_built_in_microwave_present,
            upper_cabinet_opening=upper_cabinet_opening,
            corner_display_depth_mm=side_1_display_depth_mm,
            corner_upper_display_depth_mm=side_1_upper_display_depth_mm,
            warnings=candidate_warnings,
        )

        side_2 = _build_corner_side_detail(
            side="side_2",
            side_width_mm=side_2_width_mm,
            side_modules_without_corner=side_2_candidate_modules,
            corner_at_start=side_2_corner_at_start,
            corner_is_tall=False,
            base_module_height_mm=base_module_height_mm,
            kitchen_height_mm=kitchen_height_mm,
            cabinet_top_height_mm=cabinet_top_height_mm,
            countertop_material_key=countertop_material_key,
            countertop_thickness_mm=countertop_thickness_mm,
            wall_cabinet_bottom_mm=wall_cabinet_bottom_mm,
            wall_cabinets_enabled=wall_cabinets_enabled,
            mezzanine_enabled=mezzanine_enabled,
            hob=hob,
            hob_width=hob_width,
            hood_width=hood_width,
            microwave_type=side_2_microwave_type,
            upper_built_in_microwave_present=upper_built_in_microwave_present,
            upper_cabinet_opening=upper_cabinet_opening,
            corner_display_depth_mm=side_2_display_depth_mm,
            corner_upper_display_depth_mm=side_2_upper_display_depth_mm,
            warnings=candidate_warnings,
        )

        if _has_forbidden_corner_base_neighbor(
            side_1,
            side_width_mm=side_1.get("wall_length_mm", side_1_width_mm),
            corner_at_start=side_1_corner_at_start,
        ):
            continue

        if _has_forbidden_corner_base_neighbor(
            side_2,
            side_width_mm=side_2.get("wall_length_mm", side_2_width_mm),
            corner_at_start=side_2_corner_at_start,
        ):
            continue

        corner_is_tall = _has_tall_adjacent_to_corner(
            side_1["modules"],
            side="side_1",
            side_width_mm=side_1.get("wall_length_mm", side_1_width_mm),
            corner_at_start=side_1_corner_at_start,
        ) or _has_tall_adjacent_to_corner(
            side_2["modules"],
            side="side_2",
            side_width_mm=side_2.get("wall_length_mm", side_2_width_mm),
            corner_at_start=side_2_corner_at_start,
        )

        if corner_is_tall:
            candidate_warnings = []
            side_1 = _build_corner_side_detail(
                side="side_1",
                side_width_mm=side_1_width_mm,
                side_modules_without_corner=side_1_candidate_modules,
                corner_at_start=side_1_corner_at_start,
                corner_is_tall=True,
                base_module_height_mm=base_module_height_mm,
                kitchen_height_mm=kitchen_height_mm,
                cabinet_top_height_mm=cabinet_top_height_mm,
                countertop_material_key=countertop_material_key,
                countertop_thickness_mm=countertop_thickness_mm,
                wall_cabinet_bottom_mm=wall_cabinet_bottom_mm,
                wall_cabinets_enabled=wall_cabinets_enabled,
                mezzanine_enabled=mezzanine_enabled,
                hob=hob,
                hob_width=hob_width,
                hood_width=hood_width,
                microwave_type=side_1_microwave_type,
                upper_built_in_microwave_present=upper_built_in_microwave_present,
                upper_cabinet_opening=upper_cabinet_opening,
                corner_display_depth_mm=side_1_display_depth_mm,
                corner_upper_display_depth_mm=side_1_upper_display_depth_mm,
                warnings=candidate_warnings,
            )
            side_2 = _build_corner_side_detail(
                side="side_2",
                side_width_mm=side_2_width_mm,
                side_modules_without_corner=side_2_candidate_modules,
                corner_at_start=side_2_corner_at_start,
                corner_is_tall=True,
                base_module_height_mm=base_module_height_mm,
                kitchen_height_mm=kitchen_height_mm,
                cabinet_top_height_mm=cabinet_top_height_mm,
                countertop_material_key=countertop_material_key,
                countertop_thickness_mm=countertop_thickness_mm,
                wall_cabinet_bottom_mm=wall_cabinet_bottom_mm,
                wall_cabinets_enabled=wall_cabinets_enabled,
                mezzanine_enabled=mezzanine_enabled,
                hob=hob,
                hob_width=hob_width,
                hood_width=hood_width,
                microwave_type=side_2_microwave_type,
                upper_built_in_microwave_present=upper_built_in_microwave_present,
                upper_cabinet_opening=upper_cabinet_opening,
                corner_display_depth_mm=side_2_display_depth_mm,
                corner_upper_display_depth_mm=side_2_upper_display_depth_mm,
                warnings=candidate_warnings,
            )

            if _has_forbidden_corner_base_neighbor(
                side_1,
                side_width_mm=side_1.get("wall_length_mm", side_1_width_mm),
                corner_at_start=side_1_corner_at_start,
            ):
                continue

            if _has_forbidden_corner_base_neighbor(
                side_2,
                side_width_mm=side_2.get("wall_length_mm", side_2_width_mm),
                corner_at_start=side_2_corner_at_start,
            ):
                continue

        score = _score_corner_candidate(
            side_1=side_1,
            side_2=side_2,
            side_1_width_mm=side_1.get("wall_length_mm", side_1_width_mm),
            side_2_width_mm=side_2.get("wall_length_mm", side_2_width_mm),
            corner_is_tall=corner_is_tall,
            water_output_side=room.get("entry_side", "left"),
        )

        if best_score is None or score < best_score:
            best_score = score
            best_candidate = (side_1, side_2, corner_is_tall, candidate_warnings)

    if best_candidate is None:
        raise RuntimeError("Corner layout candidate generation failed")

    side_1, side_2, corner_is_tall, candidate_warnings = best_candidate
    renumber_generated_drawers(side_1["modules"])
    renumber_generated_drawers(side_2["modules"])
    effective_side_1_width_mm = side_1.get("wall_length_mm", side_1_width_mm)
    effective_side_2_width_mm = side_2.get("wall_length_mm", side_2_width_mm)
    free_worktop_between_sink_and_hob = _corner_worktop_distance(
        side_1,
        side_2,
        effective_side_1_width_mm,
        effective_side_2_width_mm,
    )
    warnings = list(straight_layout.get("warnings", []))
    warnings.extend(candidate_warnings[:2])

    size_adjustments = [
        adjustment
        for adjustment in straight_layout.get("size_adjustments", [])
        if adjustment.get("field") != "room.wall_length_mm"
    ]

    if effective_side_1_width_mm != side_1_width_mm:
        size_adjustments.append(
            {
                "field": "room.side_1_width_mm",
                "label": "Ширина стороны 1",
                "from_mm": side_1_width_mm,
                "to_mm": effective_side_1_width_mm,
                "reason": "corner_internal_gap_standard_drawer",
            }
        )

    if effective_side_2_width_mm != side_2_width_mm:
        size_adjustments.append(
            {
                "field": "room.side_2_width_mm",
                "label": "Ширина стороны 2",
                "from_mm": side_2_width_mm,
                "to_mm": effective_side_2_width_mm,
                "reason": "corner_internal_gap_standard_drawer",
            }
        )

    layout = {
        **straight_layout,
        "shape": "corner",
        "wall_length_mm": effective_side_1_width_mm,
        "side_1_width_mm": effective_side_1_width_mm,
        "side_2_width_mm": effective_side_2_width_mm,
        "corner_module_width_mm": corner_width_mm,
        "corner_position": corner_position,
        "corner_is_tall": corner_is_tall,
        "used_width_mm": effective_side_1_width_mm + effective_side_2_width_mm - corner_width_mm,
        "remaining_width_mm": max(0, total_linear_width - straight_layout.get("used_width_mm", 0)),
        "side_1": side_1,
        "side_2": side_2,
        "modules": side_1["modules"] + side_2["modules"],
        "wall_modules": side_1["wall_modules"] + side_2["wall_modules"],
        "front_objects": side_1["front_objects"] + side_2["front_objects"],
        "plinth_modules": side_1["plinth_modules"] + side_2["plinth_modules"],
        "countertop_modules": side_1["countertop_modules"] + side_2["countertop_modules"],
        "wall_panel_modules": side_1["wall_panel_modules"] + side_2["wall_panel_modules"],
        "hob_placement": side_1.get("hob_placement") or side_2.get("hob_placement"),
        "upper_microwave_placement": side_1.get("upper_microwave_placement") or side_2.get("upper_microwave_placement"),
        "free_worktop_between_sink_and_hob_mm": free_worktop_between_sink_and_hob,
        "size_adjustments": size_adjustments,
        "warnings": warnings,
    }

    return layout

