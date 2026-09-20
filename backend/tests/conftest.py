import io
import os
import tempfile
import zipfile

_tmp = tempfile.mkdtemp()
os.environ["DATABASE_URL"] = f"sqlite:///{_tmp}/test.db"
os.environ["WORKDIR"] = f"{_tmp}/work"
os.environ["ANTHROPIC_API_KEY"] = ""  # tests never call the real LLM
os.environ["SECRET_KEY"] = "test-secret"

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app.main import app  # noqa: E402

SAMPLE_FILES = {
    "demo/app/auth.py": '''import hashlib
import jwt
from app import users

SECRET_KEY = "supersecretvalue123"


def check(token):
    return jwt.decode(token, SECRET_KEY, algorithms=["HS256"], options={"verify_exp": False})


def hash_pw(p):
    return hashlib.md5(p.encode()).hexdigest()


def find(cursor, name):
    cursor.execute(f"SELECT * FROM users WHERE name = '{name}'")


def risky(items=[]):
    try:
        return items
    except:
        pass


def load_all(cursor, ids):
    out = []
    for i in ids:
        cursor.execute("SELECT * FROM t WHERE id = %s", (i,))
        out.append(cursor.fetchone())
    return out
''',
    "demo/app/users.py": "from app import auth\n\n\ndef get_user():\n    return auth.check('x')\n",
    "demo/app/routes/api.py": '''def a(session):
    return session.query(1)


def b(session):
    return session.query(2)


def c(session):
    return session.query(3)
''',
    "demo/node_modules/evil/index.js": "eval('this must be ignored')",
    "demo/.env": "SECRET=this-file-must-be-ignored-12345",
    "demo/static/app.js": "document.getElementById('x').innerHTML = userInput;\n",
}


def make_zip(files: dict[str, str]) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        for name, content in files.items():
            z.writestr(name, content)
    return buf.getvalue()


@pytest.fixture(scope="session")
def client():
    with TestClient(app) as c:
        yield c


@pytest.fixture()
def sample_zip() -> bytes:
    return make_zip(SAMPLE_FILES)
