from app.kitchen_constants import (
    DISHDRAINER_WIDTH_OPTIONS,
    DISH_DRYING_MAX_WIDTH_MM,
    DISH_DRYING_MIN_WIDTH_MM,
    DRAWER_WIDTH_STEP_MM,
    UPPER_CABINET_TARGET_WIDTH_MM,
    UPPER_CABINET_WIDTH_OPTIONS,
    WALL_CABINET_BOTTOM_MM,
    WALL_CABINET_DEPTH_MM,
)


def get_hood_width_for_hob(hob_width: int) -> int:
    if hob_width == 300:
        return 600

    if hob_width in {800, 900}:
        return 900

    return 600


def split_upper_cabinet_width(width_mm: int) -> list[int]:
    if width_mm <= 0 or width_mm % 50 != 0:
        return []

    if width_mm < min(UPPER_CABINET_WIDTH_OPTIONS):
        return []

    candidates = []
    min_count = (width_mm + max(UPPER_CABINET_WIDTH_OPTIONS) - 1) // max(
        UPPER_CABINET_WIDTH_OPTIONS
    )
    max_count = width_mm // min(UPPER_CABINET_WIDTH_OPTIONS)

    def collect_parts(
        remaining_width: int,
        remaining_count: int,
        min_option_index: int,
        parts: list[int],
    ) -> None:
        if remaining_count == 0:
            if remaining_width == 0:
                candidates.append(sorted(parts, reverse=True))
            return

        if remaining_width < remaining_count * min(UPPER_CABINET_WIDTH_OPTIONS):
            return

        if remaining_width > remaining_count * max(UPPER_CABINET_WIDTH_OPTIONS):
            return

        for index in range(min_option_index, len(UPPER_CABINET_WIDTH_OPTIONS)):
            option = UPPER_CABINET_WIDTH_OPTIONS[index]

            if option > remaining_width:
                break

            collect_parts(
                remaining_width - option,
                remaining_count - 1,
                index,
                parts + [option],
            )

    for count in range(min_count, max_count + 1):
        average_width = width_mm / count

        if (
            average_width < min(UPPER_CABINET_WIDTH_OPTIONS)
            or average_width > max(UPPER_CABINET_WIDTH_OPTIONS)
        ):
            continue

        collect_parts(width_mm, count, 0, [])

    if not candidates:
        return []

    return min(candidates, key=upper_cabinet_split_score)


def upper_cabinet_split_score(parts: list[int]) -> tuple:
    counts = [parts.count(width) for width in UPPER_CABINET_WIDTH_OPTIONS]
    average_width = sum(parts) / len(parts)
    spread = max(parts) - min(parts)
    max_same_width_count = max(counts)
    repeated_300_bonus = parts.count(300) if max_same_width_count > 1 else 0

    return (
        abs(average_width - UPPER_CABINET_TARGET_WIDTH_MM),
        len(set(parts)),
        -max_same_width_count,
        -repeated_300_bonus,
        spread,
        sum(abs(width - UPPER_CABINET_TARGET_WIDTH_MM) for width in parts),
        len(parts),
        -sum(parts),
    )


def merge_ranges(ranges: list[tuple[int, int]]) -> list[list[int]]:
    merged_ranges = []

    for x_mm, width_mm in sorted(ranges):
        if width_mm <= 0:
            continue

        if not merged_ranges:
            merged_ranges.append([x_mm, x_mm + width_mm])
            continue

        previous = merged_ranges[-1]

        if x_mm <= previous[1]:
            previous[1] = max(previous[1], x_mm + width_mm)
        else:
            merged_ranges.append([x_mm, x_mm + width_mm])

    return merged_ranges


def split_upper_cabinet_range_width(width_mm: int) -> tuple[list[int], int]:
    segment_widths = split_upper_cabinet_width(width_mm)

    if segment_widths:
        return segment_widths, 0

    rounded_width = width_mm - (width_mm % DRAWER_WIDTH_STEP_MM)
    segment_widths = split_upper_cabinet_width(rounded_width)

    if segment_widths:
        return segment_widths, width_mm - rounded_width

    return [], width_mm


def score_upper_cabinet_ranges(ranges: list[tuple[int, int]]) -> tuple:
    merged_ranges = merge_ranges(ranges)
    all_segment_widths = []
    overflow_width = 0
    unsplit_width = 0

    for start, end in merged_ranges:
        segment_widths, overflow = split_upper_cabinet_range_width(end - start)

        if not segment_widths:
            unsplit_width += end - start
            continue

        all_segment_widths.extend(segment_widths)
        overflow_width += overflow

    if not all_segment_widths:
        return (1, unsplit_width, overflow_width, 999, 999, 999, 999, 999)

    counts = [
        all_segment_widths.count(width)
        for width in UPPER_CABINET_WIDTH_OPTIONS
    ]
    spread = max(all_segment_widths) - min(all_segment_widths)

    return (
        0,
        unsplit_width,
        overflow_width,
        len(set(all_segment_widths)),
        -max(counts),
        spread,
        sum(
            abs(width - UPPER_CABINET_TARGET_WIDTH_MM)
            for width in all_segment_widths
        ),
        len(all_segment_widths),
    )


def _subtract_ranges(
    ranges: list[tuple[int, int]],
    blocked_ranges: list[tuple[int, int]],
) -> list[tuple[int, int]]:
    visible_ranges = ranges

    for blocked_start, blocked_width in blocked_ranges:
        if blocked_width <= 0:
            continue

        blocked_end = blocked_start + blocked_width
        next_ranges = []

        for start, width in visible_ranges:
            end = start + width

            if end <= blocked_start or start >= blocked_end:
                next_ranges.append((start, width))
                continue

            if start < blocked_start:
                next_ranges.append((start, blocked_start - start))

            if end > blocked_end:
                next_ranges.append((blocked_end, end - blocked_end))

        visible_ranges = next_ranges

    return [(start, width) for start, width in visible_ranges if width > 0]


def _intersect_ranges(
    ranges: list[tuple[int, int]],
    start_mm: int,
    end_mm: int,
) -> list[tuple[int, int]]:
    intersections = []

    for start, width in ranges:
        end = start + width
        intersection_start = max(start, start_mm)
        intersection_end = min(end, end_mm)

        if intersection_end > intersection_start:
            intersections.append(
                (intersection_start, intersection_end - intersection_start)
            )

    return intersections


def _range_split_overflow(ranges: list[tuple[int, int]]) -> int:
    return score_upper_cabinet_ranges(ranges)[2]


def _split_standard_upper_range(width_mm: int) -> list[int]:
    segment_widths, overflow = split_upper_cabinet_range_width(width_mm)

    if overflow:
        return []

    return segment_widths


def split_lift_upper_cabinet_width(width_mm: int) -> list[int]:
    if width_mm <= 0:
        return []

    min_width = 500
    max_width = 1200
    target_width = 600

    if width_mm < min_width:
        return [width_mm]

    min_count = max(1, (width_mm + max_width - 1) // max_width)
    max_count = max(1, width_mm // min_width)

    if max_count < min_count:
        return [width_mm]

    count = min(
        range(min_count, max_count + 1),
        key=lambda item: (
            abs(width_mm / item - target_width),
            item,
        ),
    )
    base_width = (width_mm // count) // DRAWER_WIDTH_STEP_MM * DRAWER_WIDTH_STEP_MM
    widths = [base_width for _ in range(count)]
    remainder = width_mm - sum(widths)
    index = 0

    while remainder >= DRAWER_WIDTH_STEP_MM and widths:
        widths[index % len(widths)] += DRAWER_WIDTH_STEP_MM
        remainder -= DRAWER_WIDTH_STEP_MM
        index += 1

    if remainder > 0 and widths:
        widths[-1] += remainder

    return widths


def build_wall_modules(
    *,
    modules: list[dict],
    wall_length_mm: int,
    kitchen_height_mm: int,
    wall_cabinet_bottom_mm: int,
    wall_cabinets_enabled: bool,
    mezzanine_enabled: bool,
    cooking_module: dict | None,
    hob_width: int,
    hob_placement: dict | None,
    hood_width: int,
    sink_module: dict | None,
    microwave_type: str = "solo",
    upper_built_in_microwave_present: bool = False,
    blocked_wall_ranges: list[tuple[int, int]] | None = None,
    ceiling_filler_height_mm: int = 0,
    upper_cabinet_opening: str = "hinged",
) -> list[dict]:
    if not wall_cabinets_enabled:
        return []

    ceiling_filler_height = max(0, int(ceiling_filler_height_mm or 0))
    cabinet_top_mm = max(wall_cabinet_bottom_mm, kitchen_height_mm - ceiling_filler_height)
    upper_zone_height = max(0, cabinet_top_mm - wall_cabinet_bottom_mm)

    if upper_zone_height <= 0:
        return []

    upper_opening = "lift" if upper_cabinet_opening == "lift" else "hinged"

    if (
        upper_opening == "lift"
        and mezzanine_enabled
        and (microwave_type == "upper_built_in" or upper_built_in_microwave_present)
        and upper_zone_height >= 800
    ):
        wall_cabinet_height = 800
        mezzanine_height = upper_zone_height - wall_cabinet_height
    elif mezzanine_enabled:
        wall_cabinet_height = int(round(upper_zone_height * 2 / 3))
        mezzanine_height = upper_zone_height - wall_cabinet_height
    else:
        wall_cabinet_height = upper_zone_height
        mezzanine_height = 0

    mezzanine_y = wall_cabinet_bottom_mm + wall_cabinet_height
    wall_modules = []

    def add_wall_segment(
        name: str,
        x_mm: int,
        width_mm: int,
        *,
        tier: str = "upper",
        extra: dict | None = None,
    ) -> None:
        if width_mm <= 0:
            return

        extra = extra or {}
        wall_modules.append(
            {
                "type": "wall",
                "name": name,
                "width_mm": width_mm,
                "height_mm": wall_cabinet_height,
                "x_mm": x_mm,
                "y_mm": wall_cabinet_bottom_mm,
                "depth_mm": WALL_CABINET_DEPTH_MM,
                "tier": tier,
                **extra,
            }
        )

        if mezzanine_height > 0:
            wall_modules.append(
                {
                    "type": "wall",
                    "name": "mezzanine_drawer",
                    "width_mm": width_mm,
                    "height_mm": mezzanine_height,
                    "x_mm": x_mm,
                    "y_mm": mezzanine_y,
                    "depth_mm": WALL_CABINET_DEPTH_MM,
                    "tier": "mezzanine",
                }
            )

    base_ranges = [
        (start, end - start)
        for start, end in merge_ranges(
            [
                (module["x_mm"], module["width_mm"])
                for module in modules
                if module.get("type") == "base"
            ]
        )
    ]
    base_ranges = _subtract_ranges(base_ranges, blocked_wall_ranges or [])

    if not base_ranges:
        return []

    def clamp_hood_start_to_base_ranges(candidate_x: int) -> list[int]:
        clamped = []

        for start, width in base_ranges:
            if width < hood_width:
                continue

            clamped.append(max(start, min(candidate_x, start + width - hood_width)))

        if clamped:
            return clamped

        return [max(0, min(candidate_x, wall_length_mm - hood_width))]

    hood_range = None

    if cooking_module:
        hob_x = (
            int(hob_placement["x_mm"])
            if hob_placement and hob_placement.get("x_mm") is not None
            else int(cooking_module["x_mm"] + cooking_module["width_mm"] / 2 - hob_width / 2)
        )
        hob_center = hob_x + hob_width / 2
        centered_hood_x = int(round(hob_center - hood_width / 2))
        hood_candidate_set = set()

        for candidate_x in clamp_hood_start_to_base_ranges(centered_hood_x):
            hood_candidate_set.add(candidate_x)

        for offset in range(
            -100,
            101,
            DRAWER_WIDTH_STEP_MM,
        ):
            for candidate_x in clamp_hood_start_to_base_ranges(centered_hood_x + offset):
                hood_candidate_set.add(candidate_x)

        for module in modules:
            if module.get("type") != "base":
                continue

            for candidate_x in (
                module["x_mm"],
                module["x_mm"] + module["width_mm"] - hood_width,
                module["x_mm"] - hood_width,
                module["x_mm"] + module["width_mm"],
            ):
                for clamped_x in clamp_hood_start_to_base_ranges(int(candidate_x)):
                    hood_candidate_set.add(clamped_x)

        if not hood_candidate_set:
            hood_candidate_set.add(max(0, min(centered_hood_x, wall_length_mm - hood_width)))

        def score_hood_position(candidate_x: int) -> tuple:
            visible_ranges = _subtract_ranges(
                base_ranges,
                [(candidate_x, hood_width)],
            )
            upper_score = score_upper_cabinet_ranges(visible_ranges)

            return (
                upper_score[0],
                upper_score[1],
                upper_score[2],
                abs(candidate_x - centered_hood_x),
                upper_score[3:],
            )

        hood_start = min(hood_candidate_set, key=score_hood_position)
        hood_range = (hood_start, hood_width)

    visible_ranges = _subtract_ranges(base_ranges, [hood_range] if hood_range else [])
    dish_range = None

    if sink_module:
        sink_start = sink_module["x_mm"]
        sink_end = sink_start + sink_module["width_mm"]
        sink_center = sink_start + sink_module["width_mm"] / 2
        sink_visible_ranges = _intersect_ranges(visible_ranges, sink_start, sink_end)
        target_dish_width = get_dish_drying_cabinet_width(sink_module["width_mm"])
        dish_candidates = []

        for visible_start, visible_width in sink_visible_ranges:
            for width_mm in sorted(DISHDRAINER_WIDTH_OPTIONS, reverse=True):
                if width_mm > visible_width:
                    continue

                centered_x = int(round(sink_center - width_mm / 2))
                x_mm = max(visible_start, min(centered_x, visible_start + visible_width - width_mm))
                left_width = x_mm - visible_start
                right_width = visible_start + visible_width - (x_mm + width_mm)
                score = (
                    _range_split_overflow([(visible_start, left_width), (x_mm + width_mm, right_width)]),
                    abs((x_mm + width_mm / 2) - sink_center),
                    abs(width_mm - target_dish_width),
                    -width_mm,
                )
                dish_candidates.append((score, (x_mm, width_mm)))

        if dish_candidates:
            dish_range = min(dish_candidates, key=lambda item: item[0])[1]

    reserved_ranges = [hood_range] if hood_range else []

    if dish_range:
        reserved_ranges.append(dish_range)
        add_wall_segment(
            "dish_drying_cabinet",
            dish_range[0],
            dish_range[1],
        )

    microwave_range = None

    if microwave_type == "upper_built_in":
        microwave_width = 600
        sink_center = (
            sink_module["x_mm"] + sink_module["width_mm"] / 2
            if sink_module
            else None
        )
        microwave_candidates = []

        for visible_start, visible_width in _subtract_ranges(
            base_ranges,
            reserved_ranges,
        ):
            if visible_width < microwave_width:
                continue

            visible_end = visible_start + visible_width
            candidate_starts = {
                visible_start,
                visible_end - microwave_width,
            }

            if sink_center is not None:
                candidate_starts.add(
                    max(
                        visible_start,
                        min(
                            int(round(sink_center - microwave_width / 2)),
                            visible_end - microwave_width,
                        ),
                    )
                )

            first_step_x = (
                (visible_start + DRAWER_WIDTH_STEP_MM - 1)
                // DRAWER_WIDTH_STEP_MM
                * DRAWER_WIDTH_STEP_MM
            )
            for x_mm in range(
                first_step_x,
                visible_end - microwave_width + 1,
                DRAWER_WIDTH_STEP_MM,
            ):
                candidate_starts.add(x_mm)

            for x_mm in candidate_starts:
                if x_mm < visible_start or x_mm + microwave_width > visible_end:
                    continue

                remaining_ranges = _subtract_ranges(
                    [(visible_start, visible_width)],
                    [(x_mm, microwave_width)],
                )
                split_score = score_upper_cabinet_ranges(remaining_ranges)
                microwave_center = x_mm + microwave_width / 2
                sink_distance = (
                    abs(microwave_center - sink_center)
                    if sink_center is not None
                    else 0
                )
                microwave_candidates.append(
                    (
                        (
                            split_score[0],
                            split_score[1],
                            split_score[2],
                            sink_distance,
                            abs(x_mm - visible_start),
                        ),
                        (x_mm, microwave_width),
                    )
                )

        if microwave_candidates:
            microwave_range = min(microwave_candidates, key=lambda item: item[0])[1]
            reserved_ranges.append(microwave_range)
            add_wall_segment(
                "upper_cabinet",
                microwave_range[0],
                microwave_range[1],
                extra={"reserved_for": "built_in_microwave"},
            )

    for start, width in _subtract_ranges(base_ranges, reserved_ranges):
        segment_widths = (
            split_lift_upper_cabinet_width(width)
            if upper_opening == "lift"
            else _split_standard_upper_range(width)
        )

        if not segment_widths:
            continue

        current_x = start

        for segment_width in segment_widths:
            add_wall_segment("upper_cabinet", current_x, segment_width)
            current_x += segment_width

    if hood_range:
        add_wall_segment(
            "built_in_hood",
            hood_range[0],
            hood_range[1],
            tier="hood",
        )

    if ceiling_filler_height > 0:
        ceiling_source_ranges = [
            (module.get("x_mm", 0), module.get("width_mm", 0))
            for module in modules
            if module.get("type") != "freestanding_solo"
        ]
        ceiling_source_ranges.extend(
            [
                (module.get("x_mm", 0), module.get("width_mm", 0))
                for module in wall_modules
                if module.get("tier") != "ceiling_filler"
            ]
        )
        ceiling_source_ranges = [
            (x_mm, width_mm)
            for x_mm, width_mm in ceiling_source_ranges
            if width_mm > 0
        ]

        if not ceiling_source_ranges:
            return wall_modules

        ceiling_filler_x = min(x_mm for x_mm, _width_mm in ceiling_source_ranges)
        ceiling_filler_end = max(
            x_mm + width_mm for x_mm, width_mm in ceiling_source_ranges
        )
        wall_modules.append(
            {
                "type": "wall",
                "name": "ceiling_filler",
                "width_mm": ceiling_filler_end - ceiling_filler_x,
                "height_mm": ceiling_filler_height,
                "x_mm": ceiling_filler_x,
                "y_mm": cabinet_top_mm,
                "depth_mm": WALL_CABINET_DEPTH_MM,
                "tier": "ceiling_filler",
            }
        )

    return wall_modules


def apply_wall_facade_grouping(
    wall_modules: list[dict],
    upper_cabinet_opening: str = "hinged",
) -> list[dict]:
    if not wall_modules:
        return wall_modules

    upper_modules = [
        module
        for module in wall_modules
        if module.get("tier") in {"upper", "hood"}
    ]
    passthrough_modules = [
        module
        for module in wall_modules
        if module.get("tier") not in {"upper", "hood", "mezzanine"}
    ]
    mezzanine_template = next(
        (
            module
            for module in wall_modules
            if module.get("tier") == "mezzanine"
        ),
        None,
    )
    grouped_modules = []
    upper_opening = "lift" if upper_cabinet_opening == "lift" else "hinged"

    def can_pair_hinged_upper_cabinets(previous: dict, current: dict) -> bool:
        if previous.get("name") != "upper_cabinet" or current.get("name") != "upper_cabinet":
            return False
        if previous.get("reserved_for") or current.get("reserved_for"):
            return False
        if previous.get("facade_door_widths_mm"):
            return False
        if previous.get("y_mm") != current.get("y_mm"):
            return False
        if previous.get("height_mm") != current.get("height_mm"):
            return False
        if previous.get("x_mm", 0) + previous.get("width_mm", 0) != current.get("x_mm"):
            return False

        previous_width = previous.get("width_mm", 0)
        current_width = current.get("width_mm", 0)
        total_width = previous_width + current_width

        if previous_width == current_width:
            return True

        return (
            previous_width <= 450
            and current_width <= 450
            and total_width <= 900
        )

    def can_merge_lift_upper_module(previous: dict, current: dict) -> bool:
        if previous.get("tier") != "upper" or current.get("tier") != "upper":
            return False
        mergeable_names = {"upper_cabinet", "dish_drying_cabinet"}
        if previous.get("name") not in mergeable_names or current.get("name") not in mergeable_names:
            return False
        if previous.get("name") != "upper_cabinet" and current.get("name") != "upper_cabinet":
            return False
        if previous.get("reserved_for") or current.get("reserved_for"):
            return False
        if previous.get("y_mm") != current.get("y_mm"):
            return False
        if previous.get("height_mm") != current.get("height_mm"):
            return False
        if previous.get("x_mm", 0) + previous.get("width_mm", 0) != current.get("x_mm"):
            return False

        previous_width = int(previous.get("width_mm", 0))
        current_width = int(current.get("width_mm", 0))
        return (
            min(previous_width, current_width) < 500
            and previous_width + current_width <= 1200
        )

    def normalize_lift_upper_modules(modules: list[dict]) -> list[dict]:
        result = sorted(modules, key=lambda item: (item.get("y_mm", 0), item.get("x_mm", 0)))
        index = 0

        while index < len(result):
            module = result[index]
            if (
                module.get("tier") != "upper"
                or module.get("name") != "upper_cabinet"
                or module.get("reserved_for")
                or int(module.get("width_mm", 0)) >= 500
            ):
                index += 1
                continue

            merge_index = None
            if index > 0 and can_merge_lift_upper_module(result[index - 1], module):
                merge_index = index - 1
            if (
                merge_index is None
                and index + 1 < len(result)
                and can_merge_lift_upper_module(module, result[index + 1])
            ):
                merge_index = index + 1

            if merge_index is not None:
                target = result[merge_index]
                new_start = min(target.get("x_mm", 0), module.get("x_mm", 0))
                new_end = max(
                    target.get("x_mm", 0) + target.get("width_mm", 0),
                    module.get("x_mm", 0) + module.get("width_mm", 0),
                )
                target["x_mm"] = new_start
                target["width_mm"] = new_end - new_start
                if module.get("name") != "upper_cabinet":
                    target["name"] = module["name"]
                target["facade_opening"] = "lift_fold"
                target["facade_door_count"] = 1
                target.pop("facade_door_widths_mm", None)
                result.pop(index)
                if merge_index > index:
                    index = max(0, index - 1)
                else:
                    index = max(0, merge_index - 1)
                continue

            module.pop("facade_opening", None)
            module["facade_door_count"] = 1
            index += 1

        return result

    for module in sorted(
        upper_modules,
        key=lambda item: (item.get("y_mm", 0), item.get("x_mm", 0)),
    ):
        module = {**module}

        if upper_opening == "lift":
            if grouped_modules and can_merge_lift_upper_module(grouped_modules[-1], module):
                grouped_modules[-1]["width_mm"] += module["width_mm"]
                if module.get("name") != "upper_cabinet":
                    grouped_modules[-1]["name"] = module["name"]
                grouped_modules[-1]["facade_opening"] = "lift_fold"
                grouped_modules[-1]["facade_door_count"] = 1
                continue

            module["facade_opening"] = "lift_fold"
            module["facade_door_count"] = 1
            grouped_modules.append(module)
            continue

        if grouped_modules and can_pair_hinged_upper_cabinets(grouped_modules[-1], module):
            previous = grouped_modules[-1]
            door_width = previous["width_mm"]
            previous["width_mm"] += module["width_mm"]
            previous["facade_door_widths_mm"] = [door_width, module["width_mm"]]
            previous["facade_door_count"] = 2
            continue

        if module.get("name") == "built_in_hood":
            half_width = module["width_mm"] / 2
            module["facade_door_widths_mm"] = [half_width, half_width]
            module["facade_door_count"] = 2
        elif module.get("name") == "dish_drying_cabinet":
            if module["width_mm"] >= 600:
                half_width = module["width_mm"] / 2
                module["facade_door_widths_mm"] = [half_width, half_width]
                module["facade_door_count"] = 2
            else:
                module["facade_door_count"] = 1
        elif module.get("name") == "upper_cabinet":
            module["facade_door_count"] = 1

        grouped_modules.append(module)

    if upper_opening == "lift":
        grouped_modules = normalize_lift_upper_modules(grouped_modules)

    if mezzanine_template is None:
        return grouped_modules + passthrough_modules

    mezzanine_modules = []

    for module in grouped_modules:
        if module.get("tier") not in {"upper", "hood"}:
            continue

        mezzanine_modules.append(
            {
                "type": "wall",
                "name": "mezzanine_drawer",
                "width_mm": module["width_mm"],
                "height_mm": mezzanine_template["height_mm"],
                "x_mm": module["x_mm"],
                "y_mm": mezzanine_template["y_mm"],
                "depth_mm": mezzanine_template.get(
                    "depth_mm",
                    WALL_CABINET_DEPTH_MM,
                ),
                "tier": "mezzanine",
                "facade_door_count": 1,
            }
        )

    result = []

    for module in grouped_modules:
        result.append(module)

    result.extend(mezzanine_modules)
    result.extend(passthrough_modules)

    return result


def place_upper_built_in_microwave(
    wall_modules: list[dict],
    microwave: dict,
    warnings: list[str],
    sink_module: dict | None = None,
) -> dict | None:
    microwave_width = 600
    microwave_height = 400
    candidates = [
        module
        for module in wall_modules
        if module.get("name") == "upper_cabinet"
        and module.get("tier") == "upper"
        and module.get("reserved_for") == "built_in_microwave"
        and module.get("width_mm", 0) >= microwave_width
    ]

    if not candidates:
        warnings.append(
            "Встраиваемую микроволновку 600 мм не удалось разместить в нижней части навесных шкафов: нет подходящего upper cabinet."
        )
        return None

    sink_center = (
        sink_module["x_mm"] + sink_module["width_mm"] / 2
        if sink_module
        else None
    )

    def microwave_candidate_score(module: dict) -> tuple:
        module_center = module["x_mm"] + module["width_mm"] / 2
        sink_distance = (
            abs(module_center - sink_center)
            if sink_center is not None
            else 0
        )

        return (
            sink_distance,
            abs(module["width_mm"] - microwave_width),
            -module["width_mm"],
            module["x_mm"],
        )

    selected_module = min(
        candidates,
        key=microwave_candidate_score,
    )
    x_mm = selected_module["x_mm"] + int(
        (selected_module["width_mm"] - microwave_width) / 2
    )
    y_mm = int(selected_module.get("y_mm", WALL_CABINET_BOTTOM_MM))

    wall_modules.append(
        {
            "type": "wall",
            "name": "built_in_microwave",
            "width_mm": microwave_width,
            "height_mm": microwave_height,
            "x_mm": x_mm,
            "y_mm": y_mm,
            "depth_mm": WALL_CABINET_DEPTH_MM,
            "tier": "microwave",
            "on_module": "upper_cabinet",
            "parent_module_x_mm": selected_module["x_mm"],
            "parent_module_width_mm": selected_module["width_mm"],
        }
    )

    return {
        "placed": True,
        "on_module": "upper_cabinet",
        "x_mm": x_mm,
        "parent_module_x_mm": selected_module["x_mm"],
        "parent_module_width_mm": selected_module["width_mm"],
    }


def get_dish_drying_cabinet_width(sink_width: int) -> int:
    if sink_width >= DISH_DRYING_MAX_WIDTH_MM:
        return DISH_DRYING_MAX_WIDTH_MM

    return min(
        DISHDRAINER_WIDTH_OPTIONS,
        key=lambda width: (
            0 if width >= sink_width else 1,
            abs(width - sink_width),
            width,
        ),
    )

