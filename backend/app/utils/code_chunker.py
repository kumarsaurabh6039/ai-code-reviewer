from dataclasses import dataclass

CHUNK_LINES = 60
OVERLAP = 10


@dataclass
class Chunk:
    file_path: str
    start_line: int
    end_line: int
    language: str
    content: str


def chunk_file(path: str, language: str, text: str, max_lines: int = 3000) -> list[Chunk]:
    lines = text.splitlines()[:max_lines]
    chunks: list[Chunk] = []
    i = 0
    while i < len(lines):
        window = lines[i:i + CHUNK_LINES]
        body = "\n".join(window).strip()
        if body:
            chunks.append(Chunk(path, i + 1, i + len(window), language, "\n".join(window)))
        if i + CHUNK_LINES >= len(lines):
            break
        i += CHUNK_LINES - OVERLAP
    return chunks
