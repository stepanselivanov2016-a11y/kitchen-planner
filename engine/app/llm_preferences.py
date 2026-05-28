from __future__ import annotations

import json
import os
import re
from pathlib import Path
from typing import Any

import httpx
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field


router = APIRouter(prefix="/preferences", tags=["preferences"])

OLLAMA_URL = os.getenv("OLLAMA_URL", "http://127.0.0.1:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "qwen2.5:3b")
PREFERENCE_RULES_PATH = Path(__file__).with_name("preference_rules.json")

ALLOWED_PATCHES: dict[str, set[Any]] = {
    "room.layout_shape": {"straight", "corner"},
    "room.wall_cabinets_enabled": {True, False},
    "room.mezzanine_enabled": {True, False},
    "room.upper_cabinet_opening": {"hinged", "lift"},
    "room.ceiling_type": {"stretch", "plasterboard"},
    "room.entry_side": {"left", "right"},
    "required.refrigerator.mode": {"built_in", "freestanding"},
    "required.refrigerator.freestanding_installation": {"in_cabinet", "solo"},
    "required.oven.placement": {"under_counter", "column"},
    "required.sink.width_mm": {400, 450, 500, 600, 700, 800, 900, 1000},
    "required.hood.type": {"built_in", "solo"},
    "required.hood.width_mm": {600, 900, 1200, 1800},
    "required.microwave.type": {"built_in", "upper_built_in", "solo"},
    "required.microwave.width_mm": {600},
    "required.microwave.height_mm": {400},
    "required.hob.cabinet_width_mm": {300, 600, 800, 900},
    "optional.dishwasher.enabled": {True, False},
    "optional.dishwasher.width_mm": {450, 600},
    "optional.undercounter_fridge.enabled": {True, False},
}

FIELD_LABELS = {
    "room.layout_shape": "форма кухни",
    "room.wall_cabinets_enabled": "навесные шкафы",
    "room.mezzanine_enabled": "антресольные шкафы",
    "room.ceiling_type": "тип потолка",
    "room.entry_side": "сторона вывода воды",
    "required.refrigerator.mode": "тип холодильника",
    "required.refrigerator.freestanding_installation": "установка отдельностоящего холодильника",
    "required.oven.placement": "расположение духовки",
    "required.sink.width_mm": "ширина мойки",
    "required.hood.type": "тип вытяжки",
    "required.hood.width_mm": "ширина вытяжки",
    "required.microwave.type": "тип СВЧ",
    "required.microwave.width_mm": "ширина СВЧ",
    "required.microwave.height_mm": "высота СВЧ",
    "required.hob.cabinet_width_mm": "ширина варочной",
    "optional.dishwasher.enabled": "посудомойка",
    "optional.dishwasher.width_mm": "ширина посудомойки",
    "optional.undercounter_fridge.enabled": "подстольный холодильник",
}


class PreferenceParseRequest(BaseModel):
    text: str = ""


class PreferenceParseResponse(BaseModel):
    patch: dict[str, Any] = Field(default_factory=dict)
    locked: list[str] = Field(default_factory=list)
    notes: list[str] = Field(default_factory=list)
    source: str


def _extract_json(text: str) -> dict[str, Any]:
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```(?:json)?", "", cleaned).strip()
        cleaned = re.sub(r"```$", "", cleaned).strip()

    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", cleaned, flags=re.DOTALL)
        if not match:
            raise
        return json.loads(match.group(0))


def _normalize_patch(raw_patch: dict[str, Any]) -> dict[str, Any]:
    patch: dict[str, Any] = {}
    for field, value in raw_patch.items():
        allowed_values = ALLOWED_PATCHES.get(field)
        if allowed_values is None:
            continue
        if value in allowed_values:
            patch[field] = value
    return patch


def _load_preference_rules() -> dict[str, Any]:
    return json.loads(PREFERENCE_RULES_PATH.read_text(encoding="utf-8"))


def _apply_config_rules(text: str) -> dict[str, Any]:
    lowered = text.lower().replace("ё", "е")
    patch: dict[str, Any] = {}
    rules = _load_preference_rules()

    for rule in rules.get("semantic_rules", []):
        if any(re.search(pattern, lowered) for pattern in rule.get("exclude_patterns", [])):
            continue
        if not all(re.search(pattern, lowered) for pattern in rule.get("required_patterns", [])):
            continue
        if any(re.search(pattern, lowered) for pattern in rule.get("patterns", [])):
            patch.update(rule.get("patch", {}))

    if re.search(r"(подъ[её]мн|подъемн|лифт|авентос|складн).*?(верх|навес)|(?:верх|навес).*?(подъ[её]мн|подъемн|лифт|авентос|складн)", lowered):
        patch["room.upper_cabinet_opening"] = "lift"
    elif re.search(r"(распаш|распах).*?(верх|навес)|(?:верх|навес).*?(распаш|распах)", lowered):
        patch["room.upper_cabinet_opening"] = "hinged"

    upper_terms = "(\u0432\u0435\u0440\u0445\\w*|\u043d\u0430\u0432\u0435\u0441\\w*)"
    lift_terms = "(\u043f\u043e\u0434\u044a[\u0435\u0451]\u043c\\w*|\u043b\u0438\u0444\u0442\\w*|\u0430\u0432\u0435\u043d\u0442\u043e\u0441\\w*|\u0441\u043a\u043b\u0430\u0434\u043d\\w*)"
    hinged_terms = "(\u0440\u0430\u0441\u043f\u0430\u0448\\w*|\u0440\u0430\u0441\u043f\u0430\u0445\\w*)"
    if re.search(f"{lift_terms}.*?{upper_terms}|{upper_terms}.*?{lift_terms}", lowered):
        patch["room.upper_cabinet_opening"] = "lift"
    elif re.search(f"{hinged_terms}.*?{upper_terms}|{upper_terms}.*?{hinged_terms}", lowered):
        patch["room.upper_cabinet_opening"] = "hinged"

    return _normalize_patch(patch)


def _config_needs_llm(text: str) -> bool:
    lowered = text.lower().replace("ё", "е")
    rules = _load_preference_rules()
    return any(
        re.search(pattern, lowered)
        for pattern in rules.get("llm_trigger_patterns", [])
    )


def _fallback_parse(text: str) -> dict[str, Any]:
    lowered = text.lower().replace("ё", "е")
    patch: dict[str, Any] = {}

    def width_near(pattern: str, allowed: set[int], *, before: int = 18, after: int = 34) -> int | None:
        for match in re.finditer(pattern, lowered):
            after_window = lowered[match.end() : min(len(lowered), match.end() + after)]
            after_window = re.split(r"[,.;]", after_window, maxsplit=1)[0]
            before_window = lowered[max(0, match.start() - before) : match.start()]
            before_window = re.split(r"[,.;]", before_window)[-1]
            windows = [after_window, before_window]
            for width in sorted(allowed, reverse=True):
                if any(re.search(rf"\b{width // 10}\b|{width}", window) for window in windows):
                    return width
        return None

    def has_near(pattern: str, terms: str, *, before: int = 16, after: int = 28) -> bool:
        for match in re.finditer(pattern, lowered):
            start = max(0, match.start() - before)
            end = min(len(lowered), match.end() + after)
            window = lowered[start:end]
            if re.search(terms, window):
                return True
        return False

    if "углов" in lowered:
        patch["room.layout_shape"] = "corner"
    elif "прям" in lowered:
        patch["room.layout_shape"] = "straight"

    dishwasher_negative = re.search(
        r"(без\s+\w*посудомо\w*|пмм\s+не\s+нужн\w*|посудомо\w*\s+(не\s+ставить|не\s+нужн\w*|не\s+надо)|не\s+(ставить|надо|нужн\w*)\s+\w*посудомо\w*)",
        lowered,
    )
    if dishwasher_negative:
        patch["optional.dishwasher.enabled"] = False
    elif re.search(r"\b(пмм|посудомо\w*)\b", lowered):
        patch["optional.dishwasher.enabled"] = True
        width = width_near(r"\b(пмм|посудомо\w*)\b", {450, 600})
        if width:
            patch["optional.dishwasher.width_mm"] = width

    if "без антрес" in lowered or "антресол" in lowered and "не" in lowered:
        patch["room.mezzanine_enabled"] = False
    elif "антрес" in lowered:
        patch["room.mezzanine_enabled"] = True

    if (
        "без навес" in lowered
        or "без верхних шкаф" in lowered
        or "без верхних модул" in lowered
        or "навес" in lowered and "не" in lowered
    ):
        patch["room.wall_cabinets_enabled"] = False
    elif "навес" in lowered or "верхние шкаф" in lowered or "верхние модул" in lowered:
        patch["room.wall_cabinets_enabled"] = True

    if "натяж" in lowered:
        patch["room.ceiling_type"] = "stretch"
    if "гипс" in lowered:
        patch["room.ceiling_type"] = "plasterboard"

    if "вывод воды" in lowered or "вода" in lowered:
        if "справа" in lowered or "прав" in lowered:
            patch["room.entry_side"] = "right"
        if "слева" in lowered or "лев" in lowered:
            patch["room.entry_side"] = "left"

    if "духов" in lowered:
        if "колон" in lowered or "пенал" in lowered:
            patch["required.oven.placement"] = "column"
        elif "под стол" in lowered or "подстол" in lowered:
            patch["required.oven.placement"] = "under_counter"

    microwave_pattern = r"(свч|микроволн\w*)"
    if re.search(microwave_pattern, lowered):
        if has_near(microwave_pattern, r"(верх|навес)", before=0):
            patch["required.microwave.type"] = "upper_built_in"
        elif has_near(microwave_pattern, r"(соло|отдель)", before=0):
            patch["required.microwave.type"] = "solo"
        elif has_near(microwave_pattern, r"(колон|встро)", before=0):
            patch["required.microwave.type"] = "built_in"

    if "холод" in lowered:
        fridge_pattern = r"холод\w*"
        if has_near(fridge_pattern, r"(каркас|корпус)"):
            patch["required.refrigerator.mode"] = "freestanding"
            patch["required.refrigerator.freestanding_installation"] = "in_cabinet"
        elif has_near(fridge_pattern, r"(соло|отдельностоя|отдельно\s+стоя|отдель)"):
            patch["required.refrigerator.mode"] = "freestanding"
            patch["required.refrigerator.freestanding_installation"] = "solo"
        elif has_near(fridge_pattern, r"встро") or re.search(r"встро\w*\s+холод", lowered):
            patch["required.refrigerator.mode"] = "built_in"

    for pattern, field, allowed in (
        (r"вароч", "required.hob.cabinet_width_mm", {300, 600, 800, 900}),
        (r"(?<!посудо)мойк", "required.sink.width_mm", {400, 450, 500, 600, 700, 800, 900, 1000}),
        (r"вытяж", "required.hood.width_mm", {600, 900, 1200, 1800}),
    ):
        width = width_near(pattern, allowed)
        if width:
            patch[field] = width

    if "встро" in lowered and "вытяж" in lowered:
        patch["required.hood.type"] = "built_in"
    elif "соло" in lowered and "вытяж" in lowered:
        patch["required.hood.type"] = "solo"

    return _normalize_patch(patch)


def _semantic_hint_parse(text: str) -> dict[str, Any]:
    return _apply_config_rules(text)

    lowered = text.lower().replace("ё", "е")
    patch: dict[str, Any] = {}

    if re.search(r"(без\s+лишн\w*\s+верхн\w*|меньше\s+верхн\w*|минимум\s+верхн\w*)", lowered):
        patch["room.wall_cabinets_enabled"] = False
    if re.search(r"(верх\w*\s+.*(минимум|поменьше)|не\s+хочу\s+много\s+верхн)", lowered):
        patch["room.wall_cabinets_enabled"] = False
    if re.search(r"(больше\s+.*хранен\w*\s+сверх|закрыт\w*\s+хранен\w*\s+сверх|хранен\w*\s+сверх)", lowered):
        patch["room.wall_cabinets_enabled"] = True

    if re.search(r"(маленьк\w*|компактн\w*|узк\w*)", lowered) and re.search(
        r"(пмм|посудомо\w*)", lowered
    ):
        patch["optional.dishwasher.enabled"] = True
        patch["optional.dishwasher.width_mm"] = 450
    if re.search(r"(полноразмерн\w*|побольше|больш\w*)", lowered) and re.search(
        r"(пмм|посудомо\w*)", lowered
    ):
        patch["optional.dishwasher.enabled"] = True
        patch["optional.dishwasher.width_mm"] = 600

    if re.search(
        r"(техник\w*\s+.*спрят|спрят\w*\s+.*техник|вс[яю]\s+техник\w*\s+.*встро|техник\w*\s+.*встро|техник\w*\s+.*не\s+.*отдель)",
        lowered,
    ):
        patch["required.refrigerator.mode"] = "built_in"
        patch["required.hood.type"] = "built_in"
        patch["required.microwave.type"] = "built_in"
    if re.search(r"не\s+хочу\s+.*техник\w*.*стоя\w*\s+отдель", lowered):
        patch["required.refrigerator.mode"] = "built_in"
        patch["required.hood.type"] = "built_in"
        patch["required.microwave.type"] = "built_in"

    if re.search(r"(микроволн\w*|свч)", lowered):
        if re.search(r"(не\s+на\s+столешниц|спрят\w*\s+.*шкаф|не\s+на\s+стол)", lowered):
            patch["required.microwave.type"] = "built_in"
        if re.search(r"(убрать\s+наверх|в\s+верхн\w*|в\s+навесн\w*)", lowered):
            patch["required.microwave.type"] = "upper_built_in"

    if re.search(r"вытяж\w*.*спрят|спрят\w*.*вытяж", lowered):
        patch["required.hood.type"] = "built_in"

    if re.search(r"холод\w*.*спрят|спрят\w*.*холод", lowered):
        patch["required.refrigerator.mode"] = "built_in"
    if re.search(r"холод\w*.*не\s+встра", lowered):
        patch["required.refrigerator.mode"] = "freestanding"
    if re.search(r"холод\w*.*(стоит|стоять)\s+отдель", lowered):
        patch["required.refrigerator.mode"] = "freestanding"
        patch["required.refrigerator.freestanding_installation"] = "solo"

    if re.search(r"мойк\w*.*(компактн|маленьк|узк)", lowered):
        patch["required.sink.width_mm"] = 400
    if re.search(r"мойк\w*.*(побольше|больш)", lowered):
        patch["required.sink.width_mm"] = 600

    if re.search(r"вароч\w*.*(компактн|маленьк|узк)", lowered):
        patch["required.hob.cabinet_width_mm"] = 300
    if re.search(r"(больш\w*\s+вароч|вароч\w*.*больш)", lowered):
        patch["required.hob.cabinet_width_mm"] = 900
    if re.search(r"вароч\w*.*побольше", lowered):
        patch["required.hob.cabinet_width_mm"] = 800

    if re.search(r"(до\s+потолка|в\s+потолок)", lowered):
        if re.search(r"(не\s+надо|без|не\s+хочу)", lowered):
            patch["room.mezzanine_enabled"] = False
        else:
            patch["room.mezzanine_enabled"] = True

    return _normalize_patch(patch)


def _needs_llm_enrichment(text: str) -> bool:
    return _config_needs_llm(text)

    lowered = text.lower().replace("ё", "е")
    return bool(
        re.search(
            r"(спрят|лишн|компактн|маленьк|узк|предпоч|лучше|не\s+хочу|минимум|поменьше|побольше)",
            lowered,
        )
    )


def _notes_for_patch(patch: dict[str, Any]) -> list[str]:
    return [f"{FIELD_LABELS.get(field, field)}: {value}" for field, value in patch.items()]


async def _parse_with_ollama(text: str) -> dict[str, Any]:
    system_prompt = (
        "Ты извлекаешь параметры кухонного планировщика из русского текста. "
        "Верни только JSON без Markdown. JSON должен иметь поля patch, locked, notes. "
        "patch - объект, где ключи только из разрешенного списка, значения только допустимые. "
        "locked - массив ключей patch, которые пользователь явно зафиксировал. "
        "notes - короткие русские пояснения. "
        "Разрешенные ключи и значения: "
        f"{json.dumps({key: sorted(list(value), key=str) for key, value in ALLOWED_PATCHES.items()}, ensure_ascii=False)}"
    )
    payload = {
        "model": OLLAMA_MODEL,
        "stream": False,
        "format": "json",
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": text},
        ],
    }

    async with httpx.AsyncClient(timeout=18.0) as client:
        response = await client.post(f"{OLLAMA_URL.rstrip('/')}/api/chat", json=payload)
        response.raise_for_status()
        data = response.json()

    content = data.get("message", {}).get("content", "")
    parsed = _extract_json(content)
    return _normalize_patch(parsed.get("patch", {}))


@router.post("/parse", response_model=PreferenceParseResponse)
async def parse_preferences(payload: PreferenceParseRequest):
    text = payload.text.strip()
    if not text:
        return PreferenceParseResponse(source="empty")

    fallback_patch = _fallback_parse(text)
    semantic_patch = _semantic_hint_parse(text)
    should_enrich = _needs_llm_enrichment(text)

    if fallback_patch and not semantic_patch and not should_enrich:
        return PreferenceParseResponse(
            patch=fallback_patch,
            locked=list(fallback_patch.keys()),
            notes=_notes_for_patch(fallback_patch),
            source="rules",
        )

    try:
        ollama_patch = await _parse_with_ollama(text)
        patch = {**ollama_patch, **semantic_patch, **fallback_patch}
        source = "hybrid" if fallback_patch or semantic_patch else "ollama"
    except Exception:
        patch = {**semantic_patch, **fallback_patch}
        source = "rules"

    if not patch:
        raise HTTPException(
            status_code=422,
            detail="Не удалось распознать фиксируемые параметры в пожеланиях.",
        )

    return PreferenceParseResponse(
        patch=patch,
        locked=list(patch.keys()),
        notes=_notes_for_patch(patch),
        source=source,
    )
