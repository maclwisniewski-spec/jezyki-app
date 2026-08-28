"""
registry.py

Baza SQLite: error_log, syllabus_items, coverage_history, texts (historia
wygenerowanych i zwalidowanych tekstow, uzywana do kontynuacji fabuly).
known_words NIE jest juz zrodlem prawdy (to teraz LingQ) - tabela zostaje
w schemacie tylko dla kompatybilnosci wstecznej.
"""
from __future__ import annotations
import json
import sqlite3
from datetime import date

SCHEMA = """
CREATE TABLE IF NOT EXISTS known_words (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    language TEXT NOT NULL,
    lemma TEXT NOT NULL,
    surface_form TEXT,
    source TEXT,
    date_added TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'recognize' CHECK(status IN ('recognize', 'produce')),
    UNIQUE(language, lemma)
);

CREATE TABLE IF NOT EXISTS error_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    language TEXT NOT NULL,
    sentence TEXT NOT NULL,
    error TEXT NOT NULL,
    category TEXT,
    date TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS syllabus_items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    language TEXT NOT NULL,
    topic TEXT NOT NULL,
    cefr_level TEXT,
    status TEXT NOT NULL DEFAULT 'not_started' CHECK(status IN ('not_started', 'learning', 'tested', 'mastered')),
    test_date TEXT
);

CREATE TABLE IF NOT EXISTS texts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    language TEXT NOT NULL,
    content TEXT NOT NULL,
    target_words TEXT,
    date TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS coverage_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    language TEXT NOT NULL,
    date TEXT NOT NULL,
    token_coverage REAL NOT NULL,
    type_coverage REAL,
    corpus_register TEXT,
    sample_size INTEGER
);
"""


def connect(db_path: str = "marginalia.db") -> sqlite3.Connection:
    conn = sqlite3.connect(db_path)
    conn.executescript(SCHEMA)
    return conn


def get_known_lemmas(conn, language: str, statuses=("recognize", "produce")) -> set[str]:
    placeholders = ",".join("?" for _ in statuses)
    rows = conn.execute(
        f"SELECT lemma FROM known_words WHERE language = ? AND status IN ({placeholders})",
        (language, *statuses),
    ).fetchall()
    return {r[0] for r in rows}


def log_coverage(conn, language: str, token_coverage: float, type_coverage: float | None = None,
                  corpus_register: str = "mixed", sample_size: int | None = None) -> None:
    conn.execute(
        """INSERT INTO coverage_history (language, date, token_coverage, type_coverage, corpus_register, sample_size)
           VALUES (?, ?, ?, ?, ?, ?)""",
        (language, date.today().isoformat(), token_coverage, type_coverage, corpus_register, sample_size),
    )
    conn.commit()


def save_text(conn, language: str, content: str, target_words: list[str] | None = None) -> None:
    conn.execute(
        "INSERT INTO texts (language, content, target_words, date) VALUES (?, ?, ?, ?)",
        (language, content, json.dumps(target_words or []), date.today().isoformat()),
    )
    conn.commit()


def get_recent_texts(conn: sqlite3.Connection, language: str, limit: int = 20) -> list[dict]:
    rows = conn.execute(
        "SELECT id, content, target_words, date FROM texts WHERE language = ? ORDER BY id DESC LIMIT ?",
        (language, limit),
    ).fetchall()
    results = []
    for r in rows:
        targets = []
        if r[2]:
            try:
                targets = json.loads(r[2])
            except Exception:
                targets = []
        results.append({
            "id": r[0],
            "content": r[1],
            "target_words": targets,
            "date": r[3],
        })
    return results
