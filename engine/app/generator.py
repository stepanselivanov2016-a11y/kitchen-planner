from app.kitchen_constants import *
from app.wall_modules import (
    apply_wall_facade_grouping,
    build_wall_modules,
    get_hood_width_for_hob,
    place_upper_built_in_microwave,
)
from app.corner_generator import generate_corner_layout

from app.kitchen_options import *
from app.lower_modules import *
from app.length_optimizer import *


def get_layout_shape(module_options: dict | None, normalized_spec: dict | None = None) -> str:
    module_options = module_options or {}
    normalized_spec = normalized_spec or {}
    room = module_options.get("room", {})
    shape = room.get("layout_shape", normalized_spec.get("shape", "straight"))

    return "corner" if shape == "corner" else "straight"


def _generate_layout_once(normalized_spec: dict, module_options: dict | None = None) -> dict:
    module_options = module_options or {}
    locked = get_locked_options(module_options)

    room = module_options.get("room", {})
    required = module_options.get("required", {})
    optional = module_options.get("optional", {})

    wall_length_mm = to_int(
        room.get("wall_length_mm"),
        normalized_spec.get("wall_length_mm", 3000),
    )

    countertop_material_key = get_countertop_material_key(room)
    countertop_material_label = COUNTERTOP_MATERIAL_LABELS[countertop_material_key]
    countertop_thickness_mm = get_countertop_thickness_mm(
        room,
        countertop_material_key,
    )
    kitchen_height_mm = get_kitchen_height_mm(room)

    customer_height_mode = get_customer_height_mode(room)
    customer_height_cm = get_customer_height_cm(room, customer_height_mode)

    countertop_height_mm = get_recommended_countertop_height_mm(
        customer_height_cm=customer_height_cm,
        customer_height_mode=customer_height_mode,
    )

    base_module_height_mm = get_base_module_height_mm(
        countertop_height_mm=countertop_height_mm,
        countertop_thickness_mm=countertop_thickness_mm,
    )

    warnings = []

    sink_edge, fridge_edge = determine_straight_kitchen_edges(
        normalized_spec=normalized_spec,
        warnings=warnings,
        room=room,
    )

    refrigerator = required.get("refrigerator", {})
    oven = required.get("oven", {})
    sink = required.get("sink", {})
    hood = required.get("hood", {})
    microwave = required.get("microwave", {})
    hob = required.get("hob", {})
    hood_type = hood.get("type", "built_in")
    wall_cabinets_enabled = get_wall_cabinets_enabled(room, hood_type)
    mezzanine_enabled = bool(room.get("mezzanine_enabled", True))
    ceiling_type = get_ceiling_type(room)
    upper_cabinet_opening = (
        "lift" if room.get("upper_cabinet_opening") == "lift" else "hinged"
    )
    size_adjustments = []

    refrigerator_is_solo_freestanding = (
        refrigerator.get("mode") == "freestanding"
        and refrigerator.get("freestanding_installation", "solo") == "solo"
    )

    if (
        refrigerator_is_solo_freestanding
        and mezzanine_enabled
    ):
        size_adjustments.append(
            {
                "field": "room.mezzanine_enabled",
                "label": "Антресольные шкафы",
                "from_value": format_option_value("room.mezzanine_enabled", True),
                "to_value": format_option_value("room.mezzanine_enabled", False),
                "reason": "freestanding_solo_fridge",
            }
        )
        mezzanine_enabled = False

    if not mezzanine_enabled and kitchen_height_mm > 2200:
        size_adjustments.append(
            {
                "field": "room.kitchen_height_mm",
                "label": "Высота кухни",
                "from_mm": kitchen_height_mm,
                "to_mm": 2200,
                "reason": "mezzanine_disabled",
            }
        )
        kitchen_height_mm = 2200

    if hood_type == "solo" and room.get("wall_cabinets_enabled", True):
        size_adjustments.append(
            {
                "field": "room.wall_cabinets_enabled",
                "label": "Навесные шкафы",
                "from_value": format_option_value("room.wall_cabinets_enabled", True),
                "to_value": format_option_value("room.wall_cabinets_enabled", False),
                "reason": "solo_hood",
            }
        )

    ceiling_filler_height_mm = get_ceiling_filler_height_mm(
        room,
        wall_cabinets_enabled=wall_cabinets_enabled,
        mezzanine_enabled=mezzanine_enabled,
    )
    cabinet_top_height_mm = kitchen_height_mm - ceiling_filler_height_mm

    left_modules = []
    right_modules = []
    free_worktop_candidates = []

    fridge_mode = refrigerator.get("mode", "built_in")

    if fridge_mode == "freestanding":
        freestanding_installation = refrigerator.get(
            "freestanding_installation",
            "solo",
        )

        fridge_body_width = to_int(refrigerator.get("width_mm"), 600)
        fridge_body_height = to_int(refrigerator.get("height_mm"), 2000)
        gap = to_int(refrigerator.get("gap_mm"), 20)
        fridge_carcass_side_width = 20
        fridge_width = fridge_body_width + gap * 2 + fridge_carcass_side_width * 2

        if freestanding_installation == "in_cabinet":
            fridge_module = make_module(
                "tall",
                "freestanding_fridge_in_carcass",
                fridge_width,
                body_width_mm=fridge_body_width,
                body_height_mm=fridge_body_height,
                gap_mm=gap,
                carcass_side_width_mm=fridge_carcass_side_width,
                depth_mm=to_int(refrigerator.get("depth_mm"), 650),
            )
        else:
            fridge_module = make_module(
                "freestanding_solo",
                "freestanding_fridge_solo",
                fridge_body_width + gap * 2,
                body_width_mm=fridge_body_width,
                gap_mm=gap,
                depth_mm=to_int(refrigerator.get("depth_mm"), 650),
                height_mm=fridge_body_height,
            )
    else:
        fridge_module = make_module(
            "tall",
            "built_in_fridge",
            600,
            depth_mm=600,
            height_mm=2100,
        )

    tall_columns = []

    oven_placement = oven.get("placement", "under_counter")
    microwave_type = microwave.get("type", "solo")

    if not is_valid_oven_microwave_pair(oven_placement, microwave_type):
        warnings.append(
            "Недопустимая связка духовки и микроволновки: духовка в колонне допускается только со встроенной микроволновкой в этой колонне, а соло микроволновка допускается с духовкой под столешницей."
        )

    if oven_placement == "column" and microwave_type == "built_in":
        tall_columns.append(
            make_module(
                "tall",
                "oven_microwave_column",
                600,
                oven_position="column",
                microwave_position="column",
                microwave_width_mm=600,
                microwave_height_mm=to_int(microwave.get("height_mm"), 400),
            )
        )
    elif oven_placement == "column":
        tall_columns.append(
            make_module(
                "tall",
                "oven_column",
                600,
                oven_position="column",
            )
        )
    elif microwave_type == "built_in":
        tall_columns.append(
            make_module(
                "tall",
                "microwave_column",
                600,
                microwave_position="column",
                microwave_width_mm=600,
                microwave_height_mm=to_int(microwave.get("height_mm"), 400),
            )
        )

    if fridge_edge == "right":
        right_modules.extend(tall_columns)
        right_modules.append(fridge_module)
    else:
        left_modules.append(fridge_module)
        left_modules.extend(tall_columns)

    left_modules = insert_tall_profile_handles(left_modules, "left")
    right_modules = insert_tall_profile_handles(right_modules, "right")

    dishwasher = optional.get("dishwasher", {})
    dishwasher_enabled = bool(dishwasher.get("enabled"))
    dishwasher_width = to_int(dishwasher.get("width_mm"), 600)

    undercounter_fridge = optional.get("undercounter_fridge", {})
    if undercounter_fridge.get("enabled"):
        free_worktop_candidates.append(
            make_module(
                "base",
                "undercounter_fridge",
                600,
            )
        )

    original_sink_width = to_int(sink.get("width_mm"), 600)
    sink_width = original_sink_width

    hob_width = to_int(
        hob.get("cabinet_width_mm", hob.get("width_mm")),
        600,
    )

    hob_support_modules = []

    hob_support_width = get_hob_support_width(hob_width, oven_placement)

    if oven_placement == "under_counter":
        if hob_width <= 600:
            hob_support_modules.append(
                make_module(
                    "base",
                    "oven_under_counter",
                    600,
                    oven_position="under_counter",
                    supports_hob=True,
                )
            )
        else:
            free_worktop_candidates.append(
                make_module(
                    "base",
                    "oven_under_counter",
                    600,
                    oven_position="under_counter",
                )
            )

            hob_support_modules.append(
                make_hob_support_drawer(
                    hob_support_width,
                    as_cutlery=True,
                )
            )
    else:
        hob_support_modules.append(
            make_hob_support_drawer(
                hob_support_width,
                as_cutlery=True,
            )
        )

    fixed_width_without_hob = sum(
        module["width_mm"]
        for module in (
            left_modules
            + right_modules
            + free_worktop_candidates
        )
    )

    current_worktop_width_before_generated = (
        dishwasher_width
        if dishwasher_enabled
        else 0
    )

    if locked.get("sink.width_mm"):
        size_adjustments = size_adjustments
    else:
        sink_width, sink_size_adjustments = adjust_sink_width_for_cooking_zone(
            wall_length_mm=wall_length_mm,
            fixed_width_without_hob=fixed_width_without_hob,
            sink_width=sink_width,
            dishwasher_enabled=dishwasher_enabled,
            dishwasher_width=dishwasher_width,
            hob_width=hob_width,
            oven_placement=oven_placement,
            current_worktop_width=current_worktop_width_before_generated,
            warnings=warnings,
        )
        size_adjustments.extend(sink_size_adjustments)

    if locked.get("hob.cabinet_width_mm"):
        hob_size_adjustments = []
    else:
        hob_width, hob_size_adjustments = adjust_hob_width_for_cooking_zone(
            wall_length_mm=wall_length_mm,
            fixed_width_without_hob=fixed_width_without_hob,
            sink_width=sink_width,
            dishwasher_enabled=dishwasher_enabled,
            dishwasher_width=dishwasher_width,
            hob_width=hob_width,
            oven_placement=oven_placement,
            current_worktop_width=current_worktop_width_before_generated,
            warnings=warnings,
        )
    size_adjustments.extend(hob_size_adjustments)

    if hob_size_adjustments:
        hob = {
            **hob,
            "cabinet_width_mm": hob_width,
        }

        free_worktop_candidates = [
            module
            for module in free_worktop_candidates
            if module.get("name") != "oven_under_counter"
        ]

        hob_support_modules = []
        hob_support_width = get_hob_support_width(hob_width, oven_placement)

        if oven_placement == "under_counter":
            if hob_width <= 600:
                hob_support_modules.append(
                    make_module(
                        "base",
                        "oven_under_counter",
                        600,
                        oven_position="under_counter",
                        supports_hob=True,
                    )
                )
            else:
                free_worktop_candidates.append(
                    make_module(
                        "base",
                        "oven_under_counter",
                        600,
                        oven_position="under_counter",
                    )
                )

                hob_support_modules.append(
                    make_hob_support_drawer(
                        hob_support_width,
                        as_cutlery=True,
                    )
                )
        else:
            hob_support_modules.append(
                make_hob_support_drawer(
                    hob_support_width,
                    as_cutlery=True,
                )
            )

    mandatory_adjacent_to_sink_modules = []

    if dishwasher_enabled:
        mandatory_adjacent_to_sink_modules.append(
            make_module(
                "base",
                f"dishwasher_{dishwasher_width}",
                dishwasher_width,
                locked_adjacent_to_sink=True,
                adjacent_to="sink",
            )
        )

    sink_module = make_module(
        "base",
        "sink",
        sink_width,
        edge=sink_edge,
    )

    mandatory_worktop_width = sum(
        module["width_mm"]
        for module in mandatory_adjacent_to_sink_modules
    )

    flexible_between_modules, outside_free_modules = choose_best_existing_worktop_subset(
        free_worktop_candidates=free_worktop_candidates,
        current_worktop_width=mandatory_worktop_width,
    )

    drawer_index = 1

    current_worktop_between = mandatory_worktop_width + sum(
        module["width_mm"]
        for module in flexible_between_modules
    )

    fixed_width_before_generated_drawers = sum(
        module["width_mm"]
        for module in (
            left_modules
            + [sink_module]
            + mandatory_adjacent_to_sink_modules
            + flexible_between_modules
            + hob_support_modules
            + outside_free_modules
            + right_modules
        )
    )

    available_width = wall_length_mm - fixed_width_before_generated_drawers

    min_worktop_drawer_widths = choose_drawer_widths_to_reach_worktop_min(
        current_worktop_width=current_worktop_between,
        available_width=available_width,
    )

    min_worktop_drawer_modules, drawer_index = make_drawer_modules(
        widths=min_worktop_drawer_widths,
        drawer_index=drawer_index,
        reason="worktop_between_sink_and_hob_minimum",
    )

    flexible_between_modules.extend(min_worktop_drawer_modules)

    current_worktop_between += sum(min_worktop_drawer_widths)
    available_width -= sum(min_worktop_drawer_widths)

    microwave_support_modules = []
    cutlery_modules = []
    unbuilt_width_mm = 0
    hob_support_has_cutlery = has_cutlery_drawer([hob_support_modules])

    available_width, cutlery_leftover_width = ensure_cutlery_drawer(
        available_width=available_width,
        cutlery_modules=cutlery_modules,
        module_groups=[
            hob_support_modules,
            flexible_between_modules,
            outside_free_modules,
        ],
        create_if_missing=hob_support_has_cutlery,
    )
    unbuilt_width_mm += cutlery_leftover_width

    if microwave_type == "solo":
        microwave_width = to_int(microwave.get("width_mm"), 450)

        if not has_outside_microwave_support(outside_free_modules, microwave_width):
            current_worktop_between = move_module_from_cooking_zone_to_outside_for_microwave(
                between_modules=flexible_between_modules,
                outside_modules=outside_free_modules,
                microwave_width=microwave_width,
                current_worktop_width=current_worktop_between,
            )

        if not has_outside_microwave_support(outside_free_modules, microwave_width):
            support_drawer_width = choose_microwave_support_drawer_width(
                available_width=available_width,
                microwave_width=microwave_width,
            )

            if support_drawer_width is not None:
                support_drawer_modules, drawer_index = make_drawer_modules(
                    widths=[support_drawer_width],
                    drawer_index=drawer_index,
                    reason="solo_microwave_support",
                )

                microwave_support_modules.extend(support_drawer_modules)
                available_width -= support_drawer_width

    remaining_probe_widths = choose_drawer_widths_for_remaining_space(
        available_width
    )

    remaining_probe_total = sum(remaining_probe_widths)

    should_expand_worktop_gap = (
        remaining_probe_total > WORKTOP_MIN_MM
        and current_worktop_between < WORKTOP_MAX_MM
    )

    extra_gap_widths, remaining_space_widths = choose_extra_drawers_for_gap_and_remaining(
        available_width=available_width,
        current_worktop_width=current_worktop_between,
        prefer_gap=should_expand_worktop_gap,
    )

    extra_gap_modules, drawer_index = make_drawer_modules(
        widths=extra_gap_widths,
        drawer_index=drawer_index,
        reason="expand_worktop_between_sink_and_hob",
    )

    remaining_space_modules, drawer_index = make_drawer_modules(
        widths=remaining_space_widths,
        drawer_index=drawer_index,
        reason="remaining_space",
    )
    remaining_space_modules = cutlery_modules + remaining_space_modules

    mark_first_cutlery_drawer_candidate(
        [
            hob_support_modules,
            flexible_between_modules,
            extra_gap_modules,
            outside_free_modules,
            remaining_space_modules,
            microwave_support_modules,
        ]
    )

    used_extra_width = sum(extra_gap_widths) + sum(remaining_space_widths)
    remaining_width_after_standard_fillers = available_width - used_extra_width

    if not has_cutlery_drawer(
        [
            hob_support_modules,
            flexible_between_modules,
            extra_gap_modules,
            outside_free_modules,
            remaining_space_modules,
            microwave_support_modules,
        ]
    ):
        remaining_width_after_standard_fillers, cutlery_leftover_width = ensure_cutlery_drawer(
            available_width=remaining_width_after_standard_fillers,
            cutlery_modules=cutlery_modules,
            module_groups=[
                flexible_between_modules,
                extra_gap_modules,
                remaining_space_modules,
                microwave_support_modules,
                outside_free_modules,
            ],
        )
        unbuilt_width_mm += cutlery_leftover_width
        remaining_space_modules = cutlery_modules + remaining_space_modules

    remaining_width_after_standard_fillers, hob_width = use_remaining_width_to_improve_primary_modules(
        remaining_width=remaining_width_after_standard_fillers,
        hob_support_modules=hob_support_modules,
        hob=hob,
        hob_width=hob_width,
        sink_module=sink_module,
        original_sink_width=original_sink_width,
        size_adjustments=size_adjustments,
        warnings=warnings,
        locked=locked,
    )

    drawer_index, remaining_leftover_width = add_remaining_width_to_fillers(
        remaining_width=remaining_width_after_standard_fillers,
        drawer_index=drawer_index,
        remaining_space_modules=remaining_space_modules,
        cutlery_search_groups=[
            hob_support_modules,
            flexible_between_modules,
            extra_gap_modules,
            remaining_space_modules,
            microwave_support_modules,
            outside_free_modules,
        ],
    )
    unbuilt_width_mm += remaining_leftover_width

    mark_first_cutlery_drawer_candidate(
        [
            hob_support_modules,
            flexible_between_modules,
            extra_gap_modules,
            remaining_space_modules,
            microwave_support_modules,
            outside_free_modules,
        ]
    )

    flexible_between_modules.extend(extra_gap_modules)

    gap_modules = order_gap_modules_for_sink_edge(
        sink_edge=sink_edge,
        mandatory_adjacent_modules=mandatory_adjacent_to_sink_modules,
        flexible_between_modules=flexible_between_modules,
    )

    modules = []
    place_remaining_between_sink_and_hob = (
        current_worktop_between < WORKTOP_MIN_MM
        and bool(remaining_space_modules)
    )

    if sink_edge == "right":
        modules.extend(left_modules)
        modules.extend(outside_free_modules)
        modules.extend(microwave_support_modules)
        if not place_remaining_between_sink_and_hob:
            modules.extend(remaining_space_modules)
        modules.extend(hob_support_modules)
        if place_remaining_between_sink_and_hob:
            modules.extend(remaining_space_modules)
        modules.extend(gap_modules)
        modules.append(sink_module)
        modules.extend(right_modules)
    else:
        modules.extend(left_modules)
        modules.append(sink_module)
        modules.extend(gap_modules)
        if place_remaining_between_sink_and_hob:
            modules.extend(remaining_space_modules)
        modules.extend(hob_support_modules)
        modules.extend(outside_free_modules)
        modules.extend(microwave_support_modules)
        if not place_remaining_between_sink_and_hob:
            modules.extend(remaining_space_modules)
        modules.extend(right_modules)

    reduce_300mm_modules(
        modules=modules,
        original_sink_width=original_sink_width,
        size_adjustments=size_adjustments,
        warnings=warnings,
        locked=locked,
    )

    renumber_generated_drawers(modules)

    x = 0
    for module in modules:
        mark_countertop_role(module)

        if module["type"] == "base":
            module["height_mm"] = base_module_height_mm
        elif module["type"] in {"tall", "appliance_tall"}:
            module["height_mm"] = cabinet_top_height_mm
        elif module["type"] == "profile_handle":
            module["height_mm"] = cabinet_top_height_mm - PLINTH_HEIGHT_MM

        module["x_mm"] = x
        x += module["width_mm"]

    used_width_mm = sum(module["width_mm"] for module in modules)

    if used_width_mm > wall_length_mm:
        warnings.append(
            f"Модули не помещаются в заданную длину кухни: нужно {used_width_mm} мм, доступно {wall_length_mm} мм."
        )

    if unbuilt_width_mm > 0:
        warnings.append(
            f"Остаток {unbuilt_width_mm} мм не застроен: он меньше минимального шага добора {DRAWER_WIDTH_STEP_MM} мм."
        )

    plinth_modules = build_plinth_modules(modules)

    countertop_modules = build_countertop_modules(
        modules=modules,
        material_key=countertop_material_key,
        thickness_mm=countertop_thickness_mm,
    )

    wall_panel_modules = build_wall_panel_modules(
        modules=modules,
        countertop_thickness_mm=countertop_thickness_mm,
    )

    front_objects = []
    hob_placement = None
    solo_microwave_placement = None
    upper_microwave_placement = None

    hob_objects, hob_placement = place_hob_on_worktop(
        modules=modules,
        hob=hob,
        warnings=warnings,
    )

    front_objects.extend(hob_objects)

    if microwave_type == "solo":
        microwave_objects, solo_microwave_placement = place_solo_microwave_on_worktop(
            modules=modules,
            microwave=microwave,
            wall_length_mm=wall_length_mm,
            warnings=warnings,
        )

        front_objects.extend(microwave_objects)

    free_worktop_between_sink_and_hob = calculate_free_worktop_between_sink_and_hob(
        modules
    )

    if free_worktop_between_sink_and_hob < WORKTOP_MIN_MM:
        warnings.append(
            f"Свободная зона между мойкой и варочной слишком маленькая: {free_worktop_between_sink_and_hob} мм. Нужно минимум {WORKTOP_MIN_MM} мм."
        )

    if free_worktop_between_sink_and_hob > WORKTOP_MAX_MM:
        warnings.append(
            f"Свободная зона между мойкой и варочной слишком большая: {free_worktop_between_sink_and_hob} мм. Нужно максимум {WORKTOP_MAX_MM} мм."
        )

    wall_modules = []
    wall_cabinet_bottom_mm = (
        PLINTH_HEIGHT_MM
        + base_module_height_mm
        + LOWER_PROFILE_HANDLE_HEIGHT_MM
        + countertop_thickness_mm
        + WALL_PANEL_HEIGHT_MM
    )

    requested_hood_width = to_int(hood.get("width_mm"), 600)
    hood_width = (
        requested_hood_width
        if locked.get("hood.width_mm")
        else get_hood_width_for_hob(hob_width)
    )

    if hood_width != requested_hood_width and not locked.get("hood.width_mm"):
        sync_numeric_size_adjustment(
            size_adjustments=size_adjustments,
            field="hood.width_mm",
            label="Вытяжка",
            original_value=requested_hood_width,
            final_value=hood_width,
            reason="match_hob_width",
        )

    cooking_module = None
    for module in modules:
        if module.get("countertop_occupied_by") == "hob" or module.get("supports_hob"):
            cooking_module = module
            break

    wall_modules = build_wall_modules(
        modules=modules,
        wall_length_mm=wall_length_mm,
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
        upper_built_in_microwave_present=microwave_type == "upper_built_in",
        ceiling_filler_height_mm=ceiling_filler_height_mm,
        upper_cabinet_opening=upper_cabinet_opening,
    )

    wall_modules = apply_wall_facade_grouping(
        wall_modules,
        upper_cabinet_opening=upper_cabinet_opening,
    )

    if microwave_type == "upper_built_in":
        upper_microwave_placement = place_upper_built_in_microwave(
            wall_modules=wall_modules,
            microwave=microwave,
            warnings=warnings,
            sink_module=sink_module,
        )

    return {
        "shape": "straight",
        "wall_length_mm": wall_length_mm,
        "kitchen_height_mm": kitchen_height_mm,
        "ceiling_type": ceiling_type,
        "ceiling_filler_height_mm": ceiling_filler_height_mm,
        "wall_cabinets_enabled": wall_cabinets_enabled,
        "mezzanine_enabled": mezzanine_enabled,
        "upper_cabinet_opening": upper_cabinet_opening,
        "customer_height_mode": customer_height_mode,
        "customer_height_cm": customer_height_cm,
        "countertop_height_mm": countertop_height_mm,
        "base_module_height_mm": base_module_height_mm,
        "lower_profile_handle_height_mm": LOWER_PROFILE_HANDLE_HEIGHT_MM,
        "plinth_height_mm": PLINTH_HEIGHT_MM,
        "sink_edge": sink_edge,
        "fridge_edge": fridge_edge,
        "countertop_material": countertop_material_key,
        "countertop_material_label": countertop_material_label,
        "countertop_thickness_mm": countertop_thickness_mm,
        "size_adjustments": size_adjustments,
        "modules": modules,
        "plinth_modules": plinth_modules,
        "countertop_modules": countertop_modules,
        "wall_panel_modules": wall_panel_modules,
        "wall_modules": wall_modules,
        "front_objects": front_objects,
        "used_width_mm": used_width_mm,
        "remaining_width_mm": wall_length_mm - used_width_mm,
        "free_worktop_between_sink_and_hob_mm": free_worktop_between_sink_and_hob,
        "hob_placement": hob_placement,
        "solo_microwave_placement": solo_microwave_placement,
        "upper_microwave_placement": upper_microwave_placement,
        "warnings": warnings,
    }


def _upper_facade_uniformity_score(layout: dict) -> tuple:
    facade_widths = []
    upper_ranges = []

    for module in layout.get("wall_modules", []):
        if module.get("tier") not in {"upper", "hood"}:
            continue

        upper_ranges.append(
            (
                int(round(module.get("x_mm", 0))),
                int(round(module.get("x_mm", 0) + module.get("width_mm", 0))),
            )
        )
        door_widths = module.get("facade_door_widths_mm")

        if door_widths:
            facade_widths.extend(int(round(width)) for width in door_widths)
        else:
            facade_widths.append(int(round(module.get("width_mm", 0))))

    facade_widths = [width for width in facade_widths if width > 0]
    upper_ranges = [
        (start, end)
        for start, end in sorted(upper_ranges)
        if end > start
    ]
    gap_width = 0

    for previous, current in zip(upper_ranges, upper_ranges[1:]):
        gap_width += max(0, current[0] - previous[1])

    if len(facade_widths) < 2:
        return (gap_width, 0, 0, 0, 0, 0)

    average_width = sum(facade_widths) / len(facade_widths)
    distinct_widths = len(set(facade_widths))
    spread = max(facade_widths) - min(facade_widths)

    return (
        gap_width,
        distinct_widths,
        spread,
        sum(abs(width - average_width) for width in facade_widths),
        sum(abs(width - UPPER_CABINET_TARGET_WIDTH_MM) for width in facade_widths),
        len(facade_widths),
    )


def _adjust_wall_length_for_upper_uniformity(
    *,
    normalized_spec: dict,
    original_options: dict,
    current_options: dict,
    current_layout: dict,
) -> tuple[dict, dict]:
    if get_locked_options(original_options).get("room.wall_length_mm"):
        return current_layout, current_options

    current_width = current_layout.get("wall_length_mm", 0)
    best_layout = current_layout
    best_options = current_options

    for _ in range(4):
        current_width = best_layout.get("wall_length_mm", 0)
        current_score = _upper_facade_uniformity_score(best_layout)
        next_layout = best_layout
        next_options = best_options
        next_score = current_score

        for delta in (-DRAWER_WIDTH_STEP_MM, DRAWER_WIDTH_STEP_MM):
            candidate_width = current_width + delta

            if candidate_width <= 0:
                continue

            candidate_options = copy_module_options(best_options)
            candidate_options.setdefault("room", {})["wall_length_mm"] = candidate_width
            candidate_layout = _generate_layout_once(
                normalized_spec={**normalized_spec, "wall_length_mm": candidate_width},
                module_options=candidate_options,
            )

            if candidate_layout.get("remaining_width_mm", 0) < 0:
                continue

            if layout_has_blocking_placement_issue(candidate_layout, candidate_options):
                continue

            candidate_score = _upper_facade_uniformity_score(candidate_layout)

            if candidate_score >= current_score:
                continue

            selection_score = (
                candidate_score,
                0 if delta < 0 else 1,
            )
            best_selection_score = (
                next_score,
                0 if next_layout.get("wall_length_mm", current_width) < current_width else 1,
            )

            if selection_score < best_selection_score:
                next_layout = candidate_layout
                next_options = candidate_options
                next_score = candidate_score

        if next_layout is best_layout:
            break

        best_layout = next_layout
        best_options = next_options

    if best_layout is current_layout:
        return current_layout, current_options

    original_width = to_int(
        original_options.get("room", {}).get("wall_length_mm"),
        normalized_spec.get("wall_length_mm", current_width),
    )
    upsert_layout_adjustment(
        layout=best_layout,
        field="room.wall_length_mm",
        label="Ширина кухни",
        original_value=original_width,
        final_value=best_layout["wall_length_mm"],
        reason="upper_cabinet_uniformity",
    )

    return best_layout, best_options


def generate_layout(normalized_spec: dict, module_options: dict | None = None) -> dict:
    module_options = module_options or {}

    if get_layout_shape(module_options, normalized_spec) == "corner":
        return generate_corner_layout(
            normalized_spec,
            module_options,
            straight_layout_builder=generate_layout,
        )

    baseline_layout = _generate_layout_once(
        normalized_spec=normalized_spec,
        module_options=module_options,
    )

    if (
        baseline_layout.get("remaining_width_mm", 0) >= 0
        and not layout_has_blocking_placement_issue(baseline_layout, module_options)
        and not layout_has_forced_length_adjustment(baseline_layout)
        and not has_unlocked_auto_preferred_difference(module_options)
        and not has_unlocked_invalid_oven_microwave_pair(module_options)
    ):
        adjusted_layout, _ = _adjust_wall_length_for_upper_uniformity(
            normalized_spec=normalized_spec,
            original_options=module_options,
            current_options=copy_module_options(module_options),
            current_layout=baseline_layout,
        )
        return adjusted_layout

    best_layout = baseline_layout
    best_score = score_length_candidate(
        layout=baseline_layout,
        original_options=module_options,
        candidate_options=module_options,
    )
    best_options = copy_module_options(module_options)

    for candidate_options in build_length_optimization_candidates(module_options):
        candidate_layout = _generate_layout_once(
            normalized_spec=normalized_spec,
            module_options=candidate_options,
        )
        candidate_score = score_length_candidate(
            layout=candidate_layout,
            original_options=module_options,
            candidate_options=candidate_options,
        )

        if candidate_score < best_score:
            best_layout = candidate_layout
            best_score = candidate_score
            best_options = candidate_options

    best_layout, best_options = _adjust_wall_length_for_upper_uniformity(
        normalized_spec=normalized_spec,
        original_options=module_options,
        current_options=best_options,
        current_layout=best_layout,
    )

    add_candidate_adjustments(
        layout=best_layout,
        original_options=module_options,
        candidate_options=best_options,
    )

    return best_layout
