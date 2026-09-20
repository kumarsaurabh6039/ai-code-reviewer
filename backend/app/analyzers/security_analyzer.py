"""Regex-based security rules (works on all text languages)."""
import re
from dataclasses import dataclass

from ..utils.file_utils import FileInfo
from .base import Finding

PLACEHOLDERS = ("changeme", "change-me", "change_me", "your_", "your-", "example", "placeholder", "xxxx",
                "<", ">", "${", "{{", "os.environ", "getenv", "process.env", "dummy", "secret_key_here",
                "not-a-secret", "todo", "fake", "sample", "insert", "****")


@dataclass
class Rule:
    rule_id: str
    pattern: re.Pattern
    severity: str
    title: str
    description: str
    suggestion: str
    fix_after: str
    langs: set | None = None
    confidence: float = 0.8
    exclude: re.Pattern | None = None
    skip_tests: bool = False
    category: str = "security"


def _r(p, flags=0):
    return re.compile(p, flags)


RULES = [
    Rule("SEC-AWS-KEY", _r(r"AKIA[0-9A-Z]{16}"), "critical", "AWS access key committed to source",
         "An AWS access key ID is hardcoded in the code and also lives on in repository history.",
         "Revoke and rotate the key immediately, then load it from an environment variable or secret manager.",
         "aws_key = os.environ['AWS_ACCESS_KEY_ID']", confidence=0.9),
    Rule("SEC-PRIVATE-KEY", _r(r"-----BEGIN (RSA |EC |OPENSSH |DSA |PGP )?PRIVATE KEY"), "critical",
         "Private key committed to source", "A private key is in the repository; anyone with access to the repo can use it.",
         "Rotate the key, purge it from git history, and use a secret manager.",
         "key = load_from_secret_manager('service-key')", confidence=0.9),
    Rule("SEC-HARDCODED-SECRET",
         _r(r"""(?i)(password|passwd|pwd|secret[_-]?key|client[_-]?secret|api[_-]?key|apikey|access[_-]?token|auth[_-]?token|secret)["']?\s*[:=]\s*["']([^"'\s]{8,})["']"""),
         "high", "Hardcoded secret / credential",
         "A password or API key is written directly in source code (value masked).",
         "Load the secret from an environment variable or secret manager and rotate the old value.",
         "SECRET_KEY = os.environ['SECRET_KEY']", confidence=0.7, skip_tests=True),
    Rule("SEC-SQLI-PY",
         _r(r"""\.(execute|executemany|raw)\(\s*(f["']|["'][^"']*["']\s*(%|\+)|["'][^"']*["']\.format\()|(?<![\w.])text\(\s*f["']"""),
         "high", "Possible SQL injection (string-built query)",
         "The SQL query is built with string formatting or concatenation, so attacker-controlled input could alter the query.",
         "Use parameterized queries or ORM bound parameters.",
         'cursor.execute("SELECT * FROM users WHERE id = %s", (user_id,))', {"Python"}, 0.75),
    Rule("SEC-SQLI-JS",
         _r(r"""\.(query|execute|raw)\(\s*(`[^`]*\$\{|["'][^"']*["']\s*\+)"""),
         "high", "Possible SQL injection (string-built query)",
         "The query is built from a template literal or concatenation, which may allow injection.",
         "Use parameterized queries with placeholders ($1, ?).",
         "db.query('SELECT * FROM users WHERE id = $1', [userId])", {"JavaScript", "TypeScript"}, 0.75),
    Rule("SEC-EVAL-PY", _r(r"(?<![\w.])(eval|exec)\s*\("), "high", "Use of eval()/exec()",
         "eval/exec run dynamic code; with attacker-controlled input this can lead to remote code execution.",
         "Use ast.literal_eval, json.loads or an explicit dispatch table.",
         "value = ast.literal_eval(user_text)", {"Python"}, 0.8),
    Rule("SEC-EVAL-JS", _r(r"(?<![\w.])eval\s*\(|new\s+Function\s*\("), "high", "Use of eval() / new Function()",
         "Dynamic code execution increases XSS/RCE risk.", "Use JSON.parse or a safe parser.",
         "const data = JSON.parse(text)", {"JavaScript", "TypeScript", "HTML"}, 0.8),
    Rule("SEC-SHELL", _r(r"shell\s*=\s*True|os\.system\("), "high", "Shell command execution",
         "Running commands through a shell risks command injection.",
         "Use subprocess.run([...args...]) and keep shell=False.",
         "subprocess.run(['ls', path], check=True)", {"Python"}, 0.75),
    Rule("SEC-YAML-LOAD", _r(r"yaml\.load\("), "medium", "Unsafe yaml.load()",
         "yaml.load without SafeLoader can construct arbitrary objects.", "Use yaml.safe_load.",
         "data = yaml.safe_load(stream)", {"Python"}, 0.8, exclude=_r(r"SafeLoader")),
    Rule("SEC-PICKLE", _r(r"pickle\.loads?\("), "medium", "Unsafe deserialization (pickle)",
         "Loading untrusted data with pickle can execute arbitrary code.", "Use JSON or other safe formats.",
         "data = json.loads(payload)", {"Python"}, 0.7),
    Rule("SEC-WEAK-HASH", _r(r"""hashlib\.(md5|sha1)\(|createHash\(\s*["'](md5|sha1)["']"""), "medium",
         "Weak hash algorithm (MD5/SHA-1)", "MD5/SHA-1 are broken for collision resistance and unsuitable for security purposes.",
         "Use bcrypt/argon2 for passwords and SHA-256 for integrity checks.",
         "hashlib.sha256(data).hexdigest()", None, 0.75),
    Rule("SEC-TLS-VERIFY",
         _r(r"verify\s*=\s*False|rejectUnauthorized\s*:\s*false|_create_unverified_context"), "high",
         "TLS certificate verification disabled", "HTTPS certificate checking is off, which allows man-in-the-middle attacks.",
         "Keep verification on; if you use a custom CA, pass its bundle path.", "requests.get(url, timeout=10)", None, 0.85),
    Rule("SEC-DEBUG", _r(r"(?i)^\s*DEBUG\s*=\s*True|\.run\([^)]*debug\s*=\s*True"), "medium",
         "Debug mode enabled", "Debug mode exposes stack traces and an interactive console in production.",
         "Control the debug flag from an environment variable and keep it False in production.",
         "DEBUG = os.getenv('DEBUG', 'false').lower() == 'true'", {"Python"}, 0.7),
    Rule("SEC-CORS",
         _r(r"""allow_origins\s*=\s*\[\s*["']\*["']|Access-Control-Allow-Origin["']?\s*[:,]\s*["']\*|cors\(\s*\{\s*origin\s*:\s*["']\*["']"""),
         "medium", "Permissive CORS (allows any origin)", "Any website can call the API from a browser.",
         "Allow only trusted frontend origins.", 'allow_origins=["https://app.example.com"]', None, 0.75),
    Rule("SEC-JWT-NOVERIFY", _r(r"""verify_(exp|signature|aud)["']?\s*[:=]\s*(False|false)"""), "high",
         "JWT validation disabled", "JWT expiry/signature checks are disabled, so expired or forged tokens may be accepted.",
         "Always keep expiry and signature verification enabled when decoding tokens.",
         "payload = jwt.decode(token, key, algorithms=['HS256'])  # exp verified by default", None, 0.9),
    Rule("SEC-JWT-NONE", _r(r"""algorithms\s*=\s*\[[^\]]*["']none["']"""), "critical",
         "JWT 'none' algorithm allowed", "The 'none' algorithm lets unsigned tokens be accepted.",
         "Allow only strong algorithms (HS256/RS256).", "jwt.decode(token, key, algorithms=['HS256'])", None, 0.9),
    Rule("SEC-XSS",
         _r(r"\.innerHTML\s*=|document\.write\(|dangerouslySetInnerHTML|bypassSecurityTrust(Html|Script|Url|ResourceUrl)"),
         "medium", "Possible XSS sink", "Inserting untrusted HTML into the DOM risks cross-site scripting.",
         "Use textContent or sanitize the HTML (e.g. DOMPurify).", "el.textContent = userInput",
         {"JavaScript", "TypeScript", "HTML"}, 0.65),
]


def _is_comment(line: str) -> bool:
    s = line.lstrip()
    return s.startswith(("#", "//", "*", "/*"))


def analyze_security(fi: FileInfo) -> list[Finding]:
    if fi.language in {"Markdown", "CSS"}:
        return []
    findings: list[Finding] = []
    lines = fi.content.splitlines()
    for rule in RULES:
        if rule.langs and fi.language not in rule.langs:
            continue
        if rule.skip_tests and fi.is_test:
            continue
        if fi.non_production and rule.severity != "critical":
            continue
        for i, line in enumerate(lines, start=1):
            if len(line) > 2000:
                continue
            m = rule.pattern.search(line)
            if not m:
                continue
            if rule.exclude and rule.exclude.search(line):
                continue
            if _is_comment(line) and not rule.rule_id.startswith(("SEC-AWS", "SEC-PRIVATE")):
                continue
            if rule.rule_id == "SEC-HARDCODED-SECRET":
                value = m.group(2).lower()
                if any(p in value for p in PLACEHOLDERS) or any(p in line.lower() for p in ("os.environ", "getenv", "process.env")):
                    continue
            before = re.sub(r"([\"'])[^\"']{8,}\1", r"\1***\1", line.strip()) if rule.rule_id in (
                "SEC-HARDCODED-SECRET", "SEC-AWS-KEY") else line.strip()
            if rule.rule_id == "SEC-PRIVATE-KEY":
                before = "-----BEGIN PRIVATE KEY----- ..."
            findings.append(Finding(fi.rel_path, i, rule.severity, rule.category, rule.title, rule.description,
                                    rule.suggestion, rule.rule_id, confidence=rule.confidence,
                                    fix_before=before[:300], fix_after=rule.fix_after))
    return findings
