from __future__ import annotations

import sqlite3
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
DEFAULT_DB_PATH = DATA_DIR / "lab.db"

SCHEMA_SQL = """
DROP TABLE IF EXISTS enrollments;
DROP TABLE IF EXISTS courses;
DROP TABLE IF EXISTS students;

CREATE TABLE students (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    full_name TEXT NOT NULL,
    cohort TEXT NOT NULL,
    age INTEGER NOT NULL CHECK(age > 0),
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE courses (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    course_code TEXT NOT NULL UNIQUE,
    title TEXT NOT NULL,
    credits INTEGER NOT NULL CHECK(credits > 0)
);

CREATE TABLE enrollments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    student_id INTEGER NOT NULL,
    course_id INTEGER NOT NULL,
    score REAL NOT NULL CHECK(score >= 0 AND score <= 100),
    semester TEXT NOT NULL,
    FOREIGN KEY(student_id) REFERENCES students(id),
    FOREIGN KEY(course_id) REFERENCES courses(id)
);
"""

SEED_SQL = """
INSERT INTO students (full_name, cohort, age) VALUES
  ('Alice Nguyen', 'A1', 20),
  ('Bao Tran', 'A1', 21),
  ('Chi Le', 'B2', 19),
  ('Duc Pham', 'A1', 22),
  ('Emi Ho', 'B2', 20);

INSERT INTO courses (course_code, title, credits) VALUES
  ('DB101', 'Database Fundamentals', 3),
  ('PY201', 'Python for Data', 4),
  ('AI301', 'Applied AI', 3);

INSERT INTO enrollments (student_id, course_id, score, semester) VALUES
  (1, 1, 88.5, '2026S1'),
  (1, 2, 91.0, '2026S1'),
  (2, 1, 79.0, '2026S1'),
  (2, 3, 83.5, '2026S1'),
  (3, 2, 95.0, '2026S1'),
  (4, 1, 72.5, '2026S1'),
  (4, 3, 80.0, '2026S1'),
  (5, 2, 89.0, '2026S1');
"""


def create_database(db_path: Path | str = DEFAULT_DB_PATH) -> Path:
    db_path = Path(db_path)
    db_path.parent.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(db_path)
    try:
        conn.executescript(SCHEMA_SQL)
        conn.executescript(SEED_SQL)
        conn.commit()
    finally:
        conn.close()

    return db_path


if __name__ == "__main__":
    path = create_database()
    print(f"Database initialized at: {path}")
