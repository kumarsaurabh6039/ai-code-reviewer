"""Project-level checks: README, dependency files, .gitignore, dependency list."""
import json
import re

from ..utils.file_utils import FileInfo
from .base import Finding


def analyze_project(files: list[FileInfo], root_names: set[str]) -> tuple[list[Finding], dict]:
    findings: list[Finding] = []
    by_name = {f.rel_path.lower(): f for f in files}
    readme = next((f for f in files if f.rel_path.lower() in {"readme.md", "readme.rst", "readme.txt", "readme"}), None)
    readme_lines = readme.loc if readme else 0
    logic = [f for f in files if f.is_logic]

    if logic and not readme:
        findings.append(Finding("README.md", 1, "medium", "documentation", "README is missing",
                                "There is no README, so newcomers cannot tell what the project does or how to run it.",
                                "Add a README with purpose, setup steps, usage and project structure.",
                                "DOC-NO-README", confidence=0.9))
    elif readme and readme_lines < 10:
        findings.append(Finding(readme.rel_path, 1, "low", "documentation", "README is very short",
                                f"README has only {readme_lines} non-empty lines.",
                                "Document setup, configuration, how to run tests, and architecture.",
                                "DOC-SHORT-README", confidence=0.7))

    deps: list[str] = []
    for name in ("requirements.txt", "package.json", "pyproject.toml", "pipfile"):
        if name in by_name:
            f = by_name[name]
            if name == "requirements.txt":
                deps += [re.split(r"[=<>~! \[;]", ln.strip())[0] for ln in f.content.splitlines()
                         if ln.strip() and not ln.startswith(("#", "-"))]
            elif name == "package.json":
                try:
                    data = json.loads(f.content)
                    deps += list((data.get("dependencies") or {}).keys()) + list((data.get("devDependencies") or {}).keys())
                except ValueError:
                    pass
    has_py = any(f.language == "Python" for f in logic)
    has_js = any(f.language in {"JavaScript", "TypeScript"} for f in logic)
    if has_py and not ({"requirements.txt", "pyproject.toml", "pipfile", "setup.py"} & set(by_name)):
        findings.append(Finding("requirements.txt", 1, "medium", "documentation", "No Python dependency file",
                                "No requirements.txt / pyproject.toml found, so the environment cannot be reproduced.",
                                "Add requirements.txt (pip freeze) or pyproject.toml with pinned versions.",
                                "DOC-NO-DEPS", confidence=0.8))
    if has_js and "package.json" not in by_name and len(logic) > 3:
        findings.append(Finding("package.json", 1, "low", "documentation", "No package.json found",
                                "JavaScript/TypeScript sources without a package.json are hard to install and run.",
                                "Add package.json with dependencies and scripts.", "DOC-NO-PKG", confidence=0.6))
    if ".gitignore" not in root_names and logic:
        findings.append(Finding(".gitignore", 1, "low", "code_smell", "No .gitignore",
                                "Without .gitignore, build output, virtualenvs and secrets are easily committed by mistake.",
                                "Add a .gitignore for your stack (node_modules/, venv/, .env, dist/ ...).",
                                "PRJ-NO-GITIGNORE", confidence=0.7))
    return findings, {"readme": bool(readme), "readme_lines": readme_lines, "dependencies": sorted(set(deps))[:100]}
