from app.kitchen_constants import *
from app.kitchen_options import *


def is_blocked_worktop_module(module: dict) -> bool:
    return module["name"] in {
        "sink",
    }


def can_support_solo_microwave(module: dict, microwave_width: int) -> bool:
    if module["type"] != "base":
        return False

    if is_blocked_worktop_module(module):
        return False

    if module.get("countertop_occupied_by"):
        return False

    return module["width_mm"] >= microwave_width


def mark_countertop_role(module: dict) -> dict:
    if module["type"] in {"tall", "freestanding_solo", "appliance_tall"}:
        module["countertop_role"] = "none"
        module["countertop_free_mm"] = 0
        return module

    if is_blocked_worktop_module(module):
        module["countertop_role"] = "blocked"
        module["countertop_free_mm"] = 0
        return module

    if module["type"] == "base":
        module["countertop_role"] = "free_worktop"
        module["countertop_free_mm"] = module["width_mm"]
        return module

    module["countertop_role"] = "none"
    module["countertop_free_mm"] = 0
    return module


def get_sink_and_cooking_indices(modules: list[dict]) -> tuple[int | None, int | None]:
    sink_index = None
    cooking_index = None

    for index, module in enumerate(modules):
        if module["name"] == "sink":
            sink_index = index

        if module.get("countertop_occupied_by") == "hob" or module.get("supports_hob"):
            cooking_index = index

    return sink_index, cooking_index


def get_sink_and_hob_edges(modules: list[dict]) -> tuple[int, int] | None:
    sink_module = None
    hob_module = None

    for module in modules:
        if module["name"] == "sink":
            sink_module = module

        if module.get("countertop_occupied_by") == "hob":
            hob_module = module

    if sink_module is None or hob_module is None:
        return None

    sink_start = sink_module["x_mm"]
    sink_end = sink_module["x_mm"] + sink_module["width_mm"]

    hob_start = hob_module.get("countertop_occupied_x_mm")
    hob_width = hob_module.get("countertop_occupied_width_mm")

    if hob_start is None or hob_width is None:
        hob_start = hob_module["x_mm"]
        hob_width = hob_module["width_mm"]

    hob_end = int(hob_start) + int(hob_width)

    if sink_end <= hob_start:
        return sink_end, int(hob_start)

    if hob_end <= sink_start:
        return hob_end, sink_start

    return None


def is_module_between_sink_and_hob(modules: list[dict], index: int) -> bool:
    sink_index, cooking_index = get_sink_and_cooking_indices(modules)

    if sink_index is None or cooking_index is None:
        return False

    start = min(sink_index, cooking_index) + 1
    end = max(sink_index, cooking_index)

    return start <= index < end


def calculate_free_worktop_between_sink_and_hob(modules: list[dict]) -> int:
    edges = get_sink_and_hob_edges(modules)

    if edges is None:
        return 0

    start_x, end_x = edges
    return max(0, end_x - start_x)


def choose_best_existing_worktop_subset(
    free_worktop_candidates: list[dict],
    current_worktop_width: int = 0,
) -> tuple[list[dict], list[dict]]:
    n = len(free_worktop_candidates)

    best_valid_indices = None
    best_valid_score = None

    best_under_min_indices = []
    best_under_min_width = current_worktop_width

    for mask in range(1 << n):
        indices = [index for index in range(n) if mask & (1 << index)]

        selected_width = sum(
            free_worktop_candidates[index]["width_mm"]
            for index in indices
        )

        total_width = current_worktop_width + selected_width

        if total_width > WORKTOP_MAX_MM:
            continue

        if total_width < WORKTOP_MIN_MM:
            if total_width > best_under_min_width:
                best_under_min_width = total_width
                best_under_min_indices = indices
            continue

        score = (
            abs(total_width - WORKTOP_TARGET_MM),
            -len(indices),
            total_width,
        )

        if best_valid_score is None or score < best_valid_score:
            best_valid_score = score
            best_valid_indices = indices

    if best_valid_indices is not None:
        selected_indices = set(best_valid_indices)
    else:
        selected_indices = set(best_under_min_indices)

    between_modules = []
    outside_modules = []

    for index, module in enumerate(free_worktop_candidates):
        if index in selected_indices:
            between_modules.append(module)
        else:
            outside_modules.append(module)

    return between_modules, outside_modules


def build_drawer_width_combinations(max_width: int) -> dict[int, list[int]]:
    dp: dict[int, list[int]] = {
        0: [],
    }

    for current_total in range(max_width + 1):
        if current_total not in dp:
            continue

        for drawer_width in GENERATED_DRAWER_WIDTHS:
            next_total = current_total + drawer_width

            if next_total > max_width:
                continue

            next_combo = sorted(
                dp[current_total] + [drawer_width],
                reverse=True,
            )

            if next_total not in dp:
                dp[next_total] = next_combo
                continue

            current_combo = dp[next_total]

            if drawer_widths_score(next_combo) > drawer_widths_score(current_combo):
                dp[next_total] = next_combo

    return dp


def drawer_widths_score(widths: list[int]) -> tuple[int, int, int, int, int, int]:
    if not widths:
        return (0, 0, 0, 0, 0, 0)

    return (
        -widths.count(300),
        widths.count(PREFERRED_DRAWER_WIDTH_MM),
        -len(widths),
        -len(set(widths)),
        -sum(abs(width - PREFERRED_DRAWER_WIDTH_MM) for width in widths),
        -max(widths),
    )


def choose_drawer_widths_to_reach_worktop_min(
    current_worktop_width: int,
    available_width: int,
) -> list[int]:
    if current_worktop_width >= WORKTOP_MIN_MM:
        return []

    min_added_width = WORKTOP_MIN_MM - current_worktop_width
    max_added_width = min(
        WORKTOP_MAX_MM - current_worktop_width,
        available_width,
    )

    if max_added_width <= 0:
        return []

    combinations = build_drawer_width_combinations(max_added_width)

    possible_totals = [
        total
        for total in combinations.keys()
        if min_added_width <= total <= max_added_width
    ]

    if not possible_totals:
        return []

    best_total = min(
        possible_totals,
        key=lambda total: (
            total,
            tuple(-value for value in drawer_widths_score(combinations[total])),
        ),
    )

    return combinations[best_total]


def choose_drawer_widths_for_remaining_space(remaining_width: int) -> list[int]:
    if remaining_width < min(GENERATED_DRAWER_WIDTHS):
        return []

    combinations = build_drawer_width_combinations(remaining_width)

    possible_totals = [
        total
        for total in combinations.keys()
        if total <= remaining_width
    ]

    if not possible_totals:
        return []

    best_total = max(
        possible_totals,
        key=lambda total: (
            total,
            drawer_widths_score(combinations[total]),
        ),
    )

    return combinations[best_total]


def choose_microwave_support_drawer_width(
    available_width: int,
    microwave_width: int,
) -> int | None:
    possible_widths = [
        width
        for width in GENERATED_DRAWER_WIDTHS
        if microwave_width <= width <= available_width
    ]

    if not possible_widths:
        return None

    return min(possible_widths)


def has_outside_microwave_support(
    outside_modules: list[dict],
    microwave_width: int,
) -> bool:
    return any(
        can_support_solo_microwave(module, microwave_width)
        for module in outside_modules
    )


def move_module_from_cooking_zone_to_outside_for_microwave(
    between_modules: list[dict],
    outside_modules: list[dict],
    microwave_width: int,
    current_worktop_width: int,
) -> int:
    movable_candidates = []

    for index, module in enumerate(between_modules):
        if module.get("locked_adjacent_to_sink"):
            continue

        if not can_support_solo_microwave(module, microwave_width):
            continue

        width_after_move = current_worktop_width - module["width_mm"]

        if width_after_move < WORKTOP_MIN_MM:
            continue

        movable_candidates.append((index, module))

    if not movable_candidates:
        return current_worktop_width

    selected_index, selected_module = min(
        movable_candidates,
        key=lambda item: (
            item[1]["width_mm"],
            item[0],
        ),
    )

    moved_module = between_modules.pop(selected_index)
    moved_module["moved_outside_for"] = "solo_microwave"

    outside_modules.insert(0, moved_module)

    return current_worktop_width - moved_module["width_mm"]


def choose_extra_drawers_for_gap_and_remaining(
    available_width: int,
    current_worktop_width: int,
    prefer_gap: bool,
) -> tuple[list[int], list[int]]:
    if available_width < min(GENERATED_DRAWER_WIDTHS):
        return [], []

    gap_capacity = max(0, WORKTOP_MAX_MM - current_worktop_width)
    gap_capacity = min(gap_capacity, available_width)

    all_combinations = build_drawer_width_combinations(available_width)
    gap_combinations = build_drawer_width_combinations(gap_capacity)

    best_gap_total = 0
    best_outside_total = 0
    best_score = None

    for gap_total, gap_combo in gap_combinations.items():
        if gap_total > gap_capacity:
            continue

        for outside_total, outside_combo in all_combinations.items():
            total = gap_total + outside_total

            if total > available_width:
                continue

            modules_count = len(gap_combo) + len(outside_combo)

            if prefer_gap:
                score = (
                    total,
                    gap_total,
                    drawer_widths_score(gap_combo + outside_combo),
                    -modules_count,
                )
            else:
                score = (
                    total,
                    -gap_total,
                    drawer_widths_score(gap_combo + outside_combo),
                    -modules_count,
                )

            if best_score is None or score > best_score:
                best_score = score
                best_gap_total = gap_total
                best_outside_total = outside_total

    return (
        gap_combinations.get(best_gap_total, []),
        all_combinations.get(best_outside_total, []),
    )


def make_drawer_modules(
    widths: list[int],
    drawer_index: int,
    reason: str,
) -> tuple[list[dict], int]:
    modules = []

    for width in widths:
        modules.append(
            make_module(
                "base",
                f"drawer_{drawer_index}",
                width,
                is_generated_filler=True,
                filler_reason=reason,
            )
        )

        drawer_index += 1

    return modules, drawer_index


def make_cutlery_drawer(width_mm: int = MANDATORY_DRAWER_WIDTH_MM) -> dict:
    width_mm = min(max(width_mm, MANDATORY_DRAWER_WIDTH_MM), CUTLERY_DRAWER_MAX_WIDTH_MM)

    return make_module(
        "base",
        "cutlery_drawer",
        width_mm,
        is_generated_filler=True,
        is_cutlery_drawer=True,
        filler_reason="cutlery_drawer",
    )


def choose_new_cutlery_drawer_width(available_width: int) -> tuple[int, int]:
    if available_width >= CUTLERY_DRAWER_TARGET_WIDTH_MM:
        return CUTLERY_DRAWER_TARGET_WIDTH_MM, 0

    usable_width, leftover_width = split_step_width(available_width)

    if usable_width >= MANDATORY_DRAWER_WIDTH_MM:
        return usable_width, leftover_width

    return MANDATORY_DRAWER_WIDTH_MM, 0


def mark_module_as_cutlery_drawer(module: dict) -> None:
    module["name"] = "cutlery_drawer"
    module["is_cutlery_drawer"] = True
    module["filler_reason"] = "cutlery_drawer"


def make_hob_support_drawer(width_mm: int, as_cutlery: bool = False) -> dict:
    module = make_module(
        "base",
        "drawer_hob_support",
        width_mm,
        is_generated_filler=True,
        supports_hob=True,
        filler_reason="hob_support",
    )

    if as_cutlery:
        mark_module_as_cutlery_drawer(module)

    return module


def is_generated_drawer(module: dict) -> bool:
    return (
        module.get("is_generated_filler")
        and isinstance(module.get("name"), str)
        and module["name"].startswith("drawer_")
    )


def is_cutlery_drawer_candidate(module: dict) -> bool:
    if not is_generated_drawer(module):
        return False

    if module.get("supports_hob"):
        return module.get("width_mm", 0) <= CUTLERY_DRAWER_MAX_WIDTH_MM

    return (
        MANDATORY_DRAWER_WIDTH_MM
        <= module.get("width_mm", 0)
        <= CUTLERY_DRAWER_MAX_WIDTH_MM
    )


def is_plain_filler_drawer(module: dict) -> bool:
    if not is_generated_drawer(module):
        return False

    if module.get("is_cutlery_drawer") or module.get("supports_hob"):
        return False

    return module.get("filler_reason") in {
        "remaining_space",
        "remaining_space_under_450",
    }


def find_last_plain_filler(module_groups: list[list[dict]]) -> dict | None:
    for group in module_groups:
        for module in reversed(group):
            if is_plain_filler_drawer(module):
                return module

    return None


def find_first_cutlery_drawer(module_groups: list[list[dict]]) -> dict | None:
    for group in module_groups:
        for module in group:
            if module.get("is_cutlery_drawer"):
                return module

    return None


def has_cutlery_drawer_candidate(module_groups: list[list[dict]]) -> bool:
    return any(
        is_cutlery_drawer_candidate(module)
        for group in module_groups
        for module in group
    )


def mark_first_cutlery_drawer_candidate(module_groups: list[list[dict]]) -> None:
    if find_first_cutlery_drawer(module_groups) is not None:
        return

    for group in module_groups:
        for module in group:
            if not is_cutlery_drawer_candidate(module):
                continue

            mark_module_as_cutlery_drawer(module)
            return


def ensure_cutlery_drawer(
    available_width: int,
    cutlery_modules: list[dict],
    module_groups: list[list[dict]],
    create_if_missing: bool = True,
) -> tuple[int, int]:
    if find_first_cutlery_drawer(module_groups) is not None:
        return available_width, 0

    mark_first_cutlery_drawer_candidate(module_groups)

    if find_first_cutlery_drawer(module_groups) is not None:
        return available_width, 0

    if not create_if_missing:
        return available_width, 0

    cutlery_width, leftover_width = choose_new_cutlery_drawer_width(available_width)
    cutlery_modules.append(make_cutlery_drawer(cutlery_width))
    available_width -= cutlery_width + leftover_width

    return available_width, leftover_width


def has_cutlery_drawer(module_groups: list[list[dict]]) -> bool:
    return find_first_cutlery_drawer(module_groups) is not None


def add_remaining_width_to_fillers(
    remaining_width: int,
    drawer_index: int,
    remaining_space_modules: list[dict],
    cutlery_search_groups: list[list[dict]],
) -> tuple[int, int]:
    if remaining_width <= 0:
        return drawer_index, 0

    usable_width, leftover_width = split_step_width(remaining_width)

    if usable_width <= 0:
        return drawer_index, leftover_width

    if usable_width >= MANDATORY_DRAWER_WIDTH_MM:
        modules, drawer_index = make_drawer_modules(
            widths=[usable_width],
            drawer_index=drawer_index,
            reason="remaining_space",
        )
        remaining_space_modules.extend(modules)
        return drawer_index, leftover_width

    filler = find_last_plain_filler([remaining_space_modules])

    if filler is not None:
        filler["width_mm"] += usable_width
        filler["absorbed_remaining_width_mm"] = usable_width
        return drawer_index, leftover_width

    cutlery_drawer = find_first_cutlery_drawer(cutlery_search_groups)

    if cutlery_drawer is not None:
        available_cutlery_growth = max(
            0,
            CUTLERY_DRAWER_MAX_WIDTH_MM - cutlery_drawer["width_mm"],
        )
        absorbed_width = min(usable_width, available_cutlery_growth)

        if absorbed_width > 0:
            cutlery_drawer["width_mm"] += absorbed_width
            cutlery_drawer["absorbed_remaining_width_mm"] = absorbed_width
            usable_width -= absorbed_width

        if usable_width >= MANDATORY_DRAWER_WIDTH_MM:
            modules, drawer_index = make_drawer_modules(
                widths=[usable_width],
                drawer_index=drawer_index,
                reason="remaining_space",
            )
            remaining_space_modules.extend(modules)
            return drawer_index, leftover_width

        return drawer_index, leftover_width + usable_width

    if usable_width >= MANDATORY_DRAWER_WIDTH_MM:
        remaining_space_modules.append(make_cutlery_drawer(usable_width))
        return drawer_index, leftover_width

    return drawer_index, leftover_width + usable_width


def resolve_small_remaining_space_filler(
    remaining_space_modules: list[dict],
    microwave_support_modules: list[dict],
    outside_free_modules: list[dict],
    cooking_gap_modules: list[dict],
    extra_gap_modules: list[dict],
    current_worktop_width: int,
) -> None:
    if not remaining_space_modules:
        return

    last_module = remaining_space_modules[-1]

    if not is_generated_drawer(last_module):
        return

    small_width = last_module["width_mm"]

    if small_width >= MANDATORY_DRAWER_WIDTH_MM:
        return

    outside_groups = [
        remaining_space_modules[:-1],
        microwave_support_modules,
        outside_free_modules,
    ]

    for group in outside_groups:
        for module in reversed(group):
            if is_generated_drawer(module):
                module["width_mm"] += small_width
                module["absorbed_small_remaining_filler_mm"] = small_width
                remaining_space_modules.pop()
                return

    if current_worktop_width + small_width <= WORKTOP_MAX_MM:
        for module in reversed(cooking_gap_modules):
            if is_generated_drawer(module):
                module["width_mm"] += small_width
                module["absorbed_small_remaining_filler_mm"] = small_width
                remaining_space_modules.pop()
                return

    for index in range(len(extra_gap_modules) - 1, -1, -1):
        module = extra_gap_modules[index]

        if not is_generated_drawer(module):
            continue

        if current_worktop_width - module["width_mm"] < WORKTOP_MIN_MM:
            continue

        moved_module = extra_gap_modules.pop(index)
        last_module["width_mm"] += moved_module["width_mm"]
        last_module["absorbed_gap_filler_mm"] = moved_module["width_mm"]
        return


def merge_small_generated_fillers(module_groups: list[list[dict]]) -> None:
    for group in module_groups:
        index = 0

        while index < len(group):
            module = group[index]

            if not is_generated_drawer(module) or module["width_mm"] >= MANDATORY_DRAWER_WIDTH_MM:
                index += 1
                continue

            target_index = None

            for candidate_index in range(index - 1, -1, -1):
                if is_generated_drawer(group[candidate_index]):
                    target_index = candidate_index
                    break

            if target_index is None:
                for candidate_index in range(index + 1, len(group)):
                    if is_generated_drawer(group[candidate_index]):
                        target_index = candidate_index
                        break

            if target_index is None:
                index += 1
                continue

            target_module = group[target_index]
            target_module["width_mm"] += module["width_mm"]
            target_module["absorbed_small_filler_mm"] = (
                target_module.get("absorbed_small_filler_mm", 0)
                + module["width_mm"]
            )
            group.pop(index)

            if target_index > index:
                index += 1


def renumber_generated_drawers(modules: list[dict]) -> None:
    drawer_index = 1

    for module in modules:
        if module.get("is_generated_filler") and module["name"].startswith("drawer_"):
            module["name"] = f"drawer_{drawer_index}"
            drawer_index += 1


def get_next_larger_sink_width(current_width: int, max_increase: int) -> int | None:
    for width in reversed(SINK_WIDTH_OPTIONS):
        if width <= current_width:
            continue

        if width - current_width <= max_increase:
            return width

    return None


def get_next_larger_sink_width_up_to(
    current_width: int,
    max_increase: int,
    max_width: int,
) -> int | None:
    for width in reversed(SINK_WIDTH_OPTIONS):
        if width <= current_width:
            continue

        if width > max_width:
            continue

        if width - current_width <= max_increase:
            return width

    return None


def sync_numeric_size_adjustment(
    size_adjustments: list[dict],
    field: str,
    label: str,
    original_value: int,
    final_value: int,
    reason: str,
) -> None:
    if final_value == original_value:
        return

    for adjustment in size_adjustments:
        if adjustment.get("field") != field:
            continue

        adjustment["from_mm"] = original_value
        adjustment["to_mm"] = final_value
        adjustment["reason"] = reason
        return

    size_adjustments.append(
        {
            "field": field,
            "label": label,
            "from_mm": original_value,
            "to_mm": final_value,
            "reason": reason,
        }
    )


def use_remaining_width_to_improve_primary_modules(
    remaining_width: int,
    hob_support_modules: list[dict],
    hob: dict,
    hob_width: int,
    sink_module: dict,
    original_sink_width: int,
    size_adjustments: list[dict],
    warnings: list[str],
    locked: dict | None = None,
) -> tuple[int, int]:
    if remaining_width <= 0:
        return remaining_width, hob_width

    locked = locked or {}

    if locked.get("sink.width_mm"):
        return remaining_width, hob_width

    next_sink_width = get_next_larger_sink_width_up_to(
        current_width=sink_module["width_mm"],
        max_increase=remaining_width,
        max_width=PREFERRED_DRAWER_WIDTH_MM,
    )

    if next_sink_width is not None:
        sink_increase = next_sink_width - sink_module["width_mm"]
        sink_module["width_mm"] = next_sink_width
        remaining_width -= sink_increase
        adjustment_reason = (
            "cooking_zone_minimum"
            if next_sink_width < original_sink_width
            else "use_remaining_space"
        )

        sync_numeric_size_adjustment(
            size_adjustments=size_adjustments,
            field="sink.width_mm",
            label="Мойка",
            original_value=original_sink_width,
            final_value=next_sink_width,
            reason=adjustment_reason,
        )
        warnings[:] = [
            warning
            for warning in warnings
            if not warning.startswith("Размер мойки изменён")
        ]

        if next_sink_width < original_sink_width:
            warnings.append(
                f"Размер мойки изменён с {original_sink_width} мм на {next_sink_width} мм, чтобы сохранить рабочую зону между мойкой и варочной."
            )

    return remaining_width, hob_width


def count_300_modules(modules: list[dict]) -> int:
    return sum(
        1
        for module in modules
        if module.get("width_mm") == 300
    )


def sync_sink_size_adjustment(
    size_adjustments: list[dict],
    original_sink_width: int,
    final_sink_width: int,
    warnings: list[str],
) -> None:
    if final_sink_width == original_sink_width:
        size_adjustments[:] = [
            adjustment
            for adjustment in size_adjustments
            if adjustment.get("field") != "sink.width_mm"
        ]
        warnings[:] = [
            warning
            for warning in warnings
            if not warning.startswith("Размер мойки изменён")
        ]
        return

    for adjustment in size_adjustments:
        if adjustment.get("field") != "sink.width_mm":
            continue

        adjustment["to_mm"] = final_sink_width
        return

    size_adjustments.append(
        {
            "field": "sink.width_mm",
            "label": "Мойка",
            "from_mm": original_sink_width,
            "to_mm": final_sink_width,
            "reason": "reduce_300mm_modules",
        }
    )
    warnings.append(
        f"Размер мойки изменён с {original_sink_width} мм на {final_sink_width} мм, чтобы уменьшить количество модулей шириной 300 мм."
    )


def reduce_300mm_modules(
    modules: list[dict],
    original_sink_width: int,
    size_adjustments: list[dict],
    warnings: list[str],
    locked: dict | None = None,
) -> None:
    locked = locked or {}

    if count_300_modules(modules) <= 1:
        return

    sink_module = next(
        (module for module in modules if module.get("name") == "sink"),
        None,
    )

    if sink_module is not None and not locked.get("sink.width_mm"):
        sink_increase_sources = [
            module
            for module in modules
            if module is not sink_module
            and is_generated_drawer(module)
            and not module.get("supports_hob")
            and module.get("width_mm", 0) == 300
        ]

        for source_module in sink_increase_sources:
            if count_300_modules(modules) <= 1:
                return

            next_sink_width = get_next_larger_sink_width(
                current_width=sink_module["width_mm"],
                max_increase=source_module["width_mm"],
            )

            if next_sink_width is None:
                continue

            increase = next_sink_width - sink_module["width_mm"]
            sink_module["width_mm"] = next_sink_width
            source_module["width_mm"] -= increase
            source_module["width_contributed_to_sink_mm"] = increase

            if source_module["width_mm"] <= 0:
                modules.remove(source_module)

        sync_sink_size_adjustment(
            size_adjustments=size_adjustments,
            original_sink_width=original_sink_width,
            final_sink_width=sink_module["width_mm"],
            warnings=warnings,
        )

    index = 0

    while count_300_modules(modules) > 1 and index < len(modules):
        module = modules[index]

        if not is_generated_drawer(module) or module.get("width_mm") != 300:
            index += 1
            continue

        target_module = None

        for candidate_index in range(index - 1, -1, -1):
            candidate = modules[candidate_index]
            if is_generated_drawer(candidate) and candidate is not module:
                target_module = candidate
                break

        if target_module is None:
            for candidate_index in range(index + 1, len(modules)):
                candidate = modules[candidate_index]
                if is_generated_drawer(candidate) and candidate is not module:
                    target_module = candidate
                    break

        if target_module is None:
            index += 1
            continue

        target_module["width_mm"] += module["width_mm"]
        target_module["absorbed_300mm_drawer_mm"] = (
            target_module.get("absorbed_300mm_drawer_mm", 0)
            + module["width_mm"]
        )
        modules.pop(index)


def order_gap_modules_for_sink_edge(
    sink_edge: str,
    mandatory_adjacent_modules: list[dict],
    flexible_between_modules: list[dict],
) -> list[dict]:
    if sink_edge == "right":
        return flexible_between_modules + mandatory_adjacent_modules

    return mandatory_adjacent_modules + flexible_between_modules


def get_cooking_zone_required_width(
    fixed_width_without_hob: int,
    sink_width: int,
    dishwasher_enabled: bool,
    dishwasher_width: int,
    hob_width: int,
    oven_placement: str,
    current_worktop_width: int,
) -> int:
    fixed_width = fixed_width_without_hob + sink_width

    if dishwasher_enabled:
        fixed_width += dishwasher_width

    return (
        fixed_width
        + get_hob_fixed_width(hob_width, oven_placement)
        + MANDATORY_DRAWER_WIDTH_MM
        + max(
            0,
            WORKTOP_MIN_MM
            - current_worktop_width
            - get_hob_left_offset_in_support(hob_width, oven_placement),
        )
    )


def get_reduced_sink_width_options(current_width: int) -> list[int]:
    return sorted(
        [
            width
            for width in SINK_WIDTH_OPTIONS
            if width < current_width
        ],
        reverse=True,
    )


def choose_reduced_sink_width(current_width: int, required_saving: int) -> int:
    possible_widths = get_reduced_sink_width_options(current_width)

    if not possible_widths:
        return current_width

    widths_that_save_enough = [
        width
        for width in possible_widths
        if current_width - width >= required_saving
    ]

    if widths_that_save_enough:
        return widths_that_save_enough[0]

    return possible_widths[-1]


def get_reduced_hob_width_options(current_width: int) -> list[int]:
    return sorted(
        [
            width
            for width in HOB_WIDTH_OPTIONS
            if width < current_width
        ],
        reverse=True,
    )


def choose_reduced_hob_width(current_width: int, required_saving: int) -> int:
    possible_widths = get_reduced_hob_width_options(current_width)

    if not possible_widths:
        return current_width

    widths_that_save_enough = [
        width
        for width in possible_widths
        if current_width - width >= required_saving
    ]

    if widths_that_save_enough:
        return widths_that_save_enough[0]

    return possible_widths[-1]


def get_hob_support_width(hob_width: int, oven_placement: str) -> int:
    if hob_width == 300:
        return 600

    if oven_placement == "under_counter" and hob_width <= 600:
        return 600

    return hob_width


def get_hob_left_offset_in_support(hob_width: int, oven_placement: str) -> int:
    support_width = get_hob_support_width(hob_width, oven_placement)
    return max(0, int((support_width - hob_width) / 2))


def get_hob_fixed_width(hob_width: int, oven_placement: str) -> int:
    return get_hob_support_width(hob_width, oven_placement)


def adjust_sink_width_for_cooking_zone(
    *,
    wall_length_mm: int,
    fixed_width_without_hob: int,
    sink_width: int,
    dishwasher_enabled: bool,
    dishwasher_width: int,
    hob_width: int,
    oven_placement: str,
    current_worktop_width: int,
    warnings: list[str],
) -> tuple[int, list[dict]]:
    size_adjustments = []
    required_width = get_cooking_zone_required_width(
        fixed_width_without_hob=fixed_width_without_hob,
        sink_width=sink_width,
        dishwasher_enabled=dishwasher_enabled,
        dishwasher_width=dishwasher_width,
        hob_width=hob_width,
        oven_placement=oven_placement,
        current_worktop_width=current_worktop_width,
    )

    if required_width <= wall_length_mm or sink_width <= 600:
        return sink_width, size_adjustments

    reduced_sink_width = max(
        600,
        choose_reduced_sink_width(sink_width, required_width - wall_length_mm),
    )

    if reduced_sink_width == sink_width:
        return sink_width, size_adjustments

    size_adjustments.append(
        {
            "field": "sink.width_mm",
            "label": "Мойка",
            "from_mm": sink_width,
            "to_mm": reduced_sink_width,
            "reason": "cooking_zone_fit",
        }
    )

    return reduced_sink_width, size_adjustments


def adjust_hob_width_for_cooking_zone(
    *,
    wall_length_mm: int,
    fixed_width_without_hob: int,
    sink_width: int,
    dishwasher_enabled: bool,
    dishwasher_width: int,
    hob_width: int,
    oven_placement: str,
    current_worktop_width: int,
    warnings: list[str],
) -> tuple[int, list[dict]]:
    size_adjustments = []
    required_width = get_cooking_zone_required_width(
        fixed_width_without_hob=fixed_width_without_hob,
        sink_width=sink_width,
        dishwasher_enabled=dishwasher_enabled,
        dishwasher_width=dishwasher_width,
        hob_width=hob_width,
        oven_placement=oven_placement,
        current_worktop_width=current_worktop_width,
    )

    if required_width <= wall_length_mm or hob_width <= 600:
        return hob_width, size_adjustments

    reduced_hob_width = max(
        600,
        choose_reduced_hob_width(hob_width, required_width - wall_length_mm),
    )

    if reduced_hob_width == hob_width:
        return hob_width, size_adjustments

    size_adjustments.append(
        {
            "field": "hob.cabinet_width_mm",
            "label": "Варочная поверхность",
            "from_mm": hob_width,
            "to_mm": reduced_hob_width,
            "reason": "cooking_zone_fit",
        }
    )

    return reduced_hob_width, size_adjustments


def adjust_sizes_for_mandatory_450_drawer(
    *,
    wall_length_mm: int,
    fixed_width_without_sink_and_dishwasher: int,
    sink_width: int,
    dishwasher_enabled: bool,
    dishwasher_width: int,
    warnings: list[str],
) -> tuple[int, int, list[dict]]:
    size_adjustments = []
    fixed_width = fixed_width_without_sink_and_dishwasher + sink_width

    if dishwasher_enabled:
        fixed_width += dishwasher_width

    if wall_length_mm - fixed_width >= MANDATORY_DRAWER_WIDTH_MM:
        return sink_width, dishwasher_width, size_adjustments

    for candidate_sink_width in get_reduced_sink_width_options(sink_width):
        candidate_fixed_width = fixed_width_without_sink_and_dishwasher + candidate_sink_width
        if dishwasher_enabled:
            candidate_fixed_width += dishwasher_width

        if wall_length_mm - candidate_fixed_width >= MANDATORY_DRAWER_WIDTH_MM:
            size_adjustments.append(
                {
                    "field": "sink.width_mm",
                    "label": "Мойка",
                    "from_mm": sink_width,
                    "to_mm": candidate_sink_width,
                    "reason": "mandatory_cutlery_drawer",
                }
            )
            return candidate_sink_width, dishwasher_width, size_adjustments

    if dishwasher_enabled and dishwasher_width > 450:
        candidate_dishwasher_width = 450
        candidate_fixed_width = (
            fixed_width_without_sink_and_dishwasher
            + sink_width
            + candidate_dishwasher_width
        )

        if wall_length_mm - candidate_fixed_width >= MANDATORY_DRAWER_WIDTH_MM:
            size_adjustments.append(
                {
                    "field": "dishwasher.width_mm",
                    "label": "Посудомоечная машина",
                    "from_mm": dishwasher_width,
                    "to_mm": candidate_dishwasher_width,
                    "reason": "mandatory_cutlery_drawer",
                }
            )
            return sink_width, candidate_dishwasher_width, size_adjustments

    return sink_width, dishwasher_width, size_adjustments


def build_contiguous_segments(
    modules: list[dict],
    allowed_types: set[str],
    segment_type: str,
    name_prefix: str,
    height_mm: int,
) -> list[dict]:
    sorted_modules = sorted(
        modules,
        key=lambda module: module.get("x_mm", 0),
    )

    segments = []
    current_x = None
    current_width = 0

    for module in sorted_modules:
        module_type = module.get("type")
        module_x = module.get("x_mm", 0)
        module_width = module.get("width_mm", 0)

        if module_type not in allowed_types:
            if current_x is not None:
                segments.append(
                    {
                        "type": segment_type,
                        "name": f"{name_prefix}_{len(segments) + 1}",
                        "x_mm": current_x,
                        "width_mm": current_width,
                        "height_mm": height_mm,
                    }
                )

                current_x = None
                current_width = 0

            continue

        if current_x is None:
            current_x = module_x
            current_width = module_width
            continue

        expected_next_x = current_x + current_width

        if module_x == expected_next_x:
            current_width += module_width
        else:
            segments.append(
                {
                    "type": segment_type,
                    "name": f"{name_prefix}_{len(segments) + 1}",
                    "x_mm": current_x,
                    "width_mm": current_width,
                    "height_mm": height_mm,
                }
            )

            current_x = module_x
            current_width = module_width

    if current_x is not None:
        segments.append(
            {
                "type": segment_type,
                "name": f"{name_prefix}_{len(segments) + 1}",
                "x_mm": current_x,
                "width_mm": current_width,
                "height_mm": height_mm,
            }
        )

    return segments


def build_plinth_modules(modules: list[dict]) -> list[dict]:
    plinth_modules = [
        module
        for module in modules
        if module.get("name") != "freestanding_fridge_in_carcass"
    ]

    return build_contiguous_segments(
        modules=plinth_modules,
        allowed_types={"base", "tall", "appliance_tall", "profile_handle"},
        segment_type="plinth",
        name_prefix="plinth",
        height_mm=PLINTH_HEIGHT_MM,
    )


def build_wall_panel_modules(
    modules: list[dict],
    countertop_thickness_mm: int,
) -> list[dict]:
    wall_panels = build_contiguous_segments(
        modules=modules,
        allowed_types={"base"},
        segment_type="wall_panel",
        name_prefix="wall_panel",
        height_mm=WALL_PANEL_HEIGHT_MM,
    )

    for panel in wall_panels:
        panel["countertop_thickness_mm"] = countertop_thickness_mm

    return wall_panels


def build_countertop_modules(
    modules: list[dict],
    material_key: str,
    thickness_mm: int,
) -> list[dict]:
    countertops = build_contiguous_segments(
        modules=modules,
        allowed_types={"base"},
        segment_type="countertop",
        name_prefix="countertop",
        height_mm=thickness_mm,
    )

    for countertop in countertops:
        countertop["material_key"] = material_key
        countertop["material_label"] = COUNTERTOP_MATERIAL_LABELS.get(
            material_key,
            material_key,
        )
        countertop["thickness_mm"] = thickness_mm

    return countertops


def get_free_worktop_segment_around_module(
    modules: list[dict],
    module_index: int,
) -> tuple[int, int]:
    start_index = module_index

    while start_index > 0:
        previous_module = modules[start_index - 1]

        if previous_module.get("countertop_role") != "free_worktop":
            break

        if previous_module.get("countertop_occupied_by"):
            break

        start_index -= 1

    end_index = module_index

    while end_index + 1 < len(modules):
        next_module = modules[end_index + 1]

        if next_module.get("countertop_role") != "free_worktop":
            break

        if next_module.get("countertop_occupied_by"):
            break

        end_index += 1

    segment_start = modules[start_index]["x_mm"]
    last_module = modules[end_index]
    segment_end = last_module["x_mm"] + last_module["width_mm"]

    return segment_start, segment_end


def choose_hob_x_in_segment(
    module: dict,
    segment: tuple[int, int],
    hob_width: int,
) -> int | None:
    segment_start, segment_end = segment
    preferred_x = (
        module["x_mm"]
        + get_hob_left_offset_in_support(
            hob_width,
            module.get("oven_position", ""),
        )
    )

    min_x = max(
        module["x_mm"],
        segment_start + HOB_SIDE_CLEARANCE_MM,
    )
    max_x = min(
        module["x_mm"] + module["width_mm"] - hob_width,
        segment_end - HOB_SIDE_CLEARANCE_MM - hob_width,
    )

    if min_x > max_x:
        return None

    return int(clamp(preferred_x, min_x, max_x))


def get_hob_clearance_zone(modules: list[dict]) -> tuple[int, int] | None:
    for module in modules:
        if module.get("countertop_occupied_by") != "hob":
            continue

        hob_x = module.get("countertop_occupied_x_mm")
        hob_width = module.get("countertop_occupied_width_mm")

        if hob_x is None or hob_width is None:
            continue

        return (
            int(hob_x) - HOB_SIDE_CLEARANCE_MM,
            int(hob_x) + int(hob_width) + HOB_SIDE_CLEARANCE_MM,
        )

    return None


def overlaps_interval(start: int, end: int, interval: tuple[int, int] | None) -> bool:
    if interval is None:
        return False

    interval_start, interval_end = interval
    return start < interval_end and end > interval_start


def choose_appliance_x_avoiding_interval(
    *,
    module: dict,
    appliance_width: int,
    blocked_interval: tuple[int, int] | None,
    prefer_edge: str | None = None,
) -> int | None:
    min_x = module["x_mm"]
    max_x = module["x_mm"] + module["width_mm"] - appliance_width

    if min_x > max_x:
        return None

    candidates = [
        min_x,
        max_x,
        module["x_mm"] + int((module["width_mm"] - appliance_width) / 2),
    ]

    valid_candidates = [
        x
        for x in candidates
        if not overlaps_interval(x, x + appliance_width, blocked_interval)
    ]

    if not valid_candidates:
        return None

    if prefer_edge == "left":
        return min(valid_candidates)

    if prefer_edge == "right":
        return max(valid_candidates)

    return min(
        valid_candidates,
        key=lambda x: abs(
            x
            - (
                module["x_mm"]
                + int((module["width_mm"] - appliance_width) / 2)
            )
        ),
    )


def place_hob_on_worktop(
    *,
    modules: list[dict],
    hob: dict,
    warnings: list[str],
) -> tuple[list[dict], dict | None]:
    hob_width = to_int(
        hob.get("cabinet_width_mm", hob.get("width_mm")),
        600,
    )
    support_module = None
    support_index = None

    for index, module in enumerate(modules):
        if module.get("supports_hob"):
            support_module = module
            support_index = index
            break

    if support_module is None or support_index is None:
        return [], None

    segment = get_free_worktop_segment_around_module(modules, support_index)
    hob_x = choose_hob_x_in_segment(support_module, segment, hob_width)

    if hob_x is None:
        segment_start, segment_end = segment
        warnings.append(
            f"Варочная поверхность {hob_width} мм не размещена: не получается выдержать боковые отступы {HOB_SIDE_CLEARANCE_MM} мм в зоне {segment_end - segment_start} мм."
        )
        return [], None

    support_module["countertop_role"] = "blocked"
    support_module["countertop_occupied_by"] = "hob"
    support_module["countertop_occupied_x_mm"] = hob_x
    support_module["countertop_occupied_width_mm"] = hob_width
    support_module["countertop_free_mm"] = max(
        0,
        support_module["width_mm"] - hob_width,
    )

    placement = {
        "name": "hob",
        "x_mm": int(hob_x),
        "width_mm": hob_width,
        "height_mm": 50,
        "module_name": support_module.get("name"),
    }

    return [placement], placement


def place_solo_microwave_on_worktop(
    *,
    modules: list[dict],
    microwave: dict,
    wall_length_mm: int,
    warnings: list[str],
) -> tuple[list[dict], dict | None]:
    microwave_width = to_int(microwave.get("width_mm"), 450)
    microwave_height = to_int(microwave.get("height_mm"), 250)
    blocked_interval = get_hob_clearance_zone(modules)

    candidates = [
        module
        for module in modules
        if can_support_solo_microwave(module, microwave_width)
    ]

    if not candidates:
        warnings.append(
            f"Не найден свободный нижний модуль для соло микроволновки шириной {microwave_width} мм."
        )
        return [], None

    scored_candidates = []

    for module in candidates:
        prefer_edge = (
            "left"
            if module["x_mm"] + module["width_mm"] / 2 <= wall_length_mm / 2
            else "right"
        )
        x_mm = choose_appliance_x_avoiding_interval(
            module=module,
            appliance_width=microwave_width,
            blocked_interval=blocked_interval,
            prefer_edge=prefer_edge,
        )

        if x_mm is None:
            continue

        edge_distance = min(x_mm, wall_length_mm - (x_mm + microwave_width))
        scored_candidates.append((edge_distance, module["x_mm"], x_mm, module))

    if not scored_candidates:
        warnings.append(
            f"Соло микроволновка {microwave_width} мм конфликтует с зоной варочной поверхности."
        )
        return [], None

    _, _, microwave_x, support_module = min(scored_candidates)
    support_module["countertop_occupied_by"] = "solo_microwave"
    support_module["countertop_occupied_x_mm"] = microwave_x
    support_module["countertop_occupied_width_mm"] = microwave_width
    support_module["countertop_free_mm"] = max(
        0,
        support_module["width_mm"] - microwave_width,
    )

    placement = {
        "name": "solo_microwave",
        "x_mm": int(microwave_x),
        "width_mm": microwave_width,
        "height_mm": microwave_height,
        "module_name": support_module.get("name"),
    }

    return [placement], placement



