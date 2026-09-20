from dataclasses import dataclass

SEVERITIES = ("critical", "high", "medium", "low")
SEVERITY_RANK = {s: i for i, s in enumerate(SEVERITIES)}
CATEGORIES = ("bug", "security", "code_smell", "duplication", "performance", "architecture", "testing",
              "documentation")


@dataclass
class Finding:
    file_path: str
    line: int
    severity: str
    category: str
    title: str
    description: str
    suggestion: str = ""
    rule_id: str = ""
    end_line: int | None = None
    confidence: float = 0.8
    fix_before: str = ""
    fix_after: str = ""
    source: str = "static"
