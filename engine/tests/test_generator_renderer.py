from app.generator import generate_layout
from app.renderer import render_front_view, render_side_view, render_top_view


def _corner_options(*, upper_cabinet_opening="lift", microwave_type="upper_built_in"):
    return {
        "room": {
            "layout_shape": "corner",
            "side_1_width_mm": 3000,
            "side_2_width_mm": 2300,
            "wall_length_mm": 3000,
            "kitchen_height_mm": 2700,
            "wall_cabinets_enabled": True,
            "mezzanine_enabled": True,
            "upper_cabinet_opening": upper_cabinet_opening,
            "entry_side": "right",
            "ceiling_type": "stretch",
        },
        "required": {
            "refrigerator": {
                "mode": "built_in",
                "freestanding_installation": "in_cabinet",
                "width_mm": 600,
                "depth_mm": 600,
                "height_mm": 2000,
                "gap_mm": 30,
            },
            "oven": {"placement": "under_counter"},
            "sink": {"width_mm": 600},
            "hood": {"type": "built_in", "width_mm": 600},
            "microwave": {"type": microwave_type, "width_mm": 600, "height_mm": 400},
            "hob": {"cabinet_width_mm": 600},
        },
        "optional": {
            "dishwasher": {"enabled": False, "width_mm": 600},
            "undercounter_fridge": {"enabled": False},
        },
        "locked": {
            "room.upper_cabinet_opening": True,
            "microwave.type": True,
        },
    }


def test_corner_layout_uses_shared_upper_height_when_microwave_is_upper_built_in():
    layout = generate_layout({"wall_length_mm": 3000}, _corner_options())

    side_1_heights = {
        module["height_mm"]
        for module in layout["side_1"]["wall_modules"]
        if module.get("tier") == "upper"
    }
    side_2_heights = {
        module["height_mm"]
        for module in layout["side_2"]["wall_modules"]
        if module.get("tier") == "upper"
    }
    upper_microwave_count = sum(
        1
        for module in layout["wall_modules"]
        if module.get("reserved_for") == "built_in_microwave"
    )

    assert side_1_heights == {800}
    assert side_2_heights == {800}
    assert upper_microwave_count == 1


def test_corner_layout_renders_all_svg_views():
    layout = generate_layout({"wall_length_mm": 3000}, _corner_options())

    front_svg = render_front_view(layout)
    side_svg = render_side_view(layout)
    top_svg = render_top_view(layout)

    assert front_svg.startswith("<svg")
    assert side_svg.startswith("<svg")
    assert top_svg.startswith("<svg")
    assert "Front View" in front_svg
    assert "Side View" in side_svg
    assert "Top View" in top_svg
