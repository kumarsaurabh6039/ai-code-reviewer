import io
import stat
import zipfile

import pytest

from app.core.config import settings
from app.utils.file_utils import UnsafeArchiveError, safe_extract_zip


def _zip(tmp_path, build):
    p = tmp_path / "t.zip"
    with zipfile.ZipFile(p, "w", zipfile.ZIP_DEFLATED) as z:
        build(z)
    return p


def test_zip_slip_rejected(tmp_path):
    p = _zip(tmp_path, lambda z: z.writestr("../evil.txt", "x"))
    with pytest.raises(UnsafeArchiveError):
        safe_extract_zip(p, tmp_path / "out")
    assert not (tmp_path / "evil.txt").exists()


def test_absolute_path_rejected(tmp_path):
    p = _zip(tmp_path, lambda z: z.writestr("/etc/evil.txt", "x"))
    with pytest.raises(UnsafeArchiveError):
        safe_extract_zip(p, tmp_path / "out")


def test_symlink_not_extracted(tmp_path):
    def build(z):
        info = zipfile.ZipInfo("link")
        info.external_attr = (stat.S_IFLNK | 0o777) << 16
        z.writestr(info, "/etc/passwd")
        z.writestr("ok.py", "print(1)")
    out = tmp_path / "out"
    safe_extract_zip(_zip(tmp_path, build), out)
    assert not (out / "link").exists() and (out / "ok.py").exists()


def test_zip_bomb_rejected(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "max_extracted_mb", 1)
    p = _zip(tmp_path, lambda z: z.writestr("big.txt", b"0" * (5 * 1024 * 1024)))
    with pytest.raises(UnsafeArchiveError):
        safe_extract_zip(p, tmp_path / "out")


def test_ignored_dirs_skipped(tmp_path):
    p = _zip(tmp_path, lambda z: (z.writestr("node_modules/a.js", "1"), z.writestr("src/a.py", "1")))
    out = tmp_path / "out"
    safe_extract_zip(p, out)
    assert not (out / "node_modules").exists()


def test_not_a_zip(tmp_path):
    p = tmp_path / "x.zip"
    p.write_bytes(b"not a zip")
    with pytest.raises(UnsafeArchiveError):
        safe_extract_zip(p, tmp_path / "out")
