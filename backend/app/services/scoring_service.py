"""Deterministic health score. Same issues in -> same score out (no LLM involved)."""
import math

WEIGHTS = {"critical": 15, "high": 8, "medium": 3, "low": 1}
CATEGORY_TO_SCORE = {
    "bug": "code_quality", "code_smell": "code_quality", "duplication": "code_quality",
    "security": "security", "performance": "performance", "architecture": "architecture",
    "testing": "testing", "documentation": "documentation",
}
OVERALL_WEIGHTS = {"code_quality": 0.25, "security": 0.25, "performance": 0.10,
                   "architecture": 0.15, "testing": 0.15, "documentation": 0.10}


def _clamp(v: float) -> int:
    return int(max(0, min(100, round(v))))


def compute_scores(issues: list[dict], loc: int, source_files: int, test_files: int,
                   readme_lines: int, docstring_coverage: float | None) -> dict:
    """issues: [{severity, category, confidence}]. Penalties are normalized by project size
    (sqrt of KLOC) so that big repos are not punished linearly."""
    size_factor = max(1.0, math.sqrt(loc / 1000))
    penalty = {k: 0.0 for k in OVERALL_WEIGHTS}
    for i in issues:
        key = CATEGORY_TO_SCORE.get(i["category"], "code_quality")
        penalty[key] += WEIGHTS.get(i["severity"], 1) * max(0.5, float(i.get("confidence", 0.8)))
    scores = {k: _clamp(100 - p / size_factor) for k, p in penalty.items()}

    if source_files > 0:
        ratio = min(1.0, (test_files / source_files) / 0.5)  # 1 test file per 2 source files = full marks
        scores["testing"] = min(scores["testing"], _clamp(30 + 70 * ratio))

    readme_part = 1.0 if readme_lines >= 20 else (0.5 if readme_lines > 0 else 0.0)
    doc_component = readme_part if docstring_coverage is None else 0.5 * readme_part + 0.5 * docstring_coverage
    scores["documentation"] = min(scores["documentation"], _clamp(30 + 70 * doc_component))

    overall = _clamp(sum(scores[k] * w for k, w in OVERALL_WEIGHTS.items()))
    return {"overall": overall, **scores}
