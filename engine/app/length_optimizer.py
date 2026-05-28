from app.kitchen_constants import *
from app.kitchen_options import *
from app.lower_modules import *
from app.wall_modules import get_hood_width_for_hob


def copy_module_options(module_options: dict | None) -> dict:
    module_options = module_options or {}

    return {
        "room": dict(module_options.get("room", {})),
        "locked": dict(module_options.get("locked", {})),
        "required": {
            key: dict(value)
            for key, value in module_options.get("required", {}).items()
        },
        "optional": {
            key: dict(value)
            for key, value in module_options.get("optional", {}).items()
        },
    }


def get_or_create_required(options: dict, key: str) -> dict:
    required = options.setdefault("required", {})
    value = required.setdefault(key, {})

    return value


def get_or_create_optional(options: dict, key: str) -> dict:
    optional = options.setdefault("optional", {})
    value = optional.setdefault(key, {})

    return value


def prioritized_width_options(current_width: int, available_widths: list[int]) -> list[int]:
    widths = [width for width in available_widths if width <= current_width]

    if current_width not in widths:
        widths.append(current_width)

    return sorted(set(widths), reverse=True)


def preferred_width_options(
    current_width: int,
    available_widths: list[int],
    preferred_width: int = PREFERRED_DRAWER_WIDTH_MM,
) -> list[int]:
    widths = set(available_widths + [current_width, preferred_width])

    return sorted(
        widths,
        key=lambda width: (
            0 if width == preferred_width else 1,
            0 if width == current_width else 1,
            abs(width - preferred_width),
            -width,
        ),
    )


def other_first(current_value: str, values: list[str]) -> list[str]:
    ordered = [current_value]
    ordered.extend(value for value in values if value != current_value)

    return ordered


def get_allowed_oven_microwave_pairs(
    original_values: dict,
    locked: dict,
) -> list[tuple[str, str]]:
    valid_pairs = [
        ("under_counter", "solo"),
        ("under_counter", "upper_built_in"),
        ("column", "built_in"),
    ]
    current_pair = (
        original_values["oven.placement"],
        original_values["microwave.type"],
    )

    if locked.get("oven.placement") and locked.get("microwave.type"):
        return [current_pair]

    pairs = valid_pairs

    if locked.get("oven.placement"):
        pairs = [
            pair
            for pair in pairs
            if pair[0] == original_values["oven.placement"]
        ]

    if locked.get("microwave.type"):
        pairs = [
            pair
            for pair in pairs
            if pair[1] == original_values["microwave.type"]
        ]

    if not pairs:
        return [current_pair]

    preferred_pair = (
        ("column", "built_in")
        if original_values["oven.placement"] == "column"
        else ("under_counter", "upper_built_in")
    )

    return sorted(
        pairs,
        key=lambda pair: (
            0 if pair == preferred_pair else 1,
            0 if pair == current_pair else 1,
        ),
    )


def is_valid_oven_microwave_pair(oven_placement: str, microwave_type: str) -> bool:
    return (
        (oven_placement == "under_counter" and microwave_type == "solo")
        or (oven_placement == "under_counter" and microwave_type == "upper_built_in")
        or (oven_placement == "column" and microwave_type == "built_in")
    )


def has_unlocked_invalid_oven_microwave_pair(module_options: dict) -> bool:
    values = get_original_option_values(module_options)

    if is_valid_oven_microwave_pair(
        values["oven.placement"],
        values["microwave.type"],
    ):
        return False

    locked = get_locked_options(module_options)

    return not (
        locked.get("oven.placement")
        and locked.get("microwave.type")
    )


def get_original_option_values(module_options: dict) -> dict:
    required = module_options.get("required", {})
    optional = module_options.get("optional", {})

    oven = required.get("oven", {})
    sink = required.get("sink", {})
    hob = required.get("hob", {})
    microwave = required.get("microwave", {})
    dishwasher = optional.get("dishwasher", {})
    refrigerator = required.get("refrigerator", {})
    hood = required.get("hood", {})

    return {
        "refrigerator.mode": refrigerator.get("mode", "built_in"),
        "refrigerator.freestanding_installation": refrigerator.get(
            "freestanding_installation",
            "solo",
        ),
        "sink.width_mm": to_int(sink.get("width_mm"), 600),
        "hob.cabinet_width_mm": to_int(
            hob.get("cabinet_width_mm", hob.get("width_mm")),
            600,
        ),
        "hood.type": hood.get("type", "built_in"),
        "hood.width_mm": to_int(hood.get("width_mm"), 600),
        "dishwasher.width_mm": to_int(dishwasher.get("width_mm"), 600),
        "oven.placement": oven.get("placement", "under_counter"),
        "microwave.type": microwave.get("type", "solo"),
        "microwave.width_mm": to_int(microwave.get("width_mm"), 450),
        "microwave.height_mm": to_int(microwave.get("height_mm"), 250),
    }


def get_effective_option_values(module_options: dict) -> dict:
    return get_original_option_values(module_options)


def get_layout_effective_values(module_options: dict, layout: dict) -> dict:
    values = get_effective_option_values(module_options)

    for adjustment in layout.get("size_adjustments", []):
        field = adjustment.get("field")

        if field not in values:
            continue

        if "to_mm" in adjustment:
            values[field] = adjustment["to_mm"]
        elif "to_value" in adjustment:
            to_value = adjustment["to_value"]

            if field == "oven.placement":
                values[field] = "column" if "колон" in to_value else "under_counter"
            elif field == "microwave.type":
                if "навес" in to_value:
                    values[field] = "upper_built_in"
                else:
                    values[field] = "built_in" if "встра" in to_value else "solo"

            elif field == "refrigerator.freestanding_installation":
                values[field] = "in_cabinet" if "корпус" in to_value else "solo"

    return values


def format_option_value(field: str, value) -> str:
    labels = {
        "oven.placement": {
            "under_counter": "под столешницей",
            "column": "в колонне",
        },
        "microwave.type": {
            "built_in": "встраиваемая",
            "upper_built_in": "в навесном шкафу",
            "solo": "соло",
        },
        "refrigerator.mode": {
            "built_in": "встраиваемый",
            "freestanding": "отдельностоящий",
        },
        "refrigerator.freestanding_installation": {
            "in_cabinet": "в мебельном корпусе",
            "solo": "соло рядом с кухней",
        },
        "hood.type": {
            "built_in": "встроенная",
            "solo": "соло",
        },
        "room.wall_cabinets_enabled": {
            True: "включены",
            False: "выключены",
        },
        "room.mezzanine_enabled": {
            True: "\u0432\u043a\u043b\u044e\u0447\u0435\u043d\u044b",
            False: "\u0432\u044b\u043a\u043b\u044e\u0447\u0435\u043d\u044b",
        },
    }

    return labels.get(field, {}).get(value, str(value))


def upsert_layout_adjustment(
    layout: dict,
    field: str,
    label: str,
    original_value,
    final_value,
    reason: str,
) -> None:
    if original_value == final_value:
        return

    adjustments = layout.setdefault("size_adjustments", [])

    for adjustment in adjustments:
        if adjustment.get("field") != field:
            continue

        if isinstance(final_value, int):
            final_value = adjustment.get("to_mm", final_value)
            adjustment["from_mm"] = original_value
            adjustment["to_mm"] = final_value
        else:
            final_value = adjustment.get("to_value", format_option_value(field, final_value))
            adjustment["from_value"] = format_option_value(field, original_value)
            adjustment["to_value"] = format_option_value(field, final_value)

        adjustment["reason"] = reason
        return

    adjustment = {
        "field": field,
        "label": label,
        "reason": reason,
    }

    if isinstance(final_value, int):
        adjustment["from_mm"] = original_value
        adjustment["to_mm"] = final_value
    else:
        adjustment["from_value"] = format_option_value(field, original_value)
        adjustment["to_value"] = format_option_value(field, final_value)

    adjustments.append(adjustment)


def add_candidate_adjustments(
    layout: dict,
    original_options: dict,
    candidate_options: dict,
) -> None:
    original_values = get_original_option_values(original_options)
    effective_values = get_effective_option_values(candidate_options)
    locked = get_locked_options(original_options)

    specs = [
        ("refrigerator.mode", "Холодильник"),
        ("refrigerator.freestanding_installation", "Холодильник"),
        ("sink.width_mm", "Мойка"),
        ("hob.cabinet_width_mm", "Варочная поверхность"),
        ("hood.type", "Вытяжка"),
        ("hood.width_mm", "Вытяжка"),
        ("dishwasher.width_mm", "Посудомоечная машина"),
        ("oven.placement", "Духовка"),
        ("microwave.type", "Микроволновка"),
        ("microwave.width_mm", "Микроволновка"),
        ("microwave.height_mm", "Микроволновка"),
    ]

    for field, label in specs:
        if locked.get(field):
            continue

        upsert_layout_adjustment(
            layout=layout,
            field=field,
            label=label,
            original_value=original_values[field],
            final_value=effective_values[field],
            reason="kitchen_length_optimization",
        )


def build_length_optimization_candidates(module_options: dict) -> list[dict]:
    base_options = copy_module_options(module_options)
    required = base_options.get("required", {})
    optional = base_options.get("optional", {})
    locked = get_locked_options(base_options)

    original_values = get_original_option_values(base_options)
    dishwasher_enabled = bool(optional.get("dishwasher", {}).get("enabled"))

    sink_widths = (
        [original_values["sink.width_mm"]]
        if locked.get("sink.width_mm")
        else preferred_width_options(
            original_values["sink.width_mm"],
            SINK_WIDTH_OPTIONS,
        )
    )
    hob_widths = (
        [original_values["hob.cabinet_width_mm"]]
        if locked.get("hob.cabinet_width_mm")
        else preferred_width_options(
            original_values["hob.cabinet_width_mm"],
            HOB_WIDTH_OPTIONS,
        )
    )
    oven_microwave_pairs = get_allowed_oven_microwave_pairs(
        original_values=original_values,
        locked=locked,
    )
    refrigerator_modes = (
        [required.get("refrigerator", {}).get("mode", "built_in")]
        if locked.get("refrigerator.mode")
        else other_first("built_in", ["built_in", "freestanding"])
    )
    mezzanine_is_forced_on = (
        locked.get("room.mezzanine_enabled")
        and base_options.get("room", {}).get("mezzanine_enabled", True)
    )
    refrigerator_installation_should_stay_fixed = (
        locked.get("refrigerator.freestanding_installation")
        or (
            locked.get("refrigerator.mode")
            and original_values["refrigerator.mode"] == "freestanding"
            and not mezzanine_is_forced_on
        )
    )
    refrigerator_installations = (
        [original_values["refrigerator.freestanding_installation"]]
        if refrigerator_installation_should_stay_fixed
        else (
            ["in_cabinet"]
            if mezzanine_is_forced_on
            else other_first(
                original_values["refrigerator.freestanding_installation"],
                ["solo", "in_cabinet"],
            )
        )
    )
    hood_types = (
        [required.get("hood", {}).get("type", "built_in")]
        if locked.get("hood.type")
        else other_first("built_in", ["built_in", "solo"])
    )
    hood_widths = (
        [original_values["hood.width_mm"]]
        if locked.get("hood.width_mm")
        else sorted(
            {
                get_hood_width_for_hob(hob_width)
                for hob_width in hob_widths
            }
            | {original_values["hood.width_mm"]},
            key=lambda width: (
                0 if width == get_hood_width_for_hob(original_values["hob.cabinet_width_mm"]) else 1,
                width,
            ),
        )
    )
    if locked.get("dishwasher.width_mm") or not dishwasher_enabled:
        dishwasher_widths = [
            original_values["dishwasher.width_mm"],
        ]
    else:
        dishwasher_widths = preferred_width_options(
            original_values["dishwasher.width_mm"],
            [450, 600],
        )

    candidates = []

    for refrigerator_mode in refrigerator_modes:
        current_refrigerator_installations = (
            refrigerator_installations
            if refrigerator_mode == "freestanding"
            else [original_values["refrigerator.freestanding_installation"]]
        )

        for refrigerator_installation in current_refrigerator_installations:
            for sink_width in sink_widths:
                for hob_width in hob_widths:
                    for hood_type in hood_types:
                        for hood_width in hood_widths:
                            for oven_placement, microwave_type in oven_microwave_pairs:
                                for dishwasher_width in dishwasher_widths:
                                    candidate = copy_module_options(base_options)
                                    candidate_refrigerator = get_or_create_required(candidate, "refrigerator")
                                    candidate_refrigerator["mode"] = refrigerator_mode
                                    candidate_refrigerator["freestanding_installation"] = refrigerator_installation
                                    get_or_create_required(candidate, "sink")["width_mm"] = sink_width
                                    get_or_create_required(candidate, "hob")["cabinet_width_mm"] = hob_width
                                    get_or_create_required(candidate, "hood")["type"] = hood_type
                                    get_or_create_required(candidate, "oven")["placement"] = oven_placement
                                    candidate_hood_width = (
                                        hood_width
                                        if locked.get("hood.width_mm")
                                        else get_hood_width_for_hob(hob_width)
                                    )
                                    get_or_create_required(candidate, "hood")["width_mm"] = candidate_hood_width

                                    candidate_microwave = get_or_create_required(candidate, "microwave")
                                    candidate_microwave["type"] = microwave_type

                                    if microwave_type in {"built_in", "upper_built_in"}:
                                        candidate_microwave["width_mm"] = 600
                                        candidate_microwave["height_mm"] = (
                                            original_values["microwave.height_mm"]
                                            if original_values["microwave.type"] in {"built_in", "upper_built_in"}
                                            else 400
                                        )
                                    else:
                                        if original_values["microwave.type"] == "solo":
                                            candidate_microwave["width_mm"] = original_values["microwave.width_mm"]
                                            candidate_microwave["height_mm"] = original_values["microwave.height_mm"]
                                        else:
                                            candidate_microwave["width_mm"] = 450
                                            candidate_microwave["height_mm"] = 250

                                    if dishwasher_enabled:
                                        get_or_create_optional(candidate, "dishwasher")["width_mm"] = dishwasher_width

                                    candidates.append(candidate)

    return candidates


def layout_has_blocking_placement_issue(layout: dict, module_options: dict | None = None) -> bool:
    module_options = module_options or {}
    microwave_type = (
        module_options
        .get("required", {})
        .get("microwave", {})
        .get("type", "solo")
    )

    if layout.get("hob_placement") is None:
        return True

    if microwave_type == "solo":
        return layout.get("solo_microwave_placement") is None

    if microwave_type == "upper_built_in":
        return layout.get("upper_microwave_placement") is None

    return False


def count_steps_between(widths: list[int], from_width: int, to_width: int) -> int:
    ordered = sorted(set(widths))

    if from_width not in ordered or to_width not in ordered:
        return 0

    return abs(ordered.index(from_width) - ordered.index(to_width))


def count_width_reduction_to_floor(
    original_width: int,
    final_width: int,
    floor_width: int,
    widths: list[int],
) -> int:
    if final_width >= original_width:
        return 0

    upper = original_width
    lower = max(final_width, floor_width)

    if lower >= upper:
        return 0

    return count_steps_between(widths, upper, lower)


def count_width_reduction_below_floor(
    original_width: int,
    final_width: int,
    floor_width: int,
    widths: list[int],
) -> int:
    if final_width >= floor_width or original_width <= floor_width:
        return 0

    upper = min(original_width, floor_width)
    lower = final_width

    if lower >= upper:
        return 0

    return count_steps_between(widths, upper, lower)


def variation_optimization_cost(original: dict, candidate: dict) -> int:
    if (
        original["oven.placement"] == candidate["oven.placement"]
        and original["microwave.type"] == candidate["microwave.type"]
    ):
        return 0

    preferred_compact_variants = {
        ("column", "built_in"),
        ("under_counter", "upper_built_in"),
        ("under_counter", "solo"),
    }
    candidate_pair = (
        candidate["oven.placement"],
        candidate["microwave.type"],
    )

    if candidate_pair == ("column", "built_in"):
        return 1

    if candidate_pair == ("under_counter", "upper_built_in"):
        return 2

    if candidate_pair == ("under_counter", "solo"):
        return 3

    return 99


def count_optimization_changes(
    original_options: dict,
    candidate_options: dict,
    layout: dict,
) -> tuple[tuple[int, int, int, int, int, int, int], int, int]:
    original = get_original_option_values(original_options)
    candidate = get_layout_effective_values(candidate_options, layout)
    locked = get_locked_options(original_options)

    sink_to_600_steps = count_width_reduction_to_floor(
        original["sink.width_mm"],
        candidate["sink.width_mm"],
        PREFERRED_DRAWER_WIDTH_MM,
        SINK_WIDTH_OPTIONS,
    )
    hob_to_600_steps = count_width_reduction_to_floor(
        original["hob.cabinet_width_mm"],
        candidate["hob.cabinet_width_mm"],
        PREFERRED_DRAWER_WIDTH_MM,
        HOB_WIDTH_OPTIONS,
    )
    variation_steps = variation_optimization_cost(original, candidate)
    dishwasher_changed = original["dishwasher.width_mm"] != candidate["dishwasher.width_mm"]
    sink_below_600_steps = count_width_reduction_below_floor(
        original["sink.width_mm"],
        candidate["sink.width_mm"],
        PREFERRED_DRAWER_WIDTH_MM,
        SINK_WIDTH_OPTIONS,
    )
    hob_below_600_steps = count_width_reduction_below_floor(
        original["hob.cabinet_width_mm"],
        candidate["hob.cabinet_width_mm"],
        PREFERRED_DRAWER_WIDTH_MM,
        HOB_WIDTH_OPTIONS,
    )

    priority_steps = (
        sink_to_600_steps,
        hob_to_600_steps,
        variation_steps,
        int(dishwasher_changed),
        sink_below_600_steps,
        hob_below_600_steps,
    )
    highest_used_stage = 0

    for index, value in enumerate(priority_steps, start=1):
        if value > 0:
            highest_used_stage = index

    priority_key = (
        highest_used_stage,
        *priority_steps,
    )
    default_deviation = 0

    for field, preferred_value in AUTO_PREFERRED_VALUES.items():
        if locked.get(field):
            continue

        if candidate.get(field) != preferred_value:
            default_deviation += 1

    change_count = (
        sink_to_600_steps
        + hob_to_600_steps
        + variation_steps
        + int(dishwasher_changed)
        + sink_below_600_steps
        + hob_below_600_steps
    )

    return priority_key, change_count, default_deviation


def score_length_candidate(
    layout: dict,
    original_options: dict,
    candidate_options: dict,
) -> tuple:
    remaining_width = layout.get("remaining_width_mm", 0)
    overflow = max(0, -remaining_width)
    leftover = max(0, remaining_width)
    candidate_values = get_layout_effective_values(candidate_options, layout)
    relation_penalty = (
        0
        if is_valid_oven_microwave_pair(
            candidate_values["oven.placement"],
            candidate_values["microwave.type"],
        )
        else 1
    )
    placement_penalty = (
        1
        if layout_has_blocking_placement_issue(layout, candidate_options)
        else 0
    )
    priority_key, change_count, default_deviation = count_optimization_changes(
        original_options,
        candidate_options,
        layout,
    )

    return (
        relation_penalty,
        placement_penalty,
        0 if overflow == 0 else 1,
        overflow if overflow > 0 else 0,
        default_deviation,
        priority_key[0],
        priority_key[1:],
        leftover,
        change_count,
        layout.get("used_width_mm", 0),
    )


def layout_has_forced_length_adjustment(layout: dict) -> bool:
    forced_reasons = {
        "cooking_zone_minimum",
        "mandatory_450_lower_drawer",
        "kitchen_length_optimization",
    }

    return any(
        adjustment.get("reason") in forced_reasons
        for adjustment in layout.get("size_adjustments", [])
    )


def has_unlocked_auto_preferred_difference(module_options: dict) -> bool:
    values = get_original_option_values(module_options)
    locked = get_locked_options(module_options)
    preferred_values = dict(AUTO_PREFERRED_VALUES)

    if values.get("oven.placement") == "column":
        preferred_values["oven.placement"] = "column"
        preferred_values["microwave.type"] = "built_in"
        preferred_values["microwave.width_mm"] = 600
        preferred_values["microwave.height_mm"] = 400

    return any(
        not locked.get(field) and values.get(field) != preferred_value
        for field, preferred_value in preferred_values.items()
        if field in values
    )


