from app.kitchen_constants import *


def get_locked_options(module_options: dict | None) -> dict:
    module_options = module_options or {}
    locked = module_options.get("locked", {})

    if isinstance(locked, dict):
        return locked

    return {}


def is_option_locked(module_options: dict | None, field: str) -> bool:
    return bool(get_locked_options(module_options).get(field))


SINK_WIDTH_OPTIONS = [
    400,
    450,
    500,
    600,
    800,
    900,
    1000,
    1200,
]

COUNTERTOP_MATERIAL_LABELS = {
    "chipboard_plastic": "ДСП пластик",
    "quartz_agglomerate": "Кварцевый агломерат",
    "natural_stone": "Натуральный камень",
    "acrylic_stone": "Искусственный камень (акрил)",
    "compact_plate": "Компакт-плита",
}

COUNTERTOP_DEFAULT_THICKNESS = {
    "chipboard_plastic": 38,
    "quartz_agglomerate": 20,
    "natural_stone": 20,
    "acrylic_stone": 20,
    "compact_plate": 12,
}


def to_int(value, default: int) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def clamp(value: float, min_value: float, max_value: float) -> float:
    return max(min_value, min(value, max_value))


def round_up_to_step(value: int, step: int = DRAWER_WIDTH_STEP_MM) -> int:
    if value <= 0:
        return 0

    return ((value + step - 1) // step) * step


def split_step_width(width: int) -> tuple[int, int]:
    if width <= 0:
        return 0, 0

    usable_width = width - (width % DRAWER_WIDTH_STEP_MM)
    leftover_width = width - usable_width

    return usable_width, leftover_width


def make_module(module_type: str, name: str, width_mm: int, **extra) -> dict:
    return {
        "type": module_type,
        "name": name,
        "width_mm": width_mm,
        **extra,
    }


def make_tall_profile_handle() -> dict:
    return make_module(
        "profile_handle",
        "tall_profile_handle",
        TALL_PROFILE_HANDLE_WIDTH_MM,
        profile_handle_for="tall_columns",
    )


def insert_tall_profile_handles(edge_modules: list[dict], edge: str) -> list[dict]:
    def needs_tall_profile_handle(module: dict) -> bool:
        return (
            module.get("type") in TALL_COLUMN_TYPES
            and module.get("name") != "freestanding_fridge_in_carcass"
        )

    tall_indexes = [
        index
        for index, module in enumerate(edge_modules)
        if needs_tall_profile_handle(module)
    ]

    if not tall_indexes:
        return edge_modules

    if len(tall_indexes) == 1:
        tall_index = tall_indexes[0]
        result = list(edge_modules)
        insert_index = tall_index + 1 if edge == "left" else tall_index
        result.insert(insert_index, make_tall_profile_handle())
        return result

    result = []
    for index, module in enumerate(edge_modules):
        result.append(module)
        next_module = edge_modules[index + 1] if index + 1 < len(edge_modules) else None

        if (
            needs_tall_profile_handle(module)
            and next_module
            and needs_tall_profile_handle(next_module)
        ):
            result.append(make_tall_profile_handle())

    return result


def get_text_position(normalized_spec: dict, key: str) -> str | None:
    positions = normalized_spec.get("positions", {})
    position = positions.get(key)

    if position in {"left", "center", "right"}:
        return position

    return None


def opposite_edge(edge: str) -> str:
    return "right" if edge == "left" else "left"


def get_countertop_material_key(room: dict | None) -> str:
    room = room or {}
    material = room.get("countertop_material", "chipboard_plastic")

    if material not in COUNTERTOP_MATERIAL_LABELS:
        return "chipboard_plastic"

    return material


def get_countertop_thickness_mm(room: dict | None, material_key: str) -> int:
    room = room or {}
    default_thickness = COUNTERTOP_DEFAULT_THICKNESS.get(material_key, 38)
    thickness_mm = to_int(room.get("countertop_thickness_mm"), default_thickness)

    if thickness_mm <= 0:
        return default_thickness

    return thickness_mm


def get_customer_height_mode(room: dict | None) -> str:
    room = room or {}
    mode = room.get("customer_height_mode", "exact")

    if mode in {"height_170_or_below", "exact", "height_196_or_above"}:
        return mode

    return "exact"


def get_customer_height_cm(room: dict | None, mode: str) -> float:
    room = room or {}

    if mode == "height_170_or_below":
        return 170

    if mode == "height_196_or_above":
        return 196

    try:
        height = float(room.get("customer_height_cm", 175))
    except (TypeError, ValueError):
        height = 175

    if height < 150:
        return 150

    if height > 196:
        return 196

    return height


def get_kitchen_height_mm(room: dict | None) -> int:
    room = room or {}
    height_mm = to_int(room.get("kitchen_height_mm"), 2700)

    if height_mm < 1800:
        return 1800

    if height_mm > 3200:
        return 3200

    return height_mm


def get_wall_cabinets_enabled(room: dict | None, hood_type: str) -> bool:
    room = room or {}

    if hood_type == "solo":
        return False

    return bool(room.get("wall_cabinets_enabled", True))


def get_ceiling_type(room: dict | None) -> str:
    room = room or {}
    ceiling_type = room.get("ceiling_type", "stretch")

    return "plasterboard" if ceiling_type == "plasterboard" else "stretch"


def get_ceiling_filler_height_mm(
    room: dict | None,
    *,
    wall_cabinets_enabled: bool,
    mezzanine_enabled: bool,
) -> int:
    if not wall_cabinets_enabled or not mezzanine_enabled:
        return 0

    return 20 if get_ceiling_type(room) == "plasterboard" else 120


def interpolate(
    value: float,
    from_value: float,
    to_value: float,
    from_result: float,
    to_result: float,
) -> int:
    if value <= from_value:
        return int(round(from_result))

    if value >= to_value:
        return int(round(to_result))

    ratio = (value - from_value) / (to_value - from_value)
    result = from_result + ratio * (to_result - from_result)

    return int(round(result))


def get_recommended_countertop_height_mm(
    customer_height_cm: float,
    customer_height_mode: str,
) -> int:
    if customer_height_mode == "height_170_or_below":
        return 890

    if customer_height_mode == "height_196_or_above":
        return 1030

    height = customer_height_cm

    if height <= 170:
        return 890

    if height <= 175:
        return interpolate(height, 170, 175, 890, 920)

    if height <= 180:
        return interpolate(height, 176, 180, 920, 940)

    if height <= 185:
        return interpolate(height, 181, 185, 940, 970)

    if height <= 190:
        return interpolate(height, 186, 190, 970, 1000)

    if height <= 195:
        return interpolate(height, 191, 195, 1000, 1030)

    return 1030


def get_base_module_height_mm(
    countertop_height_mm: int,
    countertop_thickness_mm: int,
) -> int:
    return (
        countertop_height_mm
        - PLINTH_HEIGHT_MM
        - LOWER_PROFILE_HANDLE_HEIGHT_MM
        - countertop_thickness_mm
    )


def determine_straight_kitchen_edges(
    normalized_spec: dict,
    warnings: list[str],
    room: dict | None = None,
) -> tuple[str, str]:
    room = room or {}

    shape = normalized_spec.get("shape", "straight")
    entry_side = room.get("entry_side")

    sink_text_position = get_text_position(normalized_spec, "sink")
    fridge_text_position = get_text_position(normalized_spec, "fridge")

    if shape == "straight" and entry_side in {"left", "right"}:
        sink_edge = entry_side
        fridge_edge = opposite_edge(sink_edge)

        if sink_text_position in {"left", "right"} and sink_text_position != sink_edge:
            warnings.append(
                "Мойка размещена ближе к выводу воды. Это правило важнее текстового пожелания."
            )

        if fridge_text_position in {"left", "right"} and fridge_text_position != fridge_edge:
            warnings.append(
                "Для прямой кухни холодильник размещён на противоположном краю от мойки."
            )

        return sink_edge, fridge_edge

    if shape != "straight":
        sink_edge = sink_text_position if sink_text_position in {"left", "right"} else "left"
        fridge_edge = fridge_text_position if fridge_text_position in {"left", "right"} else opposite_edge(sink_edge)
        return sink_edge, fridge_edge

    if sink_text_position in {"left", "right"}:
        sink_edge = sink_text_position
        fridge_edge = opposite_edge(sink_edge)

        if fridge_text_position in {"left", "right"} and fridge_text_position == sink_edge:
            warnings.append(
                "Для прямой кухни холодильник перенесён на противоположный край от мойки."
            )

        return sink_edge, fridge_edge

    if fridge_text_position in {"left", "right"}:
        fridge_edge = fridge_text_position
        sink_edge = opposite_edge(fridge_edge)
        return sink_edge, fridge_edge

    return "left", "right"


