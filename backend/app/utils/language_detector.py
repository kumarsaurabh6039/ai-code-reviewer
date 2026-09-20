from pathlib import PurePosixPath

EXT_LANG = {
    ".py": "Python",
    ".js": "JavaScript", ".jsx": "JavaScript", ".mjs": "JavaScript", ".cjs": "JavaScript",
    ".ts": "TypeScript", ".tsx": "TypeScript",
    ".html": "HTML", ".htm": "HTML",
    ".css": "CSS", ".scss": "CSS",
    ".json": "JSON",
    ".sql": "SQL",
    ".md": "Markdown",
    ".yml": "YAML", ".yaml": "YAML", ".toml": "TOML",
}
CONFIG_FILES = {"requirements.txt", "package.json", "pyproject.toml", "Dockerfile", "Pipfile", "setup.py"}
CODE_LANGS = {"Python", "JavaScript", "TypeScript", "HTML", "CSS", "SQL"}  # counted in language %
LOGIC_LANGS = {"Python", "JavaScript", "TypeScript"}  # counted as "source" for test coverage


def detect_language(filename: str) -> str | None:
    name = PurePosixPath(filename).name
    if name in CONFIG_FILES:
        return EXT_LANG.get(PurePosixPath(name).suffix.lower(), "Config")
    return EXT_LANG.get(PurePosixPath(name).suffix.lower())


def is_test_file(rel_path: str) -> bool:
    p = PurePosixPath(rel_path)
    name = p.name.lower()
    if name.startswith("test_") or name.endswith(("_test.py", ".spec.ts", ".spec.js", ".test.ts", ".test.js",
                                                  ".test.tsx", ".test.jsx", ".spec.tsx")):
        return True
    return any(part.lower() in {"tests", "test", "__tests__", "spec"} for part in p.parts[:-1])
