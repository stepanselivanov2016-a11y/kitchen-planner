import re


def detect_position(text: str, keyword_patterns: list[str]) -> str | None:
    clauses = re.split(r"[,.!;\n]+|\s+\bи\b\s+", text)

    for clause in clauses:
        clause = clause.strip()
        if not clause:
            continue

        has_keyword = any(re.search(pattern, clause) for pattern in keyword_patterns)
        if not has_keyword:
            continue

        if re.search(r"\bслева\b", clause):
            return "left"
        if re.search(r"\bсправа\b", clause):
            return "right"
        if re.search(r"по центру|в центре|центр|центре|центру", clause):
            return "center"

    for pattern in keyword_patterns:
        if re.search(fr"{pattern}.{{0,25}}слева|слева.{{0,25}}{pattern}", text):
            return "left"
        if re.search(fr"{pattern}.{{0,25}}справа|справа.{{0,25}}{pattern}", text):
            return "right"
        if re.search(fr"{pattern}.{{0,25}}(по центру|в центре|центр|центре|центру)|(по центру|в центре|центр|центре|центру).{{0,25}}{pattern}", text):
            return "center"

    return None


def parse_prompt(prompt: str) -> dict:
    text = prompt.lower()

    wall_length_mm = 3000

    match_m = re.search(r"(\d+(?:[.,]\d+)?)\s*м\b", text)
    match_mm = re.search(r"(\d{3,5})\s*мм\b", text)

    if match_mm:
        wall_length_mm = int(match_mm.group(1))
    elif match_m:
        meters = float(match_m.group(1).replace(",", "."))
        wall_length_mm = int(meters * 1000)

    appliances = {
        "sink": bool(re.search(r"мойк|раковин", text)),
        "hob": bool(re.search(r"вароч|плит|панел", text)),
        "oven": bool(re.search(r"духов", text)),
        "dishwasher": bool(re.search(r"посудом", text)),
        "fridge": bool(re.search(r"холод", text)),
    }

    positions = {
        "sink": detect_position(text, [r"мойк\w*", r"раковин\w*"]),
        "hob": detect_position(text, [r"вароч\w*", r"плит\w*", r"панел\w*"]),
        "oven": detect_position(text, [r"духов\w*"]),
        "fridge": detect_position(text, [r"холодильник\w*", r"холод\w*"]),
    }

    return {
        "shape": "straight",
        "wall_length_mm": wall_length_mm,
        "appliances": appliances,
        "positions": positions,
    }