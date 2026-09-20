from app.services.scoring_service import compute_scores
from app.services.review_service import deterministic_roadmap


def _iss(sev, cat="security", conf=0.9):
    return {"severity": sev, "category": cat, "confidence": conf}


def test_deterministic():
    issues = [_iss("high"), _iss("low", "bug")]
    a = compute_scores(issues, 2000, 10, 5, 30, 0.8)
    b = compute_scores(issues, 2000, 10, 5, 30, 0.8)
    assert a == b


def test_more_severe_issues_lower_score():
    clean = compute_scores([], 1000, 10, 6, 30, 1.0)
    bad = compute_scores([_iss("critical"), _iss("high")], 1000, 10, 6, 30, 1.0)
    assert clean["overall"] > bad["overall"] and clean["security"] == 100 and bad["security"] < 80


def test_scores_bounded():
    s = compute_scores([_iss("critical")] * 50, 100, 5, 0, 0, 0.0)
    assert all(0 <= v <= 100 for v in s.values())


def test_no_tests_caps_testing_score():
    s = compute_scores([], 1000, 10, 0, 30, 1.0)
    assert s["testing"] <= 30


def test_big_repos_are_normalized():
    small = compute_scores([_iss("high")] * 5, 500, 5, 5, 30, 1.0)
    big = compute_scores([_iss("high")] * 5, 20000, 100, 50, 30, 1.0)
    assert big["security"] > small["security"]


def test_roadmap_groups_and_orders():
    issues = [
        {"id": 1, "severity": "low", "category": "documentation", "title": "README short", "rule_id": "D", "description": "d"},
        {"id": 2, "severity": "critical", "category": "security", "title": "JWT off", "rule_id": "J", "description": "d"},
        {"id": 3, "severity": "critical", "category": "security", "title": "JWT off", "rule_id": "J", "description": "d"},
    ]
    road = deterministic_roadmap(issues)
    assert road[0]["priority"] == 1 and road[0]["category"] == "security" and road[0]["issue_ids"] == [2, 3]
    assert road[0]["effort"] in {"Low", "Medium", "High"}
