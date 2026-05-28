from app.wall_modules import apply_wall_facade_grouping


def _wall_module(name, x, width, *, tier="upper", reserved_for=None):
    module = {
        "type": "wall",
        "name": name,
        "width_mm": width,
        "height_mm": 800,
        "x_mm": x,
        "y_mm": 1520,
        "depth_mm": 350,
        "tier": tier,
    }
    if reserved_for:
        module["reserved_for"] = reserved_for
    return module


def _mezzanine(x, width):
    return {
        "type": "wall",
        "name": "mezzanine_drawer",
        "width_mm": width,
        "height_mm": 260,
        "x_mm": x,
        "y_mm": 2320,
        "depth_mm": 350,
        "tier": "mezzanine",
    }


def test_lift_upper_merges_short_segment_with_regular_neighbor():
    modules = [
        _wall_module("upper_cabinet", 400, 250),
        _mezzanine(400, 250),
        _wall_module("upper_cabinet", 650, 600),
        _mezzanine(650, 600),
    ]

    result = apply_wall_facade_grouping(modules, upper_cabinet_opening="lift")
    upper = [module for module in result if module.get("tier") == "upper"]
    mezzanine = [module for module in result if module.get("tier") == "mezzanine"]

    assert len(upper) == 1
    assert upper[0]["width_mm"] == 850
    assert upper[0]["facade_opening"] == "lift_fold"
    assert mezzanine[0]["width_mm"] == 850


def test_lift_upper_merges_short_segment_with_dish_drying_neighbor():
    modules = [
        _wall_module("upper_cabinet", 400, 250),
        _mezzanine(400, 250),
        _wall_module("dish_drying_cabinet", 650, 600),
        _mezzanine(650, 600),
    ]

    result = apply_wall_facade_grouping(modules, upper_cabinet_opening="lift")
    upper = [module for module in result if module.get("tier") == "upper"]

    assert len(upper) == 1
    assert upper[0]["name"] == "dish_drying_cabinet"
    assert upper[0]["width_mm"] == 850
    assert upper[0]["facade_opening"] == "lift_fold"


def test_short_lift_upper_falls_back_to_hinged_when_blocked():
    modules = [
        _wall_module("built_in_hood", 0, 600, tier="hood"),
        _mezzanine(0, 600),
        _wall_module("upper_cabinet", 600, 300),
        _mezzanine(600, 300),
        _wall_module("upper_cabinet", 950, 600, reserved_for="built_in_microwave"),
    ]

    result = apply_wall_facade_grouping(modules, upper_cabinet_opening="lift")
    short_upper = next(
        module
        for module in result
        if module.get("tier") == "upper" and module.get("width_mm") == 300
    )

    assert short_upper.get("facade_opening") is None
    assert short_upper["facade_door_count"] == 1
