"""Pure-python BM25 retriever over code chunks (no extra dependencies).
Swap this for pgvector similarity search later; the interface stays the same."""
import math
import re
from collections import Counter

from ..models import CodeChunk

_camel = re.compile(r"(?<=[a-z0-9])(?=[A-Z])")
_word = re.compile(r"[A-Za-z_][A-Za-z0-9_]+")
STOP = {"the", "and", "for", "are", "this", "that", "with", "what", "why", "how", "does", "from", "have", "not",
        "you", "can", "which", "where", "when", "code", "file", "there", "into", "about", "your", "mera", "meri",
        "hai", "kya", "kyun", "kaise", "ka", "ki", "ke", "mein", "se", "ko"}


def tokenize(text: str) -> list[str]:
    tokens = []
    for w in _word.findall(text):
        parts = [p for p in re.split(r"_+", _camel.sub("_", w)) if p]
        for p in parts + ([w.lower()] if len(parts) > 1 else []):
            p = p.lower()
            if len(p) > 2 and p not in STOP:
                tokens.append(p)
    return tokens


class BM25Index:
    def __init__(self, chunks: list[CodeChunk], k1: float = 1.5, b: float = 0.75):
        self.chunks = chunks
        self.k1, self.b = k1, b
        self.docs = [Counter(tokenize(c.file_path + "\n" + c.file_path + "\n" + c.content)) for c in chunks]
        self.lens = [sum(d.values()) for d in self.docs]
        self.avg = (sum(self.lens) / len(self.lens)) if self.lens else 1.0
        df: Counter = Counter()
        for d in self.docs:
            df.update(d.keys())
        n = len(self.docs)
        self.idf = {t: math.log(1 + (n - f + 0.5) / (f + 0.5)) for t, f in df.items()}

    def _expand(self, q: str) -> dict[str, float]:
        """Exact term = weight 1.0; shared-prefix terms (auth ~ authentication) = 0.6."""
        out = {q: 1.0} if q in self.idf else {}
        if len(q) >= 4:
            for t in self.idf:
                if t != q and len(t) >= 4 and (t.startswith(q) or q.startswith(t)):
                    out[t] = max(out.get(t, 0), 0.6)
        return out

    def search(self, query: str, k: int = 6) -> list[CodeChunk]:
        weights: dict[str, float] = {}
        for q in set(tokenize(query)):
            for t, w in self._expand(q).items():
                weights[t] = max(weights.get(t, 0), w)
        scored = []
        for i, d in enumerate(self.docs):
            score = 0.0
            for t, w in weights.items():
                f = d.get(t)
                if f:
                    score += w * self.idf.get(t, 0) * f * (self.k1 + 1) / (f + self.k1 * (1 - self.b + self.b * self.lens[i] / self.avg))
            if score > 0:
                path = self.chunks[i].file_path.lower()
                if path.startswith("test") or "/test" in path or "/spec" in path:
                    score *= 0.7  # prefer production code over tests when answering
                scored.append((score, i))
        scored.sort(reverse=True)
        return [self.chunks[i] for _, i in scored[:k]]


_cache: dict[int, tuple[int, BM25Index]] = {}


def get_index(repo_id: int, chunks: list[CodeChunk]) -> BM25Index:
    """Cache the index per repository; rebuild when chunk count changes."""
    cached = _cache.get(repo_id)
    if cached and cached[0] == len(chunks):
        return cached[1]
    idx = BM25Index(chunks)
    _cache[repo_id] = (len(chunks), idx)
    return idx


def invalidate(repo_id: int) -> None:
    _cache.pop(repo_id, None)
