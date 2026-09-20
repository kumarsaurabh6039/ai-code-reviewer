import time
import uuid
from pathlib import Path

from app.analyzers.security_analyzer import analyze_security
from app.services.analysis_service import run_static
from app.services.review_service import _validate
from app.utils.file_utils import FileInfo, safe_extract_zip, scan_repository
from tests.conftest import SAMPLE_FILES, make_zip


def _scan(tmp_path):
    z = tmp_path / "s.zip"
    z.write_bytes(make_zip(SAMPLE_FILES))
    root = safe_extract_zip(z, tmp_path / "src")
    return scan_repository(root)


def test_scan_ignores_junk(tmp_path):
    scan = _scan(tmp_path)
    paths = {f.rel_path for f in scan.files}
    assert "app/auth.py" in paths
    assert not any("node_modules" in p or p == ".env" for p in paths)


def test_static_findings(tmp_path):
    findings, stats = run_static(_scan(tmp_path), use_bandit=False)
    rules = {f.rule_id for f in findings}
    for expected in ("SEC-JWT-NOVERIFY", "SEC-HARDCODED-SECRET", "SEC-SQLI-PY", "SEC-WEAK-HASH", "PY-BARE-EXCEPT",
                     "PY-MUTABLE-DEFAULT", "PY-N-PLUS-ONE", "SEC-XSS", "ARCH-CIRCULAR", "ARCH-LAYER",
                     "DOC-NO-README", "TEST-NONE"):
        assert expected in rules, f"{expected} missing; got {sorted(rules)}"
    jwt_issue = next(f for f in findings if f.rule_id == "SEC-JWT-NOVERIFY")
    assert jwt_issue.file_path == "app/auth.py" and jwt_issue.line == 9 and jwt_issue.severity == "high"
    assert stats["functions"] >= 6


def test_secret_value_is_masked(tmp_path):
    findings, _ = run_static(_scan(tmp_path), use_bandit=False)
    secret = next(f for f in findings if f.rule_id == "SEC-HARDCODED-SECRET")
    assert "supersecretvalue123" not in secret.fix_before and "supersecretvalue123" not in secret.description


def test_placeholders_not_flagged():
    fi = FileInfo("cfg.py", "Python", 10, 2, 2, False, 'API_KEY = "your_api_key_here"\nPASSWORD = os.environ["X"]\n')
    assert analyze_security(fi) == []


def test_ai_validation_rejects_hallucinated_lines():
    fi = FileInfo("a.py", "Python", 10, 5, 5, False, "a\nb\nc\nd\ne\n")
    good = {"line": 3, "severity": "high", "category": "bug", "title": "t", "description": "d"}
    assert _validate(good, fi) is not None
    assert _validate({**good, "line": 99}, fi) is None
    assert _validate({**good, "severity": "urgent"}, fi) is None
    assert _validate({**good, "category": "nonsense"}, fi) is None


def _auth(client):
    email = f"{uuid.uuid4().hex[:8]}@example.com"
    tok = client.post("/api/auth/register", json={"email": email, "password": "password123"}).json()["access_token"]
    return {"Authorization": f"Bearer {tok}"}


def test_full_flow(client, sample_zip):
    h = _auth(client)
    r = client.post("/api/repositories/zip", headers=h, files={"file": ("demo.zip", sample_zip, "application/zip")})
    assert r.status_code == 202, r.text
    ids = r.json()
    for _ in range(50):  # background task
        a = client.get(f"/api/analyses/{ids['analysis_id']}", headers=h).json()
        if a["status"] in ("completed", "failed"):
            break
        time.sleep(0.2)
    assert a["status"] == "completed", a
    assert 0 <= a["scores"]["overall"] <= 100 and a["scores"]["security"] < 100
    assert a["languages"]["Python"] > 0 and a["roadmap"]

    issues = client.get(f"/api/analyses/{a['id']}/issues", headers=h).json()
    assert issues and issues[0]["severity"] in ("critical", "high")
    iid = next(i["id"] for i in issues if i["title"] == "JWT validation disabled")

    code = client.get(f"/api/issues/{iid}/code", headers=h).json()
    assert any("verify_exp" in ln for ln in code["lines"])
    ex = client.post(f"/api/issues/{iid}/explain", headers=h).json()
    assert ex["explanation"] and ex["ai"] is False
    assert client.patch(f"/api/issues/{iid}", headers=h, json={"status": "resolved"}).json()["status"] == "resolved"

    md = client.get(f"/api/analyses/{a['id']}/report?format=md", headers=h)
    assert md.status_code == 200 and "Health score" in md.text and "not an industry certification" in md.text
    assert client.get(f"/api/analyses/{a['id']}/report?format=json", headers=h).json()["scores"]["overall"] == a["scores"]["overall"]

    chat = client.post(f"/api/mentor/{ids['repository_id']}/chat", headers=h, json={"message": "how does jwt authentication work?"}).json()
    assert chat["sources"] and chat["sources"][0]["file"].endswith("auth.py")
    files = client.get(f"/api/mentor/{ids['repository_id']}/files", headers=h).json()
    assert "app/auth.py" in files
    exp = client.post(f"/api/mentor/{ids['repository_id']}/explain-code", headers=h,
                      json={"file_path": "app/auth.py", "start_line": 8, "end_line": 9})
    assert exp.status_code == 200
    bad = client.post(f"/api/mentor/{ids['repository_id']}/explain-code", headers=h,
                      json={"file_path": "../../etc/passwd", "start_line": 1, "end_line": 5})
    assert bad.status_code == 404

    # another user must not see it
    h2 = _auth(client)
    assert client.get(f"/api/analyses/{a['id']}", headers=h2).status_code == 404
    assert client.get(f"/api/issues/{iid}", headers=h2).status_code == 404
    assert client.delete(f"/api/repositories/{ids['repository_id']}", headers=h2).status_code == 404

    dash = client.get("/api/dashboard", headers=h).json()
    assert dash["repositories"] == 1 and dash["average_score"] == a["scores"]["overall"]
    assert client.delete(f"/api/repositories/{ids['repository_id']}", headers=h).status_code == 204


def test_upload_rejects_bad_files(client):
    h = _auth(client)
    assert client.post("/api/repositories/zip", headers=h, files={"file": ("x.txt", b"hi")}).status_code == 400
    evil = make_zip({"../evil.py": "x"})
    assert client.post("/api/repositories/zip", headers=h, files={"file": ("e.zip", evil)}).status_code == 400
    assert client.post("/api/repositories/github", headers=h, json={"url": "https://evil.com/a/b"}).status_code == 400
    assert client.post("/api/repositories/github", headers=h, json={"url": "https://github.com/a/b", "branch": "--upload-pack=x"}).status_code == 400
    assert client.post("/api/repositories/zip", files={"file": ("x.zip", b"x")}).status_code == 401
