from app.kitchen_constants import LOWER_PROFILE_HANDLE_HEIGHT_MM


STROKE_WIDTH = 1.1
DIMENSION_COLOR = "#1f1d86"
DIMENSION_STROKE_WIDTH = 1.0
DIMENSION_EXTENSION_GAP = 8
DIMENSION_MARKER_ID = "dimension-arrow"
MODULE_FILL = "#ffffff"
OVERLAY_FILL = "#d1d5db"
OVERLAY_STROKE = "#6b7280"
OVERLAY_OPACITY = 0.42
WALL_PANEL_FILL = "#ffffff"
COUNTERTOP_FILL = "#f8fafc"
OPENING_MARK_COLOR = "#ef4444"
OPENING_MARK_OPACITY = 0.62
OPENING_MARK_STROKE_WIDTH = 0.9
OPENING_MARK_DASH = "3 2"


def append_dimension_defs(svg: list[str]) -> None:
    svg.append(
        "<defs>"
        f"<marker id='{DIMENSION_MARKER_ID}' markerWidth='8' markerHeight='8' refX='4' refY='4' "
        "orient='auto-start-reverse' markerUnits='strokeWidth'>"
        f"<path d='M 0 0 L 8 4 L 0 8 z' fill='{DIMENSION_COLOR}' />"
        "</marker>"
        "</defs>"
    )


def dimension_extension_segment(anchor: int, dimension: int) -> tuple[int, int] | None:
    if anchor == dimension:
        return None
    if anchor > dimension:
        end = anchor - DIMENSION_EXTENSION_GAP
        if end <= dimension:
            return None
        return dimension, end

    start = anchor + DIMENSION_EXTENSION_GAP
    if start >= dimension:
        return None
    return start, dimension


def append_horizontal_dimension(
    svg: list[str],
    *,
    x1: int,
    x2: int,
    y: int,
    label: str,
    extension_y: int | None = None,
) -> None:
    if x2 <= x1:
        return
    marker_inset = min(5, max(0, (x2 - x1) // 3))
    line_x1 = x1 + marker_inset
    line_x2 = x2 - marker_inset

    if extension_y is not None:
        segment = dimension_extension_segment(extension_y, y)
        if segment is not None:
            y1, y2 = segment
            svg.append(
                f"<line x1='{x1}' y1='{y1}' x2='{x1}' y2='{y2}' stroke='{DIMENSION_COLOR}' stroke-width='{DIMENSION_STROKE_WIDTH}' />"
            )
            svg.append(
                f"<line x1='{x2}' y1='{y1}' x2='{x2}' y2='{y2}' stroke='{DIMENSION_COLOR}' stroke-width='{DIMENSION_STROKE_WIDTH}' />"
            )

    svg.append(
        f"<line x1='{line_x1}' y1='{y}' x2='{line_x2}' y2='{y}' stroke='{DIMENSION_COLOR}' stroke-width='{DIMENSION_STROKE_WIDTH}' "
        f"marker-start='url(#{DIMENSION_MARKER_ID})' marker-end='url(#{DIMENSION_MARKER_ID})' />"
    )
    svg.append(
        f"<text x='{(x1 + x2) / 2}' y='{y - 4}' text-anchor='middle' font-size='12' font-family='Arial' fill='{DIMENSION_COLOR}'>{label}</text>"
    )


def append_vertical_dimension(
    svg: list[str],
    *,
    x: int,
    y1: int,
    y2: int,
    label: str,
    extension_x: int | None = None,
    rotate_label: bool = True,
    label_side: str = "left",
) -> None:
    if y2 <= y1:
        return
    marker_inset = min(5, max(0, (y2 - y1) // 3))
    line_y1 = y1 + marker_inset
    line_y2 = y2 - marker_inset

    if extension_x is not None:
        segment = dimension_extension_segment(extension_x, x)
        if segment is not None:
            x1, x2 = segment
            svg.append(
                f"<line x1='{x1}' y1='{y1}' x2='{x2}' y2='{y1}' stroke='{DIMENSION_COLOR}' stroke-width='{DIMENSION_STROKE_WIDTH}' />"
            )
            svg.append(
                f"<line x1='{x1}' y1='{y2}' x2='{x2}' y2='{y2}' stroke='{DIMENSION_COLOR}' stroke-width='{DIMENSION_STROKE_WIDTH}' />"
            )

    svg.append(
        f"<line x1='{x}' y1='{line_y1}' x2='{x}' y2='{line_y2}' stroke='{DIMENSION_COLOR}' stroke-width='{DIMENSION_STROKE_WIDTH}' "
        f"marker-start='url(#{DIMENSION_MARKER_ID})' marker-end='url(#{DIMENSION_MARKER_ID})' />"
    )
    label_y = (y1 + y2) / 2
    if rotate_label:
        svg.append(
            f"<text x='{x - 7}' y='{label_y}' text-anchor='middle' font-size='12' font-family='Arial' fill='{DIMENSION_COLOR}' "
            f"transform='rotate(-90 {x - 7} {label_y})'>{label}</text>"
        )
    else:
        label_x = x - 8
        text_anchor = "end"
        if label_side == "right":
            label_x = x + 8
            text_anchor = "start"
        svg.append(
            f"<text x='{label_x}' y='{label_y + 4}' text-anchor='{text_anchor}' font-size='12' font-family='Arial' fill='{DIMENSION_COLOR}'>{label}</text>"
        )


def append_opening_path(svg: list[str], points: list[tuple[float, float]]) -> None:
    if len(points) < 2:
        return

    path = " ".join(
        f"{'M' if index == 0 else 'L'} {x:.1f} {y:.1f}"
        for index, (x, y) in enumerate(points)
    )
    svg.append(
        f"<path d='{path}' fill='none' stroke='{OPENING_MARK_COLOR}' stroke-width='{OPENING_MARK_STROKE_WIDTH}' "
        f"stroke-dasharray='{OPENING_MARK_DASH}' stroke-opacity='{OPENING_MARK_OPACITY}' />"
    )


def append_lift_opening_mark(
    svg: list[str],
    *,
    x: int,
    y: int,
    w: int,
    h: int,
) -> None:
    if w <= 12 or h <= 12:
        return

    inset_x = max(5, min(w * 0.12, 18))
    top_y = y + max(5, min(h * 0.08, 12))
    bottom_y = y + h - max(6, min(h * 0.16, 22))
    center_x = x + w / 2

    append_opening_path(
        svg,
        [
            (x + inset_x, top_y),
            (center_x, bottom_y),
            (x + w - inset_x, top_y),
        ],
    )


def append_hinged_opening_mark(
    svg: list[str],
    *,
    x: int,
    y: int,
    w: int,
    h: int,
    hinge_side: str,
) -> None:
    if w <= 12 or h <= 12:
        return

    inset_y = max(5, min(h * 0.16, 18))
    inset_x = max(5, min(w * 0.12, 16))
    hinge_x = x + inset_x if hinge_side == "left" else x + w - inset_x
    apex_x = x + w - inset_x if hinge_side == "left" else x + inset_x
    apex_y = y + h / 2

    append_opening_path(
        svg,
        [
            (hinge_x, y + inset_y),
            (apex_x, apex_y),
            (hinge_x, y + h - inset_y),
        ],
    )


def append_hinged_opening_for_doors(
    svg: list[str],
    *,
    x: int,
    y: int,
    w: int,
    h: int,
    door_widths: list[float],
    wall_length_px: int,
    margin: int,
    barrier_xs: list[int] | None = None,
) -> None:
    if not door_widths:
        door_widths = [w]

    door_x = x
    door_count = len(door_widths)
    for index, door_width in enumerate(door_widths):
        door_w = int(round(door_width))
        if index == door_count - 1:
            door_w = x + w - door_x

        if door_count == 1:
            hinge_side = nearest_barrier_hinge_side(
                x=door_x,
                w=door_w,
                wall_length_px=wall_length_px,
                margin=margin,
                barrier_xs=barrier_xs,
            )
        else:
            hinge_side = "left" if index < door_count / 2 else "right"

        append_hinged_opening_mark(
            svg,
            x=door_x,
            y=y,
            w=door_w,
            h=h,
            hinge_side=hinge_side,
        )
        door_x += door_w


def nearest_edge_hinge_side(
    *,
    x: int,
    w: int,
    wall_length_px: int,
    margin: int,
) -> str:
    module_center = x + w / 2
    drawing_center = margin + wall_length_px / 2
    return "left" if module_center <= drawing_center else "right"


def nearest_barrier_hinge_side(
    *,
    x: int,
    w: int,
    wall_length_px: int,
    margin: int,
    barrier_xs: list[int] | None = None,
) -> str:
    module_center = x + w / 2
    candidates: list[tuple[float, str]] = [
        (abs(module_center - margin), "left"),
        (abs(module_center - (margin + wall_length_px)), "right"),
    ]

    for barrier_x in barrier_xs or []:
        if abs(barrier_x - module_center) < 1:
            continue
        candidates.append(
            (
                abs(module_center - barrier_x),
                "left" if barrier_x < module_center else "right",
            )
        )

    return min(candidates, key=lambda item: item[0])[1]


def tall_barrier_edges_px(
    modules: list[dict],
    *,
    margin: int,
    scale: float,
    exclude_module: dict | None = None,
) -> list[int]:
    edges = []
    tall_names = {
        "built_in_fridge",
        "freestanding_fridge_in_carcass",
        "oven_microwave_column",
        "microwave_column",
        "oven_column",
        "corner_tall",
    }
    for module in modules:
        if exclude_module is not None and module is exclude_module:
            continue
        if module.get("type") not in {"tall", "appliance_tall"} and module.get("name") not in tall_names:
            continue
        x = margin + int(module.get("x_mm", 0) * scale)
        x2 = margin + int((module.get("x_mm", 0) + module.get("width_mm", 0)) * scale)
        edges.extend([x, x2])
    return edges


def mezzanine_uses_lift(width_mm: int, height_mm: int) -> bool:
    return width_mm >= height_mm


def render_top_view(layout: dict) -> str:
    if layout.get("shape") == "corner":
        return render_corner_top_view(layout)

    scale = 0.25
    margin = 40
    module_depth_mm = 600
    wall_module_depth_mm = 350

    display_length_mm = max(
        layout.get("wall_length_mm", 3000),
        layout.get("used_width_mm", 0),
    )

    content_width_px = int(display_length_mm * scale)
    dimension_canvas_padding_right = 140 if layout.get("is_corner_side") else 0
    width_px = content_width_px + margin * 2 + dimension_canvas_padding_right
    height_px = 285

    svg = []
    svg.append(f"<svg xmlns='http://www.w3.org/2000/svg' width='{width_px}' height='{height_px}'>")
    svg.append("<rect width='100%' height='100%' fill='white' />")
    svg.append(f"<text x='{margin}' y='24' font-size='16' font-family='Arial'>Top View</text>")

    base_y = 55
    wall_y = base_y
    wall_h = int(wall_module_depth_mm * scale)
    h = int(module_depth_mm * scale)

    for module in layout.get("modules", []):
        x = margin + int(module["x_mm"] * scale)
        x2 = margin + int((module["x_mm"] + module["width_mm"]) * scale)
        w = x2 - x

        fill = "#374151" if module["type"] == "profile_handle" else MODULE_FILL

        svg.append(f"<rect x='{x}' y='{base_y}' width='{w}' height='{h}' fill='{fill}' stroke='black' stroke-width='{STROKE_WIDTH}' />")
        if module["type"] == "profile_handle":
            svg.append(
                f"<text x='{x + 3}' y='{base_y + h + 16}' font-size='9' font-family='Arial'>profile</text>"
            )
        elif not is_drawer_filler_module(module):
            svg.append(
                f"<text x='{x + 6}' y='{base_y + h + 16}' font-size='11' font-family='Arial'>{module['name']}</text>"
            )

    for module in layout.get("wall_modules", []):
        if module.get("tier") == "ceiling_filler":
            continue
        x = margin + int(module["x_mm"] * scale)
        w = int(module["width_mm"] * scale)
        fill = MODULE_FILL

        svg.append(
            f"<rect x='{x}' y='{wall_y}' width='{w}' height='{wall_h}' fill='{fill}' fill-opacity='0.72' stroke='black' stroke-width='{STROKE_WIDTH}' />"
        )
        svg.append(
            f"<line x1='{x}' y1='{wall_y + wall_h}' x2='{x + w}' y2='{wall_y + wall_h}' stroke='black' stroke-width='{STROKE_WIDTH}' stroke-dasharray='4 3' />"
        )
        door_x = x
        for door_width_mm in module.get("facade_door_widths_mm", [])[:-1]:
            door_x += int(door_width_mm * scale)
            svg.append(
                f"<line x1='{door_x}' y1='{wall_y}' x2='{door_x}' y2='{wall_y + wall_h}' stroke='black' stroke-width='{STROKE_WIDTH}' />"
            )

    svg.append("</svg>")
    return "".join(svg)


def _module_top_fill(module: dict) -> str:
    if module["type"] == "profile_handle":
        return "#374151"
    return MODULE_FILL


def merge_svg_lines(lines: set[tuple[int, int, int, int]]) -> list[tuple[int, int, int, int]]:
    horizontal: dict[int, list[tuple[int, int]]] = {}
    vertical: dict[int, list[tuple[int, int]]] = {}
    other = []

    for x1, y1, x2, y2 in lines:
        if y1 == y2:
            start, end = sorted((x1, x2))
            horizontal.setdefault(y1, []).append((start, end))
        elif x1 == x2:
            start, end = sorted((y1, y2))
            vertical.setdefault(x1, []).append((start, end))
        else:
            other.append((x1, y1, x2, y2))

    result = []

    for y, intervals in horizontal.items():
        merged = []
        for start, end in sorted(intervals):
            if not merged or start > merged[-1][1]:
                merged.append([start, end])
            else:
                merged[-1][1] = max(merged[-1][1], end)

        result.extend((start, y, end, y) for start, end in merged)

    for x, intervals in vertical.items():
        merged = []
        for start, end in sorted(intervals):
            if not merged or start > merged[-1][1]:
                merged.append([start, end])
            else:
                merged[-1][1] = max(merged[-1][1], end)

        result.extend((x, start, x, end) for start, end in merged)

    result.extend(other)
    return sorted(result)


def rect_edges(x: int, y: int, w: int, h: int) -> set[tuple[int, int, int, int]]:
    return {
        (x, y, x + w, y),
        (x, y + h, x + w, y + h),
        (x, y, x, y + h),
        (x + w, y, x + w, y + h),
    }


def shared_rect_edges(
    a: tuple[int, int, int, int],
    b: tuple[int, int, int, int],
) -> set[tuple[int, int, int, int]]:
    ax, ay, aw, ah = a
    bx, by, bw, bh = b
    shared = set()

    if ax + aw == bx or bx + bw == ax:
        x = ax + aw if ax + aw == bx else ax
        start = max(ay, by)
        end = min(ay + ah, by + bh)
        if end > start:
            shared.add((x, start, x, end))

    if ay + ah == by or by + bh == ay:
        y = ay + ah if ay + ah == by else ay
        start = max(ax, bx)
        end = min(ax + aw, bx + bw)
        if end > start:
            shared.add((start, y, end, y))

    return shared


def render_corner_top_view(layout: dict) -> str:
    scale = 0.22
    margin = 46
    base_depth_mm = 600
    wall_depth_mm = 350
    side_1_width_mm = layout.get("side_1_width_mm", layout.get("wall_length_mm", 3000))
    side_2_width_mm = layout.get("side_2_width_mm", 2400)
    side_2_corner_at_start = layout.get("side_2", {}).get("corner_position", "left") == "left"
    width_px = int((side_1_width_mm + base_depth_mm) * scale) + margin * 2
    height_px = int((side_2_width_mm + base_depth_mm) * scale) + margin * 2
    origin_x = margin
    origin_y = margin
    corner_at_left = layout.get("corner_position") == "left"
    side_2_x = (
        origin_x
        if corner_at_left
        else origin_x + int(max(0, side_1_width_mm - base_depth_mm) * scale)
    )

    svg = [
        f"<svg xmlns='http://www.w3.org/2000/svg' width='{width_px}' height='{height_px}'>",
        "<rect width='100%' height='100%' fill='white' />",
        f"<text x='{margin}' y='24' font-size='16' font-family='Arial'>Top View - Corner</text>",
    ]

    base_h = int(base_depth_mm * scale)
    wall_h = int(wall_depth_mm * scale)

    base_shapes = []
    wall_shapes = []

    for module in layout.get("side_1", {}).get("modules", []):
        x = origin_x + int(module.get("side_x_mm", module.get("x_mm", 0)) * scale)
        y = origin_y
        w = int(module.get("width_mm", 0) * scale)
        shape_kind = (
            "corner_false"
            if module.get("corner_false_panel")
            else "corner"
            if module.get("corner_module")
            else "normal"
        )
        base_shapes.append((x, y, w, base_h, _module_top_fill(module), shape_kind))
        if module.get("name") != "corner_base":
            svg.append(f"<text x='{x + 4}' y='{y + base_h + 14}' font-size='9' font-family='Arial'>{module['name']}</text>")

    for module in layout.get("side_2", {}).get("modules", []):
        x = side_2_x
        module_width_mm = module.get("width_mm", 0)
        module_x_mm = module.get("side_x_mm", module.get("x_mm", 0))
        top_view_y_mm = (
            module_x_mm
            if side_2_corner_at_start
            else side_2_width_mm - module_x_mm - module_width_mm
        )
        y = origin_y + int(top_view_y_mm * scale)
        h = int(module_width_mm * scale)
        shape_kind = (
            "corner_false"
            if module.get("corner_false_panel")
            else "corner"
            if module.get("corner_module")
            else "normal"
        )
        base_shapes.append((x, y, base_h, h, _module_top_fill(module), shape_kind))
        if module.get("name") != "corner_base":
            svg.append(f"<text x='{x + base_h + 6}' y='{y + 14}' font-size='9' font-family='Arial'>{module['name']}</text>")

    for x, y, w, h, fill, _ in base_shapes:
        svg.append(f"<rect x='{x}' y='{y}' width='{w}' height='{h}' fill='{fill}' stroke='none' />")

    base_outline = set()
    for x, y, w, h, _, _ in base_shapes:
        base_outline.update(rect_edges(x, y, w, h))

    for index, shape in enumerate(base_shapes):
        x, y, w, h, _, kind = shape
        if kind not in {"corner", "corner_false"}:
            continue

        for other in base_shapes[index + 1:]:
            ox, oy, ow, oh, _, other_kind = other
            if {kind, other_kind} != {"corner", "corner_false"}:
                continue

            base_outline.difference_update(
                shared_rect_edges((x, y, w, h), (ox, oy, ow, oh))
            )

    for x1, y1, x2, y2 in merge_svg_lines(base_outline):
        svg.append(
            f"<line x1='{x1}' y1='{y1}' x2='{x2}' y2='{y2}' stroke='black' stroke-width='{STROKE_WIDTH}' />"
        )

    def upper_false_panel_shape(side: dict, *, is_side_2: bool) -> tuple[int, int, int, int] | None:
        projection = _make_corner_projection(layout, "side_2" if is_side_2 else "side_1")
        if not projection.get("other_has_upper"):
            return None

        side_width = side.get("wall_length_mm", side_2_width_mm if is_side_2 else side_1_width_mm)
        corner_position = side.get("corner_position", "left")
        false_x_mm = (
            350
            if corner_position == "left"
            else max(0, side_width - 350 - 50)
        )

        if is_side_2:
            top_y_mm = (
                false_x_mm
                if side_2_corner_at_start
                else side_width - false_x_mm - 50
            )
            return (
                side_2_x,
                origin_y + int(top_y_mm * scale),
                wall_h,
                max(1, int(50 * scale)),
            )

        return (
            origin_x + int(false_x_mm * scale),
            origin_y,
            max(1, int(50 * scale)),
            wall_h,
        )

    for module in layout.get("side_1", {}).get("wall_modules", []):
        if module.get("tier") == "ceiling_filler":
            continue
        x = origin_x + int(module.get("side_x_mm", module.get("x_mm", 0)) * scale)
        y = origin_y
        w = int(module.get("width_mm", 0) * scale)
        wall_shapes.append((x, y, w, wall_h, MODULE_FILL, 1, "normal"))

    for module in layout.get("side_2", {}).get("wall_modules", []):
        if module.get("tier") == "ceiling_filler":
            continue
        x = side_2_x
        module_width_mm = module.get("width_mm", 0)
        module_x_mm = module.get("side_x_mm", module.get("x_mm", 0))
        top_view_y_mm = (
            module_x_mm
            if side_2_corner_at_start
            else side_2_width_mm - module_x_mm - module_width_mm
        )
        y = origin_y + int(top_view_y_mm * scale)
        h = int(module_width_mm * scale)
        wall_shapes.append((x, y, wall_h, h, MODULE_FILL, 1, "normal"))

    for side_key, is_side_2 in (("side_1", False), ("side_2", True)):
        shape = upper_false_panel_shape(layout.get(side_key, {}), is_side_2=is_side_2)
        if shape:
            x, y, w, h = shape
            wall_shapes.append((x, y, w, h, MODULE_FILL, 1, "upper_false"))

    for x, y, w, h, fill, opacity, _ in wall_shapes:
        svg.append(
            f"<rect x='{x}' y='{y}' width='{w}' height='{h}' fill='{fill}' fill-opacity='{opacity}' stroke='none' />"
        )

    wall_outline = set()
    for x, y, w, h, _, _, _ in wall_shapes:
        wall_outline.update(rect_edges(x, y, w, h))

    for index, shape in enumerate(wall_shapes):
        x, y, w, h, _, _, kind = shape
        if kind != "upper_false":
            continue

        for other in wall_shapes:
            if other is shape:
                continue
            ox, oy, ow, oh, _, _, other_kind = other
            if other_kind == "upper_false":
                continue

            wall_outline.difference_update(
                shared_rect_edges((x, y, w, h), (ox, oy, ow, oh))
            )

    for x1, y1, x2, y2 in merge_svg_lines(wall_outline):
        svg.append(
            f"<line x1='{x1}' y1='{y1}' x2='{x2}' y2='{y2}' stroke='black' stroke-width='{STROKE_WIDTH}' />"
        )

    svg.append("</svg>")
    return "".join(svg)


def get_mezzanine_height_mm(layout: dict) -> int:
    if layout.get("mezzanine_enabled") is False:
        return 0

    for module in layout.get("wall_modules", []):
        if module.get("tier") == "mezzanine":
            return int(module.get("height_mm", 0))

    kitchen_height_mm = layout.get("kitchen_height_mm", 2700)
    return max(0, int(round((kitchen_height_mm - 1450) / 3)))


def get_ceiling_filler_height_mm(layout: dict) -> int:
    if not layout.get("wall_cabinets_enabled", True) or not layout.get(
        "mezzanine_enabled", True
    ):
        return 0

    for module in layout.get("wall_modules", []):
        if module.get("tier") == "ceiling_filler":
            return int(module.get("height_mm", 0))

    return int(layout.get("ceiling_filler_height_mm", 0) or 0)


def _is_projection_tall_module(module: dict) -> bool:
    return module.get("type") in {"tall", "appliance_tall", "freestanding_solo"} or module.get("name") in {
        "built_in_fridge",
        "freestanding_fridge_in_carcass",
        "freestanding_fridge_solo",
        "corner_tall",
    }


def _has_tall_projection(side: dict) -> bool:
    return any(
        _is_projection_tall_module(module)
        for module in side.get("modules", [])
        if not module.get("corner_module")
    )


def _has_upper_projection(side: dict) -> bool:
    return any(
        module.get("tier") in {"upper", "hood", "mezzanine", "microwave"}
        for module in side.get("wall_modules", [])
    )


def _make_corner_projection(layout: dict, side_key: str) -> dict:
    side = layout.get(side_key, {})
    other_side_key = "side_2" if side_key == "side_1" else "side_1"
    other_side = layout.get(other_side_key, {})
    corner_position = side.get("corner_position", layout.get("corner_position", "right"))
    other_has_tall = _has_tall_projection(other_side)
    other_wall_modules = other_side.get("wall_modules", [])
    upper_bottom_mm = min(
        (
            int(module.get("y_mm", 1450))
            for module in other_wall_modules
            if module.get("tier") in {"upper", "hood", "microwave"}
        ),
        default=1450,
    )
    mezzanine_bottom_mm = min(
        (
            int(module.get("y_mm", kitchen_height_mm := layout.get("kitchen_height_mm", 2700)))
            for module in other_wall_modules
            if module.get("tier") == "mezzanine"
        ),
        default=layout.get("kitchen_height_mm", 2700),
    )

    return {
        "corner_position": corner_position,
        "other_has_tall": other_has_tall,
        "other_has_upper": _has_upper_projection(other_side),
        "upper_bottom_mm": upper_bottom_mm,
        "mezzanine_bottom_mm": mezzanine_bottom_mm,
    }


def append_corner_projection_overlay(
    svg: list[str],
    *,
    projection: dict | None,
    margin: int,
    scale: float,
    baseline_y: int,
    base_top_y: int,
    kitchen_height_mm: int,
    wall_length_mm: int,
) -> None:
    if not projection:
        return

    corner_position = projection.get("corner_position", "right")
    other_has_tall = bool(projection.get("other_has_tall"))
    other_has_upper = bool(projection.get("other_has_upper"))

    if not other_has_tall and not other_has_upper:
        return

    false_panel_width_mm = 50

    if not other_has_tall:
        lower_projection_width_mm = min(600, wall_length_mm)
        lower_x_mm = (
            0
            if corner_position == "left"
            else max(0, wall_length_mm - lower_projection_width_mm)
        )
        lower_x = margin + int(lower_x_mm * scale)
        lower_x2 = margin + int((lower_x_mm + lower_projection_width_mm) * scale)
        lower_w = max(1, lower_x2 - lower_x)
        lower_y = base_top_y
        lower_h = baseline_y - lower_y
        svg.append(
            f"<rect x='{lower_x}' y='{lower_y}' width='{lower_w}' height='{lower_h}' fill='{OVERLAY_FILL}' "
            f"fill-opacity='{OVERLAY_OPACITY}' stroke='{OVERLAY_STROKE}' stroke-width='{STROKE_WIDTH}' />"
        )

    depth_mm = 600 if other_has_tall else 350
    projection_width_mm = min(depth_mm, wall_length_mm)
    x_mm = 0 if corner_position == "left" else max(0, wall_length_mm - projection_width_mm)
    x = margin + int(x_mm * scale)
    projection_x2 = margin + int((x_mm + projection_width_mm) * scale)
    w = max(1, projection_x2 - x)

    upper_bottom_mm = int(projection.get("upper_bottom_mm", 1450))
    mezzanine_bottom_mm = int(
        projection.get("mezzanine_bottom_mm", kitchen_height_mm)
    )
    upper_y = baseline_y - int(kitchen_height_mm * scale)
    upper_bottom_y = baseline_y - int(upper_bottom_mm * scale)
    upper_h = max(1, upper_bottom_y - upper_y)
    mezzanine_y = baseline_y - int(mezzanine_bottom_mm * scale)
    upper_projection_width_mm = 350 if other_has_upper else 0
    false_x_mm = (
        x_mm + upper_projection_width_mm
        if corner_position == "left"
        else x_mm + projection_width_mm - upper_projection_width_mm - false_panel_width_mm
    )
    false_x = margin + int(false_x_mm * scale)
    false_x2 = margin + int((false_x_mm + false_panel_width_mm) * scale)
    false_w = max(1, false_x2 - false_x)

    if other_has_tall:
        lower_projection_y = upper_bottom_y
        lower_projection_h = baseline_y - lower_projection_y
        svg.append(
            f"<rect x='{x}' y='{lower_projection_y}' width='{w}' height='{lower_projection_h}' fill='{OVERLAY_FILL}' "
            f"fill-opacity='{OVERLAY_OPACITY}' stroke='none' />"
        )

    hidden_false_panel_lines = []

    if other_has_upper:
        svg.append(
            f"<rect x='{false_x}' y='{upper_y}' width='{false_w}' height='{upper_h}' "
            f"fill='{MODULE_FILL}' stroke='none' />"
        )
        hidden_false_panel_lines.extend(
            [
                (false_x, upper_y, false_x + false_w, upper_y, STROKE_WIDTH),
                (false_x, upper_bottom_y, false_x + false_w, upper_bottom_y, STROKE_WIDTH),
            ]
        )
        hidden_false_panel_lines.extend(
            [
                (false_x, upper_y, false_x, upper_bottom_y, STROKE_WIDTH),
                (false_x + false_w, upper_y, false_x + false_w, upper_bottom_y, STROKE_WIDTH),
            ]
        )

        for x1, y1, x2, y2, stroke_width in hidden_false_panel_lines:
            svg.append(
                f"<line x1='{x1}' y1='{y1}' x2='{x2}' y2='{y2}' "
                f"stroke='black' stroke-width='{stroke_width}' />"
            )

    if other_has_tall:
        svg.append(
            f"<rect x='{x}' y='{upper_y}' width='{w}' height='{upper_h}' fill='{OVERLAY_FILL}' "
            f"fill-opacity='{OVERLAY_OPACITY}' stroke='none' />"
        )
        svg.append(
            f"<line x1='{x}' y1='{upper_bottom_y}' x2='{x + w}' y2='{upper_bottom_y}' "
            f"stroke='{OVERLAY_STROKE}' stroke-width='{STROKE_WIDTH}' stroke-opacity='0.55' />"
        )
        svg.append(
            f"<rect x='{x}' y='{upper_y}' width='{w}' height='{baseline_y - upper_y}' fill='none' "
            f"stroke='{OVERLAY_STROKE}' stroke-width='{STROKE_WIDTH}' stroke-opacity='0.75' />"
        )
    else:
        svg.append(
            f"<rect x='{x}' y='{upper_y}' width='{w}' height='{upper_h}' fill='{OVERLAY_FILL}' "
            f"fill-opacity='{OVERLAY_OPACITY}' stroke='{OVERLAY_STROKE}' stroke-width='{STROKE_WIDTH}' />"
        )


def append_ceiling_filler_modules(
    svg: list[str],
    *,
    layout: dict,
    margin: int,
    scale: float,
    baseline_y: int,
) -> None:
    for module in layout.get("wall_modules", []):
        if module.get("tier") != "ceiling_filler":
            continue

        x = margin + int(module.get("x_mm", 0) * scale)
        y = baseline_y - int(
            (module.get("y_mm", 0) + module.get("height_mm", 0)) * scale
        )
        w = int(module.get("width_mm", 0) * scale)
        h = max(1, int(module.get("height_mm", 0) * scale))
        svg.append(
            f"<rect x='{x}' y='{y}' width='{w}' height='{h}' fill='{MODULE_FILL}' stroke='black' stroke-width='{STROKE_WIDTH}' />"
        )


def append_microwave_face(svg: list[str], *, x: int, y: int, w: int, h: int) -> None:
    if w <= 0 or h <= 0:
        return

    pad = max(3, min(10, int(min(w, h) * 0.08)))
    frame_x = x + pad
    frame_y = y + pad
    frame_w = max(1, w - pad * 2)
    frame_h = max(1, h - pad * 2)
    panel_w = max(8, int(frame_w * 0.2))
    glass_w = max(1, frame_w - panel_w - pad)

    svg.append(
        f"<rect x='{frame_x}' y='{frame_y}' width='{frame_w}' height='{frame_h}' rx='3' fill='#111827' stroke='#374151' stroke-width='{STROKE_WIDTH}' />"
    )
    svg.append(
        f"<rect x='{frame_x + 3}' y='{frame_y + 3}' width='{glass_w}' height='{max(1, frame_h - 6)}' rx='2' fill='#1f2937' stroke='#6b7280' stroke-width='{max(0.6, STROKE_WIDTH * 0.7)}' />"
    )
    svg.append(
        f"<path d='M {frame_x + 8} {frame_y + frame_h - 8} C {frame_x + glass_w * 0.35} {frame_y + 8}, {frame_x + glass_w * 0.65} {frame_y + frame_h - 10}, {frame_x + glass_w - 8} {frame_y + 8}' fill='none' stroke='#93c5fd' stroke-width='0.9' opacity='0.45' />"
    )

    panel_x = frame_x + glass_w + pad
    svg.append(
        f"<rect x='{panel_x}' y='{frame_y + 3}' width='{max(1, panel_w - 3)}' height='{max(1, frame_h - 6)}' rx='2' fill='#f8fafc' stroke='#9ca3af' stroke-width='{max(0.6, STROKE_WIDTH * 0.7)}' />"
    )
    button_cx = panel_x + max(3, int(panel_w / 2))
    button_top = frame_y + 10
    for index in range(3):
        cy = button_top + index * max(5, int(frame_h / 5))
        svg.append(
            f"<circle cx='{button_cx}' cy='{cy}' r='{max(1, min(3, int(panel_w / 8)))}' fill='#64748b' />"
        )


def append_solo_microwave_face(svg: list[str], *, x: int, y: int, w: int, h: int) -> None:
    if w <= 0 or h <= 0:
        return

    base_h = max(2, int(h * 0.08))
    body_y = y
    body_h = max(1, h - base_h)
    pad = max(4, min(10, int(min(w, body_h) * 0.08)))
    panel_w = max(10, int(w * 0.18))
    glass_x = x + pad
    glass_y = body_y + pad
    glass_w = max(1, w - panel_w - pad * 3)
    glass_h = max(1, body_h - pad * 2)
    panel_x = glass_x + glass_w + pad

    svg.append(
        f"<rect x='{x}' y='{body_y}' width='{w}' height='{body_h}' rx='4' fill='#e5e7eb' stroke='#374151' stroke-width='{STROKE_WIDTH}' />"
    )
    svg.append(
        f"<rect x='{glass_x}' y='{glass_y}' width='{glass_w}' height='{glass_h}' rx='2' fill='#111827' stroke='#4b5563' stroke-width='{STROKE_WIDTH}' />"
    )
    svg.append(
        f"<path d='M {glass_x + 8} {glass_y + glass_h - 8} C {glass_x + glass_w * 0.35} {glass_y + 8}, {glass_x + glass_w * 0.65} {glass_y + glass_h - 10}, {glass_x + glass_w - 8} {glass_y + 8}' fill='none' stroke='#93c5fd' stroke-width='0.9' opacity='0.45' />"
    )
    svg.append(
        f"<rect x='{panel_x}' y='{glass_y}' width='{max(1, panel_w)}' height='{glass_h}' rx='2' fill='#f8fafc' stroke='#9ca3af' stroke-width='{max(0.6, STROKE_WIDTH * 0.75)}' />"
    )
    knob_cx = panel_x + panel_w / 2
    for index in range(3):
        svg.append(
            f"<circle cx='{knob_cx}' cy='{glass_y + glass_h * (0.28 + index * 0.22)}' r='{max(1.4, min(3, panel_w * 0.12))}' fill='#64748b' />"
        )

    foot_w = max(4, int(w * 0.12))
    foot_y = y + h - base_h
    svg.append(
        f"<rect x='{x + int(w * 0.16)}' y='{foot_y}' width='{foot_w}' height='{base_h}' fill='#6b7280' />"
    )
    svg.append(
        f"<rect x='{x + w - int(w * 0.16) - foot_w}' y='{foot_y}' width='{foot_w}' height='{base_h}' fill='#6b7280' />"
    )


def append_oven_face(svg: list[str], *, x: int, y: int, w: int, h: int) -> None:
    if w <= 0 or h <= 0:
        return

    pad = max(4, min(12, int(min(w, h) * 0.07)))
    frame_x = x + pad
    frame_y = y + pad
    frame_w = max(1, w - pad * 2)
    frame_h = max(1, h - pad * 2)
    control_h = max(10, int(frame_h * 0.18))
    glass_y = frame_y + control_h + max(2, int(pad * 0.5))
    glass_h = max(1, frame_h - control_h - pad)

    svg.append(
        f"<rect x='{frame_x}' y='{frame_y}' width='{frame_w}' height='{frame_h}' fill='#111827' stroke='#374151' stroke-width='{STROKE_WIDTH}' />"
    )
    svg.append(
        f"<rect x='{frame_x + 3}' y='{frame_y + 3}' width='{max(1, frame_w - 6)}' height='{control_h}' fill='#f8fafc' stroke='#9ca3af' stroke-width='{max(0.6, STROKE_WIDTH * 0.7)}' />"
    )
    for ratio in (0.18, 0.82):
        svg.append(
            f"<circle cx='{frame_x + frame_w * ratio}' cy='{frame_y + 3 + control_h / 2}' r='{max(2, min(4, control_h * 0.22))}' fill='#64748b' />"
        )
    svg.append(
        f"<rect x='{frame_x + frame_w * 0.36}' y='{frame_y + 3 + control_h * 0.28}' width='{frame_w * 0.28}' height='{max(2, control_h * 0.32)}' fill='#cbd5e1' />"
    )
    svg.append(
        f"<rect x='{frame_x + 4}' y='{glass_y}' width='{max(1, frame_w - 8)}' height='{glass_h}' fill='#1f2937' stroke='#6b7280' stroke-width='{max(0.6, STROKE_WIDTH * 0.75)}' />"
    )
    handle_y = glass_y + max(4, glass_h * 0.18)
    svg.append(
        f"<line x1='{frame_x + frame_w * 0.22}' y1='{handle_y}' x2='{frame_x + frame_w * 0.78}' y2='{handle_y}' stroke='#e5e7eb' stroke-width='1.5' stroke-linecap='round' />"
    )


def append_dishwasher_icon(svg: list[str], *, x: int, y: int, w: int, h: int) -> None:
    if w <= 0 or h <= 0:
        return

    icon_size = max(28, min(w * 0.38, h * 0.34, 58))
    icon_x = x + (w - icon_size) / 2
    icon_y = y + h * 0.34
    stroke = "#111827"
    secondary_stroke = "#4b5563"
    thin = max(0.8, STROKE_WIDTH * 0.75)

    svg.append(
        f"<rect x='{icon_x}' y='{icon_y}' width='{icon_size}' height='{icon_size * 0.78}' "
        f"fill='none' stroke='{stroke}' stroke-width='{STROKE_WIDTH}' />"
    )
    panel_h = icon_size * 0.2
    svg.append(
        f"<line x1='{icon_x}' y1='{icon_y + panel_h}' x2='{icon_x + icon_size}' y2='{icon_y + panel_h}' "
        f"stroke='{stroke}' stroke-width='{thin}' />"
    )
    svg.append(
        f"<circle cx='{icon_x + icon_size * 0.18}' cy='{icon_y + panel_h * 0.5}' r='{max(1.3, icon_size * 0.035)}' "
        f"fill='none' stroke='{secondary_stroke}' stroke-width='{thin}' />"
    )
    svg.append(
        f"<circle cx='{icon_x + icon_size * 0.32}' cy='{icon_y + panel_h * 0.5}' r='{max(1.1, icon_size * 0.028)}' "
        f"fill='{secondary_stroke}' />"
    )
    rack_y = icon_y + panel_h + icon_size * 0.16
    for offset in (0.0, 0.13, 0.26):
        svg.append(
            f"<line x1='{icon_x + icon_size * 0.18}' y1='{rack_y + icon_size * offset}' "
            f"x2='{icon_x + icon_size * 0.82}' y2='{rack_y + icon_size * offset}' "
            f"stroke='{secondary_stroke}' stroke-width='{thin}' stroke-linecap='round' />"
        )
    for ratio in (0.28, 0.43, 0.58, 0.73):
        svg.append(
            f"<line x1='{icon_x + icon_size * ratio}' y1='{rack_y - icon_size * 0.04}' "
            f"x2='{icon_x + icon_size * ratio}' y2='{rack_y + icon_size * 0.31}' "
            f"stroke='{secondary_stroke}' stroke-width='{max(0.6, thin * 0.75)}' stroke-linecap='round' />"
        )
    svg.append(
        f"<path d='M {icon_x + icon_size * 0.22:.1f} {icon_y + icon_size * 0.68:.1f} "
        f"C {icon_x + icon_size * 0.38:.1f} {icon_y + icon_size * 0.58:.1f}, "
        f"{icon_x + icon_size * 0.54:.1f} {icon_y + icon_size * 0.78:.1f}, "
        f"{icon_x + icon_size * 0.78:.1f} {icon_y + icon_size * 0.64:.1f}' "
        f"fill='none' stroke='{secondary_stroke}' stroke-width='{thin}' stroke-linecap='round' />"
    )


def append_plinth_vent(svg: list[str], *, x: int, y: int, w: int, h: int) -> None:
    if w <= 24 or h <= 8:
        return

    vent_w = min(w * 0.68, 92)
    vent_h = max(3, min(6, h * 0.18))
    gap = max(3, vent_h * 0.8)
    total_h = vent_h * 2 + gap
    start_x = x + (w - vent_w) / 2
    start_y = y + (h - total_h) / 2

    for index in range(2):
        slot_y = start_y + index * (vent_h + gap)
        svg.append(
            f"<rect x='{start_x:.1f}' y='{slot_y:.1f}' width='{vent_w:.1f}' height='{vent_h:.1f}' "
            f"rx='{vent_h / 2:.1f}' fill='none' stroke='#111827' stroke-width='{max(0.8, STROKE_WIDTH * 0.8)}' />"
        )


def module_needs_plinth_vent(module: dict) -> bool:
    name = module.get("name", "")
    return (
        name in {"oven_microwave_column", "oven_column", "built_in_fridge"}
        or name == "oven_under_counter"
        or module.get("countertop_occupied_by") == "hob"
        or bool(module.get("supports_hob"))
    )


def append_under_counter_oven_markup(
    svg: list[str],
    *,
    x: int,
    y: int,
    w: int,
    h: int,
    scale: float,
) -> None:
    oven_h = min(h, int(584 * scale))
    drawer_h = max(0, h - oven_h)
    drawer_y = y
    oven_y = y
    drawer_y = y + oven_h

    if drawer_h > 0:
        drawer_height_mm = int(round(drawer_h / scale))
        svg.append(
            f"<rect x='{x}' y='{drawer_y}' width='{w}' height='{drawer_h}' fill='{MODULE_FILL}' stroke='black' stroke-width='{STROKE_WIDTH}' />"
        )
        if drawer_h >= 14:
            dim_x = x + max(16, min(w - 44, int(w * 0.78)))
            append_vertical_dimension(
                svg,
                x=dim_x,
                y1=drawer_y,
                y2=drawer_y + drawer_h,
                label=str(drawer_height_mm),
                extension_x=None,
                rotate_label=False,
                label_side="right",
            )

    if oven_h > 0:
        append_oven_face(svg, x=x, y=oven_y, w=w, h=oven_h)


def append_built_in_hood_face(svg: list[str], *, x: int, y: int, w: int, h: int, scale: float) -> None:
    lip_h = max(1, int(15 * scale))
    lip_y = y + h
    svg.append(
        f"<rect x='{x}' y='{lip_y}' width='{w}' height='{lip_h}' fill='#4b5563' stroke='black' stroke-width='{STROKE_WIDTH}' />"
    )
    inset = max(4, int(w * 0.08))
    svg.append(
        f"<line x1='{x + inset}' y1='{lip_y + max(1, lip_h // 2)}' x2='{x + w - inset}' y2='{lip_y + max(1, lip_h // 2)}' stroke='#d1d5db' stroke-width='0.8' />"
    )


def append_hob_face(svg: list[str], *, x: int, y: int, w: int, h: int, width_mm: int) -> None:
    if w <= 0 or h <= 0:
        return

    pad_x = max(4, min(12, int(w * 0.04)))
    pad_y = max(2, min(6, int(h * 0.16)))
    glass_x = x + pad_x
    glass_y = y + pad_y
    glass_w = max(1, w - pad_x * 2)
    glass_h = max(1, h - pad_y * 2)
    burner_count = 1 if width_mm <= 300 else 2

    svg.append(
        f"<rect x='{glass_x}' y='{glass_y}' width='{glass_w}' height='{glass_h}' fill='#111827' stroke='#020617' stroke-width='{STROKE_WIDTH}' />"
    )
    svg.append(
        f"<rect x='{glass_x + 3}' y='{glass_y + 3}' width='{max(1, glass_w - 6)}' height='{max(1, glass_h - 6)}' fill='none' stroke='#475569' stroke-width='0.8' opacity='0.7' />"
    )

    centers = [glass_x + glass_w / 2]
    if burner_count == 2:
        centers = [glass_x + glass_w * 0.34, glass_x + glass_w * 0.66]

    burner_y = glass_y + glass_h * 0.48
    max_radius = max(3, int(min(glass_w / (burner_count * 3), glass_h * 0.32)))
    for center_x in centers:
        svg.append(
            f"<circle cx='{center_x}' cy='{burner_y}' r='{max_radius}' fill='none' stroke='#e5e7eb' stroke-width='1.2' opacity='0.9' />"
        )
        svg.append(
            f"<circle cx='{center_x}' cy='{burner_y}' r='{max(1, int(max_radius * 0.55))}' fill='none' stroke='#94a3b8' stroke-width='0.9' opacity='0.85' />"
        )

    control_y = glass_y + glass_h - max(4, int(glass_h * 0.18))
    control_start_x = glass_x + glass_w * 0.42
    for index in range(burner_count + 1):
        svg.append(
            f"<circle cx='{control_start_x + index * max(5, int(glass_w * 0.06))}' cy='{control_y}' r='1.4' fill='#cbd5e1' opacity='0.9' />"
        )


def append_sink_faucet_face(svg: list[str], *, x: int, countertop_top_y: int, w: int) -> None:
    if w <= 0:
        return

    center_x = x + w / 2
    base_y = countertop_top_y - 24
    stroke = "#2a1a0c"
    stroke_width = 2.2
    scale_factor = max(0.32, min(0.42, w / 360))

    body_w = 20 * scale_factor
    body_h = 54 * scale_factor
    spout_h = 126 * scale_factor
    spout_w = 18 * scale_factor
    cross_w = 96 * scale_factor
    side_pipe_w = 22 * scale_factor
    lower_stem_w = max(5, 14 * scale_factor)
    lower_foot_w = 48 * scale_factor
    lower_foot_h = max(6, 12 * scale_factor)

    body_left = center_x - body_w / 2
    body_right = center_x + body_w / 2
    body_top = base_y - body_h
    stem_top = body_top - spout_h

    def p(value: float) -> str:
        return f"{value:.1f}"

    svg.append(
        f"<path d='M {p(body_left)} {p(body_top)} "
        f"L {p(body_left)} {p(stem_top + spout_w / 2)} "
        f"C {p(body_left)} {p(stem_top - spout_w * 0.55)}, {p(body_right)} {p(stem_top - spout_w * 0.55)}, {p(body_right)} {p(stem_top + spout_w / 2)} "
        f"L {p(body_right)} {p(body_top)} Z' "
        f"fill='white' stroke='{stroke}' stroke-width='{stroke_width}' stroke-linejoin='round' />"
    )
    svg.append(
        f"<rect x='{p(body_left - 2 * scale_factor)}' y='{p(body_top)}' "
        f"width='{p(body_w + 4 * scale_factor)}' height='{p(body_h)}' "
        f"fill='white' stroke='{stroke}' stroke-width='{stroke_width}' />"
    )
    svg.append(
        f"<line x1='{p(body_left - 2 * scale_factor)}' y1='{p(body_top + body_h * 0.45)}' "
        f"x2='{p(body_right + 2 * scale_factor)}' y2='{p(body_top + body_h * 0.45)}' "
        f"stroke='{stroke}' stroke-width='{stroke_width}' />"
    )
    svg.append(
        f"<path d='M {p(center_x - cross_w / 2)} {p(base_y)} "
        f"L {p(center_x - side_pipe_w)} {p(base_y)} "
        f"C {p(center_x - side_pipe_w * 0.55)} {p(base_y + 4 * scale_factor)}, {p(center_x + side_pipe_w * 0.55)} {p(base_y + 4 * scale_factor)}, {p(center_x + side_pipe_w)} {p(base_y)} "
        f"L {p(center_x + cross_w / 2)} {p(base_y)} "
        f"L {p(center_x + cross_w / 2)} {p(base_y + 28 * scale_factor)} "
        f"L {p(center_x + side_pipe_w)} {p(base_y + 28 * scale_factor)} "
        f"C {p(center_x + side_pipe_w * 0.55)} {p(base_y + 22 * scale_factor)}, {p(center_x - side_pipe_w * 0.55)} {p(base_y + 22 * scale_factor)}, {p(center_x - side_pipe_w)} {p(base_y + 28 * scale_factor)} "
        f"L {p(center_x - cross_w / 2)} {p(base_y + 28 * scale_factor)} Z' "
        f"fill='white' stroke='{stroke}' stroke-width='{stroke_width}' stroke-linejoin='round' />"
    )
    lower_stem_y = base_y + 28 * scale_factor
    lower_stem_h = max(5, 14 * scale_factor)
    svg.append(
        f"<rect x='{p(center_x - lower_stem_w / 2)}' y='{p(lower_stem_y)}' "
        f"width='{p(lower_stem_w)}' height='{p(lower_stem_h)}' "
        f"fill='white' stroke='{stroke}' stroke-width='{stroke_width}' />"
    )
    foot_y = lower_stem_y + lower_stem_h
    svg.append(
        f"<rect x='{p(center_x - lower_foot_w / 2)}' y='{p(foot_y)}' "
        f"width='{p(lower_foot_w)}' height='{p(lower_foot_h)}' "
        f"fill='white' stroke='{stroke}' stroke-width='{stroke_width}' />"
    )
    svg.append(
        f"<rect x='{p(center_x + cross_w / 2 - 16 * scale_factor)}' y='{p(base_y - 32 * scale_factor)}' "
        f"width='{p(12 * scale_factor)}' height='{p(32 * scale_factor)}' "
        f"fill='white' stroke='{stroke}' stroke-width='{stroke_width}' />"
    )
    svg.append(
        f"<rect x='{p(center_x - cross_w / 2 + 4 * scale_factor)}' y='{p(base_y - 20 * scale_factor)}' "
        f"width='{p(12 * scale_factor)}' height='{p(20 * scale_factor)}' "
        f"fill='white' stroke='{stroke}' stroke-width='{stroke_width}' />"
    )


def append_fridge_icon(svg: list[str], *, x: int, y: int, w: int, h: int, variant: str) -> None:
    if w <= 0 or h <= 0:
        return

    icon_size = max(18, min(44, int(min(w, h) * 0.28)))
    icon_x = x + (w - icon_size) / 2
    icon_y = y + (h - icon_size) / 2
    stroke = "#111111"
    secondary_stroke = "#444444"

    if variant == "freezer":
        center_x = icon_x + icon_size / 2
        center_y = icon_y + icon_size / 2
        arm = icon_size * 0.36
        for angle in (0, 60, -60):
            x1 = center_x - arm
            x2 = center_x + arm
            svg.append(
                f"<line x1='{x1}' y1='{center_y}' x2='{x2}' y2='{center_y}' "
                f"stroke='{stroke}' stroke-width='1.4' stroke-linecap='round' "
                f"transform='rotate({angle} {center_x} {center_y})' />"
            )
            branch_offset = arm * 0.58
            branch = icon_size * 0.11
            for side in (-1, 1):
                branch_x = center_x + side * branch_offset
                svg.append(
                    f"<path d='M {branch_x} {center_y} l {side * -branch} {-branch} M {branch_x} {center_y} l {side * -branch} {branch}' "
                    f"fill='none' stroke='{stroke}' stroke-width='1.0' stroke-linecap='round' "
                    f"transform='rotate({angle} {center_x} {center_y})' />"
                )
        svg.append(
            f"<circle cx='{center_x}' cy='{center_y}' r='{max(2, icon_size * 0.08)}' fill='white' stroke='{stroke}' stroke-width='1.0' />"
        )
        svg.append(
            f"<circle cx='{center_x}' cy='{center_y}' r='{max(4, icon_size * 0.42)}' fill='none' stroke='{secondary_stroke}' stroke-width='0.8' stroke-dasharray='2 3' opacity='0.7' />"
        )
        return

    svg.append(
        f"<rect x='{icon_x}' y='{icon_y}' width='{icon_size}' height='{icon_size}' fill='white' stroke='{stroke}' stroke-width='1.4' />"
    )
    for shelf_ratio in (0.34, 0.62):
        shelf_y = icon_y + icon_size * shelf_ratio
        svg.append(
            f"<line x1='{icon_x + icon_size * 0.12}' y1='{shelf_y}' x2='{icon_x + icon_size * 0.88}' y2='{shelf_y}' stroke='{stroke}' stroke-width='1.0' stroke-linecap='round' />"
        )

    bottle_x = icon_x + icon_size * 0.2
    bottle_y = icon_y + icon_size * 0.42
    bottle_w = icon_size * 0.16
    bottle_h = icon_size * 0.4
    svg.append(
        f"<rect x='{bottle_x}' y='{bottle_y}' width='{bottle_w}' height='{bottle_h}' fill='white' stroke='{secondary_stroke}' stroke-width='1.1' />"
    )
    svg.append(
        f"<rect x='{bottle_x + bottle_w * 0.25}' y='{bottle_y - icon_size * 0.12}' width='{bottle_w * 0.5}' height='{icon_size * 0.12}' fill='white' stroke='{secondary_stroke}' stroke-width='1.1' />"
    )
    box_x = icon_x + icon_size * 0.5
    box_y = icon_y + icon_size * 0.7
    svg.append(
        f"<rect x='{box_x}' y='{box_y}' width='{icon_size * 0.3}' height='{icon_size * 0.14}' fill='white' stroke='{secondary_stroke}' stroke-width='1.1' />"
    )


def append_column_section(
    svg: list[str],
    *,
    x: int,
    y: int,
    w: int,
    h: int,
    fill: str,
    label: str,
    size_label: str,
    opening: str | None = None,
    hinge_side: str = "right",
) -> None:
    if h <= 0:
        return

    svg.append(
        f"<rect x='{x}' y='{y}' width='{w}' height='{h}' fill='{MODULE_FILL}' stroke='black' stroke-width='{STROKE_WIDTH}' />"
    )

    if label == "microwave":
        append_microwave_face(svg, x=x, y=y, w=w, h=h)
    elif label == "oven":
        append_oven_face(svg, x=x, y=y, w=w, h=h)
    elif label in {"fridge", "freezer"}:
        append_fridge_icon(svg, x=x, y=y, w=w, h=h, variant=label)

    if opening == "lift":
        append_lift_opening_mark(svg, x=x, y=y, w=w, h=h)
    elif opening == "mezzanine":
        if w >= h:
            append_lift_opening_mark(svg, x=x, y=y, w=w, h=h)
        else:
            append_hinged_opening_mark(svg, x=x, y=y, w=w, h=h, hinge_side=hinge_side)
    elif opening == "hinged":
        append_hinged_opening_mark(svg, x=x, y=y, w=w, h=h, hinge_side=hinge_side)


def render_tall_column_markup(
    svg: list[str],
    *,
    module: dict,
    x: int,
    y: int,
    w: int,
    baseline_y: int,
    scale: float,
    kitchen_height_mm: int,
    plinth_height_mm: int,
    mezzanine_height_mm: int,
    wall_panel_top_mm: int,
    margin: int,
    wall_length_mm: int,
    barrier_xs: list[int] | None = None,
) -> None:
    name = module.get("name")
    column_hinge_side = nearest_barrier_hinge_side(
        x=x,
        w=w,
        wall_length_px=int(wall_length_mm * scale),
        margin=margin,
        barrier_xs=barrier_xs,
    )

    def y_from_floor(y_mm: int) -> int:
        return baseline_y - int(y_mm * scale)

    def section_rect(bottom_mm: int, height_mm: int) -> tuple[int, int]:
        top_mm = bottom_mm + height_mm
        y = y_from_floor(top_mm)
        return y, y_from_floor(bottom_mm) - y

    if name == "freestanding_fridge_in_carcass":
        body_width_mm = int(module.get("body_width_mm", module.get("width_mm", 600)))
        body_height_mm = int(module.get("body_height_mm", 2000))
        gap_mm = int(module.get("gap_mm", 20))
        side_width_mm = int(module.get("carcass_side_width_mm", 20))
        fridge_x = x + int((side_width_mm + gap_mm) * scale)
        fridge_w = int(body_width_mm * scale)
        side_w = max(1, int(side_width_mm * scale))
        top_panel_h = max(1, int(side_width_mm * scale))
        carcass_height_mm = min(
            kitchen_height_mm,
            body_height_mm + gap_mm + side_width_mm,
        )
        carcass_y, carcass_h = section_rect(0, carcass_height_mm)
        fridge_y, fridge_h = section_rect(0, min(body_height_mm, kitchen_height_mm))
        mezzanine_bottom_mm = max(0, kitchen_height_mm - mezzanine_height_mm)
        upper_bottom_mm = carcass_height_mm
        upper_height_mm = max(0, mezzanine_bottom_mm - upper_bottom_mm)

        svg.append(
            f"<rect x='{x}' y='{carcass_y}' width='{w}' height='{carcass_h}' fill='{MODULE_FILL}' stroke='black' stroke-width='{STROKE_WIDTH}' />"
        )
        svg.append(
            f"<rect x='{x}' y='{carcass_y}' width='{side_w}' height='{carcass_h}' fill='{MODULE_FILL}' stroke='black' stroke-width='{STROKE_WIDTH}' />"
        )
        svg.append(
            f"<rect x='{x + w - side_w}' y='{carcass_y}' width='{side_w}' height='{carcass_h}' fill='{MODULE_FILL}' stroke='black' stroke-width='{STROKE_WIDTH}' />"
        )
        top_panel_y = baseline_y - int(carcass_height_mm * scale)
        svg.append(
            f"<rect x='{x}' y='{top_panel_y}' width='{w}' height='{top_panel_h}' fill='{MODULE_FILL}' stroke='black' stroke-width='{STROKE_WIDTH}' />"
        )
        svg.append(
            f"<rect x='{fridge_x}' y='{fridge_y}' width='{fridge_w}' height='{fridge_h}' fill='{MODULE_FILL}' stroke='black' stroke-width='{STROKE_WIDTH}' />"
        )
        append_fridge_icon(svg, x=fridge_x, y=fridge_y, w=fridge_w, h=fridge_h, variant="fridge")

        if upper_height_mm > 0:
            section_y, section_h = section_rect(upper_bottom_mm, upper_height_mm)
            append_column_section(
                svg,
                x=x,
                y=section_y,
                w=w,
                h=section_h,
                fill="#d1d5db",
                label="hinged",
                size_label=f"{upper_height_mm} mm",
                opening="lift",
            )

        if mezzanine_height_mm > 0:
            section_y, section_h = section_rect(mezzanine_bottom_mm, mezzanine_height_mm)
            append_column_section(
                svg,
                x=x,
                y=section_y,
                w=w,
                h=section_h,
                fill="#c7d2fe",
                label="mezzanine",
                size_label=f"{mezzanine_height_mm} mm",
                opening="mezzanine",
            )

    if name == "built_in_fridge":
        freezer_height_mm = 723
        freezer_bottom_mm = plinth_height_mm
        freezer_top_mm = freezer_bottom_mm + freezer_height_mm
        mezzanine_bottom_mm = max(plinth_height_mm, kitchen_height_mm - mezzanine_height_mm)
        fridge_height_mm = max(0, mezzanine_bottom_mm - freezer_top_mm)

        sections = [
            (freezer_bottom_mm, freezer_height_mm, "#bfdbfe", "freezer", f"{freezer_height_mm} mm"),
            (freezer_top_mm, fridge_height_mm, "#dbeafe", "fridge", f"{fridge_height_mm} mm"),
            (mezzanine_bottom_mm, mezzanine_height_mm, "#c7d2fe", "mezzanine", f"{mezzanine_height_mm} mm"),
        ]

        for bottom_mm, height_mm, fill, label, size_label in sections:
            section_y, section_h = section_rect(bottom_mm, height_mm)
            append_column_section(
                svg,
                x=x,
                y=section_y,
                w=w,
                h=section_h,
                fill=fill,
                label=label,
                size_label=size_label,
                opening="mezzanine" if label == "mezzanine" else None,
                hinge_side=column_hinge_side,
            )

    if name == "oven_microwave_column":
        oven_height_mm = 584
        microwave_height_mm = int(module.get("microwave_height_mm", 400))
        mezzanine_bottom_mm = max(plinth_height_mm, kitchen_height_mm - mezzanine_height_mm)
        microwave_top_mm = min(wall_panel_top_mm, mezzanine_bottom_mm)
        microwave_bottom_mm = microwave_top_mm - microwave_height_mm
        oven_bottom_mm = microwave_bottom_mm - oven_height_mm
        drawer_bottom_mm = plinth_height_mm
        drawer_height_mm = max(0, oven_bottom_mm - drawer_bottom_mm)
        swing_bottom_mm = microwave_top_mm
        swing_height_mm = max(0, mezzanine_bottom_mm - swing_bottom_mm)

        sections = [
            (drawer_bottom_mm, drawer_height_mm, "#e5e7eb", "drawer", f"{drawer_height_mm} mm"),
            (oven_bottom_mm, oven_height_mm, "#fecaca", "oven", f"{oven_height_mm} mm"),
            (microwave_bottom_mm, microwave_height_mm, "#fde68a", "microwave", f"{microwave_height_mm} mm"),
            (swing_bottom_mm, swing_height_mm, "#d1d5db", "hinged", f"{swing_height_mm} mm"),
            (mezzanine_bottom_mm, mezzanine_height_mm, "#c7d2fe", "mezzanine", f"{mezzanine_height_mm} mm"),
        ]

        for bottom_mm, height_mm, fill, label, size_label in sections:
            section_y, section_h = section_rect(bottom_mm, height_mm)
            append_column_section(
                svg,
                x=x,
                y=section_y,
                w=w,
                h=section_h,
                fill=fill,
                label=label,
                size_label=size_label,
                opening=(
                    "hinged"
                    if label == "hinged"
                    else "mezzanine"
                    if label == "mezzanine"
                    else None
                ),
                hinge_side=column_hinge_side if label in {"hinged", "mezzanine"} else "right",
            )


def append_lower_profile_handles(
    svg: list[str],
    *,
    modules: list[dict],
    margin: int,
    scale: float,
    handle_top_y: int,
    handle_height_mm: int,
) -> None:
    handle_height_px = max(1, int(handle_height_mm * scale))
    sorted_modules = sorted(modules, key=lambda module: module.get("x_mm", 0))
    current_x = None
    current_width = 0

    def flush() -> None:
        if current_x is None or current_width <= 0:
            return

        x = margin + int(current_x * scale)
        w = int(current_width * scale)
        svg.append(
            f"<rect x='{x}' y='{handle_top_y}' width='{w}' height='{handle_height_px}' fill='#4b5563' fill-opacity='0.85' stroke='#111827' stroke-width='{STROKE_WIDTH}' />"
        )

    for module in sorted_modules:
        if (
            module.get("type") != "base"
            or module.get("corner_module")
        ):
            flush()
            current_x = None
            current_width = 0
            continue

        module_x = module.get("x_mm", 0)
        module_width = module.get("width_mm", 0)

        if current_x is None:
            current_x = module_x
            current_width = module_width
            continue

        if module_x == current_x + current_width:
            current_width += module_width
        else:
            flush()
            current_x = module_x
            current_width = module_width

    flush()


def is_drawer_filler_module(module: dict) -> bool:
    name = module.get("name", "")
    return bool(
        module.get("type") == "base"
        and module.get("is_generated_filler")
        and (
            name == "cutlery_drawer"
            or (isinstance(name, str) and name.startswith("drawer_"))
        )
    )


def append_drawer_filler_profile_handles(
    svg: list[str],
    *,
    modules: list[dict],
    margin: int,
    scale: float,
    base_top_y: int,
    base_height_mm: int,
    handle_height_mm: int,
) -> None:
    handle_height_px = max(1, int(handle_height_mm * scale))
    base_height_px = int(base_height_mm * scale)
    handle_y = base_top_y + max(0, int((base_height_px - handle_height_px) / 2))

    for module in modules:
        if not is_drawer_filler_module(module):
            continue

        x = margin + int(module.get("x_mm", 0) * scale)
        x2 = margin + int(
            (module.get("x_mm", 0) + module.get("width_mm", 0)) * scale
        )
        w = x2 - x
        if w <= 0:
            continue

        svg.append(
            f"<rect x='{x}' y='{handle_y}' width='{w}' height='{handle_height_px}' fill='#4b5563' fill-opacity='0.85' stroke='#111827' stroke-width='{STROKE_WIDTH}' />"
        )


def append_tall_profile_handles(
    svg: list[str],
    *,
    modules: list[dict],
    margin: int,
    scale: float,
    baseline_y: int,
    kitchen_height_mm: int,
    plinth_height_mm: int,
) -> None:
    tall_types = {"tall", "appliance_tall"}
    sorted_modules = sorted(modules, key=lambda module: module.get("x_mm", 0))
    handle_width_mm = 50
    handle_width_px = max(1, int(handle_width_mm * scale))
    handle_top_y = baseline_y - int(kitchen_height_mm * scale)
    handle_bottom_y = baseline_y - int(plinth_height_mm * scale)
    handle_height_px = handle_bottom_y - handle_top_y
    handle_boundaries = set()

    for index, module in enumerate(sorted_modules):
        if module.get("type") not in tall_types:
            continue

        module_x = module.get("x_mm", 0)
        module_end = module_x + module.get("width_mm", 0)
        previous_module = sorted_modules[index - 1] if index > 0 else None
        next_module = sorted_modules[index + 1] if index + 1 < len(sorted_modules) else None
        has_tall_neighbor = False

        if (
            previous_module
            and previous_module.get("type") in tall_types
            and previous_module.get("x_mm", 0) + previous_module.get("width_mm", 0) == module_x
        ):
            handle_boundaries.add(module_x)
            has_tall_neighbor = True

        if (
            next_module
            and next_module.get("type") in tall_types
            and module_end == next_module.get("x_mm", 0)
        ):
            handle_boundaries.add(module_end)
            has_tall_neighbor = True

        if has_tall_neighbor:
            continue

        if (
            previous_module
            and previous_module.get("x_mm", 0) + previous_module.get("width_mm", 0) == module_x
        ):
            handle_boundaries.add(module_x)
        elif next_module and module_end == next_module.get("x_mm", 0):
            handle_boundaries.add(module_end)

    for boundary_mm in sorted(handle_boundaries):
        x = margin + int((boundary_mm - handle_width_mm / 2) * scale)
        svg.append(
            f"<rect x='{x}' y='{handle_top_y}' width='{handle_width_px}' height='{handle_height_px}' fill='#374151' fill-opacity='0.88' stroke='#111827' stroke-width='{STROKE_WIDTH}' />"
        )


def _corner_side_layout(layout: dict, side_key: str) -> dict:
    side = layout.get(side_key, {})
    side_width_mm = side.get("wall_length_mm", layout.get("wall_length_mm", 3000))
    modules = side.get("modules", [])
    wall_modules = side.get("wall_modules", [])
    front_objects = side.get("front_objects", [])
    plinth_modules = side.get("plinth_modules", [])
    countertop_modules = side.get("countertop_modules", [])
    wall_panel_modules = side.get("wall_panel_modules", [])

    side_layout = {
        **layout,
        "shape": "straight",
        "is_corner_side": True,
        "corner_side_key": side_key,
        "wall_length_mm": side_width_mm,
        "used_width_mm": max(
            [
                module.get("x_mm", 0) + module.get("width_mm", 0)
                for module in modules
            ]
            or [0]
        ),
        "modules": modules,
        "wall_modules": wall_modules,
        "front_objects": front_objects,
        "plinth_modules": plinth_modules,
        "countertop_modules": countertop_modules,
        "wall_panel_modules": wall_panel_modules,
        "corner_projection": _make_corner_projection(layout, side_key),
    }

    return side_layout


def append_front_view_dimensions(
    svg: list[str],
    *,
    layout: dict,
    margin: int,
    scale: float,
    baseline_y: int,
    base_top_y: int,
    base_bottom_y: int,
    plinth_height_mm: int,
    lower_profile_handle_height_mm: int,
    wall_panel_height_mm: int,
    kitchen_height_mm: int,
) -> None:
    def is_tall_dimension_module(module: dict | None) -> bool:
        if not module:
            return False
        return module.get("type") in {"tall", "appliance_tall"} or module.get("name") in {
            "built_in_fridge",
            "freestanding_fridge_in_carcass",
            "oven_microwave_column",
            "microwave_column",
            "oven_column",
            "corner_tall",
        }

    def edge_modules() -> tuple[dict | None, dict | None]:
        candidates = [
            module
            for module in layout.get("modules", [])
            if module.get("width_mm", 0) > 0 and module.get("type") != "profile_handle"
        ]
        if not candidates:
            return None, None

        left_module = min(candidates, key=lambda item: item.get("x_mm", 0))
        right_module = max(
            candidates,
            key=lambda item: item.get("x_mm", 0) + item.get("width_mm", 0),
        )
        return left_module, right_module

    def column_section_ranges(module: dict) -> list[tuple[int, int, int]]:
        name = module.get("name")
        column_height_mm = int(module.get("height_mm", kitchen_height_mm))
        mezzanine_height_mm = get_mezzanine_height_mm(layout)
        countertop_thickness_mm = int(layout.get("countertop_thickness_mm", 38))
        base_module_height_mm = int(layout.get("base_module_height_mm", 0))
        wall_panel_top_mm = (
            plinth_height_mm
            + base_module_height_mm
            + lower_profile_handle_height_mm
            + countertop_thickness_mm
            + wall_panel_height_mm
        )

        if name == "built_in_fridge":
            freezer_height_mm = 723
            freezer_bottom_mm = plinth_height_mm
            freezer_top_mm = freezer_bottom_mm + freezer_height_mm
            mezzanine_bottom_mm = max(plinth_height_mm, column_height_mm - mezzanine_height_mm)
            fridge_height_mm = max(0, mezzanine_bottom_mm - freezer_top_mm)

            return [
                (freezer_bottom_mm, freezer_bottom_mm + freezer_height_mm, freezer_height_mm),
                (freezer_top_mm, freezer_top_mm + fridge_height_mm, fridge_height_mm),
                (mezzanine_bottom_mm, mezzanine_bottom_mm + mezzanine_height_mm, mezzanine_height_mm),
            ]

        if name == "oven_microwave_column":
            oven_height_mm = 584
            microwave_height_mm = int(module.get("microwave_height_mm", 400))
            mezzanine_bottom_mm = max(plinth_height_mm, column_height_mm - mezzanine_height_mm)
            microwave_top_mm = min(wall_panel_top_mm, mezzanine_bottom_mm)
            microwave_bottom_mm = microwave_top_mm - microwave_height_mm
            oven_bottom_mm = microwave_bottom_mm - oven_height_mm
            drawer_bottom_mm = plinth_height_mm
            drawer_height_mm = max(0, oven_bottom_mm - drawer_bottom_mm)
            swing_bottom_mm = microwave_top_mm
            swing_height_mm = max(0, mezzanine_bottom_mm - swing_bottom_mm)

            return [
                (drawer_bottom_mm, drawer_bottom_mm + drawer_height_mm, drawer_height_mm),
                (oven_bottom_mm, oven_bottom_mm + oven_height_mm, oven_height_mm),
                (microwave_bottom_mm, microwave_top_mm, microwave_height_mm),
                (swing_bottom_mm, swing_bottom_mm + swing_height_mm, swing_height_mm),
                (mezzanine_bottom_mm, mezzanine_bottom_mm + mezzanine_height_mm, mezzanine_height_mm),
            ]

        return []

    def append_column_edge_dimensions(module: dict, *, side: str) -> None:
        sections = [
            section
            for section in column_section_ranges(module)
            if section[2] > 0
        ]
        if not sections:
            return

        module_x = margin + int(module.get("x_mm", 0) * scale)
        module_right_x = module_x + int(module.get("width_mm", 0) * scale)
        anchor_x = module_x if side == "left" else module_right_x
        dim_x = max(14, anchor_x - 34) if side == "left" else anchor_x + 34

        for bottom_mm, top_mm, height_mm in sections:
            append_vertical_dimension(
                svg,
                x=dim_x,
                y1=baseline_y - int(top_mm * scale),
                y2=baseline_y - int(bottom_mm * scale),
                label=str(height_mm),
                extension_x=anchor_x,
            )

    left_edge_module, right_edge_module = edge_modules()
    left_edge_is_tall = is_tall_dimension_module(left_edge_module)
    right_edge_is_tall = is_tall_dimension_module(right_edge_module)

    lower_y = baseline_y + 34
    lower_modules = [
        module
        for module in layout.get("modules", [])
        if module.get("width_mm", 0) > 0
    ]
    for module in lower_modules:
        x1 = margin + int(module["x_mm"] * scale)
        x2 = x1 + int(module["width_mm"] * scale)
        append_horizontal_dimension(
            svg,
            x1=x1,
            x2=x2,
            y=lower_y,
            label=str(module["width_mm"]),
            extension_y=baseline_y,
        )

    handle_top_y = base_top_y - int(lower_profile_handle_height_mm * scale)
    countertop_top_y = handle_top_y - int(layout.get("countertop_thickness_mm", 38) * scale)
    upper_segments = {}
    for module in layout.get("wall_modules", []):
        if module.get("tier") == "ceiling_filler":
            continue
        if module.get("width_mm", 0) <= 0:
            continue
        x1 = margin + int(module["x_mm"] * scale)
        x2 = margin + int((module["x_mm"] + module["width_mm"]) * scale)
        y_mm = module.get("y_mm", 1450)
        module_bottom_y = baseline_y - int(y_mm * scale)
        module_top_y = baseline_y - int((y_mm + module.get("height_mm", 400)) * scale)
        key = (x1, x2)
        if key not in upper_segments or module_top_y < upper_segments[key][2]:
            upper_segments[key] = (module_bottom_y, module_top_y, module["width_mm"])

    upper_dimensions = [
        (x1, x2, bottom_y, top_y, width_mm)
        for (x1, x2), (bottom_y, top_y, width_mm) in upper_segments.items()
    ]
    projection = layout.get("corner_projection") or {}
    if projection.get("other_has_upper"):
        wall_length_mm = layout.get("wall_length_mm", 3000)
        depth_mm = int(projection.get("depth_mm", 340))
        projection_width_mm = min(depth_mm, wall_length_mm)
        corner_position = projection.get(
            "corner_position", layout.get("corner_position", "left")
        )
        x_mm = (
            0
            if corner_position == "left"
            else max(0, wall_length_mm - projection_width_mm)
        )
        upper_projection_width_mm = 350
        false_panel_width_mm = int(projection.get("false_panel_width_mm", 50))
        false_x_mm = (
            x_mm + upper_projection_width_mm
            if corner_position == "left"
            else x_mm
            + projection_width_mm
            - upper_projection_width_mm
            - false_panel_width_mm
        )
        x1 = margin + int(false_x_mm * scale)
        x2 = margin + int((false_x_mm + false_panel_width_mm) * scale)
        upper_bottom_mm = int(projection.get("upper_bottom_mm", 1450))
        false_bottom_y = baseline_y - int(upper_bottom_mm * scale)
        false_top_y = baseline_y - int(kitchen_height_mm * scale)
        upper_dimensions.append(
            (x1, x2, false_bottom_y, false_top_y, false_panel_width_mm)
        )

    upper_dimension_y = None
    kitchen_top_y = baseline_y - int(kitchen_height_mm * scale)
    has_ceiling_filler = any(
        module.get("tier") == "ceiling_filler"
        for module in layout.get("wall_modules", [])
    )
    if upper_dimensions:
        upper_dimension_y = min(min(item[3] for item in upper_dimensions) - 14, kitchen_top_y - 18)

    for x1, x2, _module_bottom_y, module_top_y, width_mm in upper_dimensions:
        extension_y = kitchen_top_y if has_ceiling_filler else module_top_y
        append_horizontal_dimension(
            svg,
            x1=x1,
            x2=x2,
            y=upper_dimension_y,
            label=str(width_mm),
            extension_y=extension_y,
        )

    min_furniture_x_mm = 0
    min_candidates = [
        int(module.get("x_mm", 0))
        for module in layout.get("modules", [])
        if module.get("type") != "profile_handle"
    ]
    min_candidates.extend(
        int(module.get("x_mm", 0))
        for module in layout.get("wall_modules", [])
        if module.get("tier") != "ceiling_filler"
    )
    if min_candidates:
        min_furniture_x_mm = min(min_candidates)
    furniture_left_x = margin + int(min_furniture_x_mm * scale)

    if upper_dimensions:
        left_x = min(furniture_left_x, min(item[0] for item in upper_dimensions))
        top_y = min(item[3] for item in upper_dimensions)
        bottom_y = max(item[2] for item in upper_dimensions)
    else:
        left_x = furniture_left_x
        top_y = baseline_y - int(kitchen_height_mm * scale)
        bottom_y = base_top_y - int(wall_panel_height_mm * scale)

    use_right_generic_dimensions = False
    if layout.get("is_corner_side"):
        projection = layout.get("corner_projection") or {}
        tall_projection_on_right = (
            projection.get("corner_position") == "right"
            and projection.get("other_has_tall")
        )
        tall_projection_on_left = (
            projection.get("corner_position") == "left"
            and projection.get("other_has_tall")
        )

        if left_edge_is_tall and not right_edge_is_tall:
            use_right_generic_dimensions = True
        elif right_edge_is_tall and not left_edge_is_tall:
            use_right_generic_dimensions = False
        else:
            use_right_generic_dimensions = layout.get("corner_side_key") == "side_2"

        if use_right_generic_dimensions and tall_projection_on_right:
            use_right_generic_dimensions = False
        elif not use_right_generic_dimensions and tall_projection_on_left:
            use_right_generic_dimensions = True

    dimension_anchor_x = left_x
    dimension_x = max(14, left_x - (78 if layout.get("is_corner_side") else 58))
    if use_right_generic_dimensions:
        right_candidates = [
            margin + int((module.get("x_mm", 0) + module.get("width_mm", 0)) * scale)
            for module in layout.get("modules", [])
            if module.get("type") != "profile_handle"
        ]
        right_candidates.extend(
            margin + int((module.get("x_mm", 0) + module.get("width_mm", 0)) * scale)
            for module in layout.get("wall_modules", [])
            if module.get("tier") != "ceiling_filler"
        )
        right_x = max(right_candidates or [margin + int(layout.get("wall_length_mm", 0) * scale)])
        dimension_anchor_x = right_x
        dimension_x = right_x + 54

    if layout.get("is_corner_side"):
        projection = layout.get("corner_projection") or {}
        tall_projection_on_right = (
            projection.get("corner_position") == "right"
            and projection.get("other_has_tall")
        )
        tall_projection_on_left = (
            projection.get("corner_position") == "left"
            and projection.get("other_has_tall")
        )

        if left_edge_is_tall and left_edge_module and not tall_projection_on_left:
            append_column_edge_dimensions(left_edge_module, side="left")
        if (
            right_edge_is_tall
            and right_edge_module
            and right_edge_module is not left_edge_module
            and not tall_projection_on_right
        ):
            append_column_edge_dimensions(right_edge_module, side="right")
    ceiling_filler_height_mm = get_ceiling_filler_height_mm(layout)
    ceiling_bottom_y = baseline_y - int(
        (kitchen_height_mm - ceiling_filler_height_mm) * scale
    )
    append_vertical_dimension(
        svg,
        x=dimension_x,
        y1=baseline_y - int(kitchen_height_mm * scale),
        y2=baseline_y,
        label=str(kitchen_height_mm),
        extension_x=dimension_anchor_x,
    )
    append_vertical_dimension(
        svg,
        x=dimension_x + 24,
        y1=base_top_y,
        y2=base_bottom_y,
        label=str(layout.get("base_module_height_mm", 0)),
        extension_x=dimension_anchor_x,
    )
    append_vertical_dimension(
        svg,
        x=dimension_x + 24,
        y1=base_bottom_y,
        y2=baseline_y,
        label=str(plinth_height_mm),
        extension_x=dimension_anchor_x,
    )
    append_vertical_dimension(
        svg,
        x=dimension_x + 24,
        y1=handle_top_y,
        y2=base_top_y,
        label=str(lower_profile_handle_height_mm),
        extension_x=dimension_anchor_x,
        rotate_label=False,
    )
    append_vertical_dimension(
        svg,
        x=dimension_x + 24,
        y1=countertop_top_y,
        y2=handle_top_y,
        label=str(layout.get("countertop_thickness_mm", 38)),
        extension_x=dimension_anchor_x,
        rotate_label=False,
    )
    append_vertical_dimension(
        svg,
        x=dimension_x + 24,
        y1=countertop_top_y - int(wall_panel_height_mm * scale),
        y2=countertop_top_y,
        label=str(wall_panel_height_mm),
        extension_x=dimension_anchor_x,
    )
    if upper_dimensions:
        if ceiling_filler_height_mm > 0:
            append_vertical_dimension(
                svg,
                x=dimension_x + 24,
                y1=baseline_y - int(kitchen_height_mm * scale),
                y2=ceiling_bottom_y,
                label=str(ceiling_filler_height_mm),
                extension_x=dimension_anchor_x,
            )
        mezzanine_split_candidates = []
        for module in layout.get("wall_modules", []):
            if "mezzanine" not in module.get("name", ""):
                continue
            mezzanine_split_candidates.append(
                baseline_y - int(module.get("y_mm", 0) * scale)
            )

        mezzanine_split_y = (
            min(mezzanine_split_candidates) if mezzanine_split_candidates else None
        )
        if mezzanine_split_y is not None and top_y < mezzanine_split_y < bottom_y:
            append_vertical_dimension(
                svg,
                x=dimension_x + 24,
                y1=top_y,
                y2=mezzanine_split_y,
                label=str(int(round((mezzanine_split_y - top_y) / scale))),
                extension_x=dimension_anchor_x,
            )
            append_vertical_dimension(
                svg,
                x=dimension_x + 24,
                y1=mezzanine_split_y,
                y2=bottom_y,
                label=str(int(round((bottom_y - mezzanine_split_y) / scale))),
                extension_x=dimension_anchor_x,
            )
        else:
            append_vertical_dimension(
                svg,
                x=dimension_x + 24,
                y1=top_y,
                y2=bottom_y,
                label=str(int(round((bottom_y - top_y) / scale))),
                extension_x=dimension_anchor_x,
            )


def render_front_view(layout: dict) -> str:
    if layout.get("shape") == "corner":
        return render_front_view(_corner_side_layout(layout, "side_1"))

    scale = 0.25
    margin = 140 if layout.get("is_corner_side") else 92

    base_height_mm = layout.get("base_module_height_mm", 720)
    plinth_height_mm = layout.get("plinth_height_mm", 100)
    lower_profile_handle_height_mm = layout.get(
        "lower_profile_handle_height_mm",
        LOWER_PROFILE_HANDLE_HEIGHT_MM,
    )
    kitchen_height_mm = layout.get("kitchen_height_mm", 2700)
    wall_panel_height_mm = 600

    display_length_mm = max(
        layout.get("wall_length_mm", 3000),
        layout.get("used_width_mm", 0),
    )

    content_width_px = int(display_length_mm * scale)
    dimension_canvas_padding_right = 90 if layout.get("is_corner_side") else 0
    width_px = content_width_px + margin * 2 + dimension_canvas_padding_right
    header_height = 104
    baseline_y = header_height + int(kitchen_height_mm * scale)
    height_px = baseline_y + 70

    svg = []
    svg.append(f"<svg xmlns='http://www.w3.org/2000/svg' width='{width_px}' height='{height_px}'>")
    append_dimension_defs(svg)
    svg.append("<rect width='100%' height='100%' fill='white' />")
    svg.append(f"<text x='{margin}' y='24' font-size='16' font-family='Arial'>Front View</text>")
    svg.append(
        f"<text x='{margin}' y='44' font-size='12' font-family='Arial'>Countertop height: {layout.get('countertop_height_mm', 0)} mm | Base modules: {layout.get('base_module_height_mm', 0)} mm | Plinth: {layout.get('plinth_height_mm', 0)} mm</text>"
    )

    base_height_px = int(base_height_mm * scale)
    plinth_height_px = int(plinth_height_mm * scale)
    lower_profile_handle_height_px = int(lower_profile_handle_height_mm * scale)
    base_bottom_y = baseline_y - plinth_height_px
    base_top_y = base_bottom_y - base_height_px
    handle_top_y = base_top_y - lower_profile_handle_height_px

    global_countertop_thickness_px = int(
        layout.get("countertop_thickness_mm", 38) * scale
    )
    mezzanine_height_mm = get_mezzanine_height_mm(layout)
    wall_panel_top_mm = (
        plinth_height_mm
        + base_height_mm
        + lower_profile_handle_height_mm
        + layout.get("countertop_thickness_mm", 38)
        + wall_panel_height_mm
    )
    tall_barrier_xs = tall_barrier_edges_px(
        layout.get("modules", []),
        margin=margin,
        scale=scale,
    )

    # Стеновая панель.
    # Она отображается только над нижними base-модулями,
    # не строится за пенальными группами
    # и физически находится за столешницей и за соло-микроволновкой.
    wall_border_lines = set()
    suppressed_opening_rects = []

    def add_wall_border_line(x1: int, y1: int, x2: int, y2: int) -> None:
        line = (x1, y1, x2, y2)
        reverse_line = (x2, y2, x1, y1)
        if reverse_line in wall_border_lines:
            return
        wall_border_lines.add(line)

    for panel in layout.get("wall_panel_modules", []):
        x = margin + int(panel["x_mm"] * scale)
        w = int(panel["width_mm"] * scale)
        h = int(wall_panel_height_mm * scale)

        countertop_thickness_px = int(
            panel.get(
                "countertop_thickness_mm",
                layout.get("countertop_thickness_mm", 38),
            )
            * scale
        )

        y = handle_top_y - countertop_thickness_px - h

        svg.append(
            f"<rect x='{x}' y='{y}' width='{w}' height='{h}' fill='{WALL_PANEL_FILL}' stroke='black' stroke-width='{STROKE_WIDTH}' stroke-dasharray='4 3' />"
        )

    # Верхние модули и вытяжка
    profile_handle_edges = set()
    for module in layout.get("modules", []):
        if module.get("type") != "profile_handle":
            continue

        handle_x = margin + int(module["x_mm"] * scale)
        handle_w = int(module["width_mm"] * scale)
        profile_handle_edges.add(handle_x)
        profile_handle_edges.add(handle_x + handle_w)

    suppressed_wall_edges = set()
    projection = layout.get("corner_projection") or {}
    if projection.get("other_has_upper"):
        depth_mm = int(projection.get("depth_mm", 340))
        wall_length_mm = layout.get("wall_length_mm", 3000)
        projection_width_mm = min(depth_mm, wall_length_mm)
        corner_position = projection.get(
            "corner_position", layout.get("corner_position", "left")
        )
        x_mm = (
            0
            if corner_position == "left"
            else max(0, wall_length_mm - projection_width_mm)
        )
        upper_projection_width_mm = 350
        false_panel_width_mm = int(projection.get("false_panel_width_mm", 50))
        false_x_mm = (
            x_mm + upper_projection_width_mm
            if corner_position == "left"
            else x_mm
            + projection_width_mm
            - upper_projection_width_mm
            - false_panel_width_mm
        )
        visible_join_mm = (
            false_x_mm + false_panel_width_mm
            if corner_position == "left"
            else false_x_mm
        )
        suppressed_wall_edges.add(margin + int(visible_join_mm * scale))

    for module in layout.get("wall_modules", []):
        if module.get("tier") == "ceiling_filler":
            continue
        x = margin + int(module["x_mm"] * scale)
        x2 = margin + int((module["x_mm"] + module["width_mm"]) * scale)
        w = x2 - x
        y_mm = module.get("y_mm", 1450)
        y = baseline_y - int((y_mm + module.get("height_mm", 400)) * scale)
        bottom_y = baseline_y - int(y_mm * scale)
        h = bottom_y - y

        fill = MODULE_FILL

        svg.append(
            f"<rect x='{x}' y='{y}' width='{w}' height='{h}' fill='{fill}' stroke='none' />"
        )
        if module.get("name") == "built_in_hood":
            append_built_in_hood_face(svg, x=x, y=y, w=w, h=h, scale=scale)
        if module.get("name") == "built_in_microwave":
            append_microwave_face(svg, x=x, y=y, w=w, h=h)
        add_wall_border_line(x, y, x + w, y)
        add_wall_border_line(x, y + h, x + w, y + h)
        if module.get("suppress_opening_marks"):
            suppressed_opening_rects.append((x, y, w, h))
        if x not in profile_handle_edges and x not in suppressed_wall_edges:
            add_wall_border_line(x, y, x, y + h)
        if x + w not in profile_handle_edges and x + w not in suppressed_wall_edges:
            add_wall_border_line(x + w, y, x + w, y + h)
        door_x = x
        for door_width_mm in module.get("facade_door_widths_mm", [])[:-1]:
            door_x += int(door_width_mm * scale)
            add_wall_border_line(door_x, y, door_x, y + h)
        if (
            module.get("name") != "built_in_microwave"
            and not module.get("suppress_opening_marks")
        ):
            if module.get("tier") == "mezzanine":
                if mezzanine_uses_lift(
                    int(module.get("width_mm", 0)),
                    int(module.get("height_mm", 0)),
                ):
                    append_lift_opening_mark(svg, x=x, y=y, w=w, h=h)
                else:
                    append_hinged_opening_for_doors(
                        svg,
                        x=x,
                        y=y,
                        w=w,
                        h=h,
                        door_widths=[],
                        wall_length_px=int(layout.get("wall_length_mm", 3000) * scale),
                        margin=margin,
                        barrier_xs=tall_barrier_xs,
                    )
            elif module.get("tier") in {"upper", "hood"}:
                if module.get("reserved_for") == "built_in_microwave":
                    microwave_height_px = int(400 * scale)
                    upper_facade_h = max(0, h - microwave_height_px)
                    if upper_facade_h > 0:
                        add_wall_border_line(x, y + upper_facade_h, x + w, y + upper_facade_h)
                    if upper_facade_h > 0:
                        append_lift_opening_mark(
                            svg,
                            x=x,
                            y=y,
                            w=w,
                            h=upper_facade_h,
                        )
                elif module.get("facade_opening") == "lift_fold":
                    fold_y = y + int(h / 2)
                    add_wall_border_line(x, fold_y, x + w, fold_y)
                    append_lift_opening_mark(svg, x=x, y=y, w=w, h=h)
                else:
                    door_widths_px = [
                        float(width_mm) * scale
                        for width_mm in module.get("facade_door_widths_mm", [])
                    ]
                    append_hinged_opening_for_doors(
                        svg,
                        x=x,
                        y=y,
                        w=w,
                        h=h,
                        door_widths=door_widths_px,
                        wall_length_px=int(layout.get("wall_length_mm", 3000) * scale),
                        margin=margin,
                        barrier_xs=tall_barrier_xs,
                    )
    for index, rect in enumerate(suppressed_opening_rects):
        for other_rect in suppressed_opening_rects[index + 1:]:
            for line in shared_rect_edges(rect, other_rect):
                if line[1] == line[3]:
                    wall_border_lines.discard(line)

    for x1, y1, x2, y2 in merge_svg_lines(wall_border_lines):
        svg.append(
            f"<line x1='{x1}' y1='{y1}' x2='{x2}' y2='{y2}' stroke='black' stroke-width='{STROKE_WIDTH}' />"
        )

    lower_border_lines = set()

    def add_lower_border_line(x1: int, y1: int, x2: int, y2: int) -> None:
        line = (x1, y1, x2, y2)
        reverse_line = (x2, y2, x1, y1)
        if reverse_line in lower_border_lines:
            return
        lower_border_lines.add(line)

    # Нижние и высокие модули
    for module in layout.get("modules", []):
        x = margin + int(module["x_mm"] * scale)
        x2 = margin + int((module["x_mm"] + module["width_mm"]) * scale)
        w = x2 - x

        if module["type"] == "profile_handle":
            h = int(module.get("height_mm", kitchen_height_mm - plinth_height_mm) * scale)
            y = baseline_y - plinth_height_px - h
            fill = "#374151"
        elif module["type"] in {"tall", "appliance_tall"}:
            h = int(module.get("height_mm", kitchen_height_mm) * scale)
            y = baseline_y - h
            fill = MODULE_FILL
        elif module["type"] == "freestanding_solo":
            h = int(module.get("height_mm", 2000) * scale)
            y = baseline_y - h
            fill = MODULE_FILL
        elif module.get("corner_false_panel"):
            h = base_height_px
            y = base_top_y
            fill = MODULE_FILL
        elif module.get("countertop_role") == "free_worktop":
            h = base_height_px
            y = base_top_y
            fill = MODULE_FILL
        elif module.get("countertop_role") == "blocked":
            h = base_height_px
            y = base_top_y
            fill = MODULE_FILL
        else:
            h = base_height_px
            y = base_top_y
            fill = MODULE_FILL

        svg.append(
            f"<rect x='{x}' y='{y}' width='{w}' height='{h}' fill='{fill}' stroke='none' />"
        )
        add_lower_border_line(x, y, x + w, y)
        add_lower_border_line(x, y + h, x + w, y + h)
        add_lower_border_line(x, y, x, y + h)
        add_lower_border_line(x + w, y, x + w, y + h)

        if module.get("name") == "oven_under_counter":
            append_under_counter_oven_markup(svg, x=x, y=y, w=w, h=h, scale=scale)

        if str(module.get("name", "")).startswith("dishwasher_"):
            append_dishwasher_icon(svg, x=x, y=y, w=w, h=h)

        if module.get("name") == "sink":
            append_hinged_opening_mark(
                svg,
                x=x,
                y=y,
                w=w,
                h=h,
                hinge_side=nearest_barrier_hinge_side(
                    x=x,
                    w=w,
                    wall_length_px=int(layout.get("wall_length_mm", 3000) * scale),
                    margin=margin,
                    barrier_xs=tall_barrier_xs,
                ),
            )

        if module["type"] in {"tall", "appliance_tall"}:
            render_tall_column_markup(
                svg,
                module=module,
                x=x,
                y=y,
                w=w,
                baseline_y=baseline_y,
                scale=scale,
                kitchen_height_mm=int(module.get("height_mm", kitchen_height_mm)),
                plinth_height_mm=plinth_height_mm,
                mezzanine_height_mm=mezzanine_height_mm,
                wall_panel_top_mm=wall_panel_top_mm,
                margin=margin,
                wall_length_mm=layout.get("wall_length_mm", 3000),
                barrier_xs=tall_barrier_edges_px(
                    layout.get("modules", []),
                    margin=margin,
                    scale=scale,
                    exclude_module=module,
                ),
            )

        if module["type"] == "profile_handle":
            continue

        if module.get("corner_false_panel"):
            continue

        if module.get("name") not in {
            "oven_microwave_column",
            "built_in_fridge",
            "freestanding_fridge_in_carcass",
            "corner_base",
            "oven_under_counter",
            "sink",
            "cutlery_drawer",
        }:
            if (
                not is_drawer_filler_module(module)
                and not str(module.get("name", "")).startswith("dishwasher_")
            ):
                svg.append(
                    f"<text x='{x + 6}' y='{y + 22}' font-size='11' font-family='Arial'>{module['name']}</text>"
                )

    # Столешница.
    # Показывается только на front view.
    # Идёт над нижними модулями по тем же участкам, что и стеновая панель.
    for x1, y1, x2, y2 in merge_svg_lines(lower_border_lines):
        svg.append(
            f"<line x1='{x1}' y1='{y1}' x2='{x2}' y2='{y2}' stroke='black' stroke-width='{STROKE_WIDTH}' />"
        )

    append_lower_profile_handles(
        svg,
        modules=layout.get("modules", []),
        margin=margin,
        scale=scale,
        handle_top_y=handle_top_y,
        handle_height_mm=lower_profile_handle_height_mm,
    )
    append_drawer_filler_profile_handles(
        svg,
        modules=layout.get("modules", []),
        margin=margin,
        scale=scale,
        base_top_y=base_top_y,
        base_height_mm=base_height_mm,
        handle_height_mm=lower_profile_handle_height_mm,
    )

    for countertop in layout.get("countertop_modules", []):
        x = margin + int(countertop["x_mm"] * scale)
        w = int(countertop["width_mm"] * scale)
        h = int(
            countertop.get(
                "thickness_mm",
                countertop.get("height_mm", 38),
            )
            * scale
        )

        y = handle_top_y - h

        svg.append(
            f"<rect x='{x}' y='{y}' width='{w}' height='{h}' fill='{COUNTERTOP_FILL}' stroke='black' stroke-width='{STROKE_WIDTH}' />"
        )

    # Цоколь.
    # Идёт по низу вдоль base-модулей и пенальных модулей.
    # Не идёт под отдельно стоящим холодильником.
    for module in layout.get("modules", []):
        if module.get("name") != "sink":
            continue

        sink_x = margin + int(module["x_mm"] * scale)
        sink_x2 = margin + int((module["x_mm"] + module["width_mm"]) * scale)
        append_sink_faucet_face(
            svg,
            x=sink_x,
            countertop_top_y=handle_top_y - global_countertop_thickness_px,
            w=sink_x2 - sink_x,
        )

    for plinth in layout.get("plinth_modules", []):
        x = margin + int(plinth["x_mm"] * scale)
        w = int(plinth["width_mm"] * scale)
        h = plinth_height_px

        y = baseline_y - h

        svg.append(
            f"<rect x='{x}' y='{y}' width='{w}' height='{h}' fill='#9ca3af' stroke='black' stroke-width='{STROKE_WIDTH}' />"
        )

    for module in layout.get("modules", []):
        if not module_needs_plinth_vent(module):
            continue

        module_x = margin + int(module.get("x_mm", 0) * scale)
        module_w = int(module.get("width_mm", 0) * scale)
        append_plinth_vent(
            svg,
            x=module_x,
            y=baseline_y - plinth_height_px,
            w=module_w,
            h=plinth_height_px,
        )

    # Объекты только для фронтального вида: например, соло микроволновка.
    # Она рисуется после стеновой панели и столешницы, поэтому визуально находится перед ними.
    for obj in layout.get("front_objects", []):
        x = margin + int(obj["x_mm"] * scale)
        w = int(obj["width_mm"] * scale)
        h = int(obj.get("height_mm", 250) * scale)

        y = handle_top_y - global_countertop_thickness_px - h

        if obj["name"] == "hob":
            append_hob_face(
                svg,
                x=x,
                y=y,
                w=w,
                h=h,
                width_mm=int(obj.get("width_mm", 0)),
            )
            continue

        if obj["name"] == "solo_microwave":
            append_solo_microwave_face(svg, x=x, y=y, w=w, h=h)
            continue

        svg.append(
            f"<rect x='{x}' y='{y}' width='{w}' height='{h}' fill='{MODULE_FILL}' stroke='black' stroke-width='{STROKE_WIDTH}' />"
        )

        svg.append(
            f"<text x='{x + 6}' y='{y + 22}' font-size='11' font-family='Arial'>{obj['name']}</text>"
        )

    svg.append(
        f"<line x1='{margin}' y1='{baseline_y}' x2='{margin + content_width_px}' y2='{baseline_y}' stroke='black' stroke-width='{STROKE_WIDTH}' />"
    )

    append_corner_projection_overlay(
        svg,
        projection=layout.get("corner_projection"),
        margin=margin,
        scale=scale,
        baseline_y=baseline_y,
        base_top_y=handle_top_y,
        kitchen_height_mm=kitchen_height_mm,
        wall_length_mm=layout.get("wall_length_mm", 3000),
    )
    append_ceiling_filler_modules(
        svg,
        layout=layout,
        margin=margin,
        scale=scale,
        baseline_y=baseline_y,
    )

    append_front_view_dimensions(
        svg,
        layout=layout,
        margin=margin,
        scale=scale,
        baseline_y=baseline_y,
        base_top_y=base_top_y,
        base_bottom_y=base_bottom_y,
        plinth_height_mm=plinth_height_mm,
        lower_profile_handle_height_mm=lower_profile_handle_height_mm,
        wall_panel_height_mm=wall_panel_height_mm,
        kitchen_height_mm=kitchen_height_mm,
    )

    svg.append("</svg>")
    return "".join(svg)


def render_side_view(layout: dict) -> str:
    if layout.get("shape") != "corner":
        return ""

    return render_front_view(_corner_side_layout(layout, "side_2")).replace(
        "Front View",
        "Side View",
        1,
    )
