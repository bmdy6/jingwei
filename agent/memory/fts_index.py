"""FTS5 全文搜索索引 — 支持记忆的语义检索."""
import sqlite3
import re
from typing import Any

# 使用 100% 绝对无乱码的显式 Unicode 转义码点范围
_CJK_RE = re.compile(r'([\u4e00-\u9fff\u3400-\u4dbf\u3000-\u303f\uff00-\uffef])')

def _cjk_space(text: str) -> str:
    """Insert spaces around CJK characters so unicode61 tokenizer splits each char."""
    if not text:
        return ""
    return _CJK_RE.sub(r' \1 ', text)

def create_search_table(conn, name: str, columns: tuple[str, ...], tokenizer="unicode61"):
    """Use an ordinary SQLite table when the build has no FTS5 module."""
    # All identifiers come from static application code, never tool/user input.
    fields = ", ".join(columns)
    try:
        conn.execute(f"CREATE VIRTUAL TABLE IF NOT EXISTS {name} USING fts5({fields}, tokenize='{tokenizer}')")
    except sqlite3.OperationalError as exc:
        if "no such module: fts5" not in str(exc).lower():
            raise
        schema = ", ".join(f"{column} TEXT" for column in columns)
        conn.execute(f"CREATE TABLE IF NOT EXISTS {name} ({schema})")


def create_table(conn: sqlite3.Connection):
    create_search_table(conn, "memories_fts",
                        ("content", "description", "memory_type", "filename", "timestamp"),
                        "porter unicode61")

def populate(conn: sqlite3.Connection, rows: list[dict]):
    """批量插入记忆."""
    for row in rows:
        content_cjk = _cjk_space(row["content"])
        desc_cjk = _cjk_space(row["description"])
        conn.execute(
            "INSERT INTO memories_fts(content, description, memory_type, filename, timestamp) VALUES (?, ?, ?, ?, ?)",
            (content_cjk, desc_cjk, row["memory_type"], row["filename"], row.get("timestamp", "")),
        )

def search(conn: sqlite3.Connection, query: str, limit: int = 5) -> list[dict]:
    """FTS5 全文搜索，BM25 排序."""
    query_cjk = _cjk_space(query)
    rows = conn.execute(
        """SELECT rowid, content, description, memory_type, filename, timestamp, rank
           FROM memories_fts WHERE memories_fts MATCH ?
           ORDER BY rank LIMIT ?""",
        (query_cjk, limit),
    ).fetchall()
    return [{"id": r[0], "content": r[1], "description": r[2],
            "memory_type": r[3], "filename": r[4], "timestamp": r[5], "rank": r[6]} for r in rows]

def rebuild(conn: sqlite3.Connection):
    conn.execute("INSERT INTO memories_fts(memories_fts) VALUES('rebuild')")


