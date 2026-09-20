"""Safe ZIP extraction and repository scanning.

IMPORTANT: uploaded code is NEVER executed. We only read it as text.
"""
import os
import re
import shutil
import stat
import zipfile
from dataclasses import dataclass, field
from pathlib import Path, PurePosixPath

from ..core.config import settings
from .language_detector import LOGIC_LANGS, detect_language, is_test_file

IGNORE_DIRS = {
    ".git", "node_modules", "venv", ".venv", "env", "__pycache__", "dist", "build", ".idea", ".vscode",
    ".next", ".angular", "coverage", ".pytest_cache", ".mypy_cache", "site-packages", "target", "vendor",
    ".tox", "__MACOSX",
}
NON_PROD_DIRS = {"docs", "docs_src", "doc", "examples", "example", "samples", "sample", "fixtures", "scripts_dev"}
IGNORE_SUFFIXES = (".min.js", ".min.css", ".map")
IGNORE_NAMES = {"package-lock.json", "yarn.lock", "pnpm-lock.yaml", "poetry.lock", ".env"}


class UnsafeArchiveError(ValueError):
    pass


def _is_ignored_path(parts: tuple[str, ...]) -> bool:
    return any(p in IGNORE_DIRS for p in parts)


def safe_extract_zip(zip_path: Path, dest: Path) -> Path:
    """Extract with zip-slip, zip-bomb and symlink protection. Returns repo root dir."""
    dest.mkdir(parents=True, exist_ok=True)
    dest_resolved = dest.resolve()
    max_total = settings.max_extracted_mb * 1024 * 1024
    total = 0
    count = 0
    try:
        zf = zipfile.ZipFile(zip_path)
    except zipfile.BadZipFile as e:
        raise UnsafeArchiveError("File is not a valid ZIP archive") from e

    with zf:
        infos = zf.infolist()
        if len(infos) > settings.max_files * 4:
            raise UnsafeArchiveError("ZIP contains too many entries")
        if sum(i.file_size for i in infos) > max_total * 3:
            raise UnsafeArchiveError("ZIP uncompressed size is far above the limit")

        for info in infos:
            name = info.filename.replace("\\", "/")
            pure = PurePosixPath(name)
            if pure.is_absolute() or re.match(r"^[A-Za-z]:", name) or ".." in pure.parts:
                raise UnsafeArchiveError(f"Unsafe path in ZIP: {info.filename}")
            mode = info.external_attr >> 16
            if stat.S_ISLNK(mode):
                continue  # never extract symlinks
            if _is_ignored_path(pure.parts):
                continue  # skip node_modules, .git, venv ... (saves disk)
            target = (dest / pure).resolve()
            if dest_resolved != target and dest_resolved not in target.parents:
                raise UnsafeArchiveError(f"Unsafe path in ZIP: {info.filename}")
            if info.is_dir():
                target.mkdir(parents=True, exist_ok=True)
                continue
            count += 1
            if count > settings.max_files * 2:
                raise UnsafeArchiveError("ZIP exceeds the file-count limit")
            target.parent.mkdir(parents=True, exist_ok=True)
            with zf.open(info) as src, open(target, "wb") as out:
                while True:
                    chunk = src.read(64 * 1024)
                    if not chunk:
                        break
                    total += len(chunk)  # count REAL bytes; declared sizes can lie
                    if total > max_total:
                        raise UnsafeArchiveError("Extracted size limit exceeded (possible zip bomb)")
                    out.write(chunk)

    entries = [e for e in dest.iterdir() if e.name != "__MACOSX"]
    if len(entries) == 1 and entries[0].is_dir():
        return entries[0]  # GitHub-style zips have one top-level folder
    return dest


def remove_tree(path: Path | str | None) -> None:
    if path and Path(path).exists():
        shutil.rmtree(path, ignore_errors=True)


@dataclass
class FileInfo:
    rel_path: str
    language: str
    size: int
    lines: int
    loc: int
    is_test: bool
    content: str = field(repr=False, default="")

    @property
    def non_production(self) -> bool:
        """Tests, docs and example code: quality/security noise is suppressed there."""
        parts = {x.lower() for x in PurePosixPath(self.rel_path).parts[:-1]}
        return self.is_test or bool(parts & NON_PROD_DIRS)

    @property
    def is_logic(self) -> bool:
        return self.language in LOGIC_LANGS and not self.is_test


@dataclass
class ScanResult:
    root: Path
    files: list[FileInfo]
    skipped: list[tuple[str, str]]

    def by_path(self) -> dict[str, FileInfo]:
        return {f.rel_path: f for f in self.files}


def _ignored_file(name: str) -> bool:
    if name in IGNORE_NAMES or name.endswith(IGNORE_SUFFIXES):
        return True
    return name.startswith(".env.") and name not in (".env.example", ".env.sample")


def scan_repository(root: Path) -> ScanResult:
    files: list[FileInfo] = []
    skipped: list[tuple[str, str]] = []
    total_bytes = 0
    max_bytes = settings.max_extracted_mb * 1024 * 1024
    for dirpath, dirnames, filenames in os.walk(root, followlinks=False):
        dirnames[:] = sorted(d for d in dirnames
                             if d not in IGNORE_DIRS and not os.path.islink(os.path.join(dirpath, d)))
        for fn in sorted(filenames):
            if _ignored_file(fn):
                continue
            ap = Path(dirpath) / fn
            if ap.is_symlink():
                continue
            lang = detect_language(fn)
            if not lang:
                continue
            rel = ap.relative_to(root).as_posix()
            size = ap.stat().st_size
            if size > settings.max_file_kb * 1024:
                skipped.append((rel, "file too large"))
                continue
            if len(files) >= settings.max_files or total_bytes + size > max_bytes:
                skipped.append((rel, "scan limit reached"))
                continue
            data = ap.read_bytes()
            if b"\0" in data[:2048]:
                skipped.append((rel, "binary"))
                continue
            text = data.decode("utf-8", errors="replace")
            lines = text.count("\n") + (1 if text and not text.endswith("\n") else 0)
            loc = sum(1 for ln in text.splitlines() if ln.strip())
            total_bytes += size
            files.append(FileInfo(rel, lang, size, lines, loc, is_test_file(rel), text))
    return ScanResult(root, files, skipped)
