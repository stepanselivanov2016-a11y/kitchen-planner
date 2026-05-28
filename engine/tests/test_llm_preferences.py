from app.llm_preferences import (
    _apply_config_rules,
    _extract_json,
    _normalize_patch,
)


def test_extract_json_from_markdown_response():
    assert _extract_json('```json\n{"patch": {"room.layout_shape": "corner"}}\n```') == {
        "patch": {"room.layout_shape": "corner"}
    }


def test_normalize_patch_filters_unknown_fields_and_invalid_values():
    patch = _normalize_patch(
        {
            "room.layout_shape": "corner",
            "required.hob.cabinet_width_mm": 750,
            "unknown.field": True,
        }
    )

    assert patch == {"room.layout_shape": "corner"}


def test_config_rules_detect_lift_upper_cabinets_from_natural_phrase():
    patch = _apply_config_rules("Хочу верхние шкафы с подъёмными фасадами")

    assert patch["room.upper_cabinet_opening"] == "lift"
