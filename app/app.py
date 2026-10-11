"""Small notes API used to demo a Docker + CI/CD setup.

Endpoints:
  GET  /            simple HTML page with the visit counter
  GET  /health      health check used by Docker and the deploy job
  GET  /api/notes   list notes
  POST /api/notes   create a note: {"text": "..."}
"""
import os

import psycopg
from flask import Flask, jsonify, request

DATABASE_URL = os.environ.get(
    "DATABASE_URL", "postgresql://app:app@localhost:5432/app"
)
APP_VERSION = os.environ.get("APP_VERSION", "dev")

app = Flask(__name__)


def get_conn():
    return psycopg.connect(DATABASE_URL, autocommit=True)


def init_db():
    with get_conn() as conn:
        conn.execute(
            """CREATE TABLE IF NOT EXISTS notes (
                   id SERIAL PRIMARY KEY,
                   text TEXT NOT NULL,
                   created_at TIMESTAMPTZ NOT NULL DEFAULT now())"""
        )
        conn.execute(
            "CREATE TABLE IF NOT EXISTS visits (id INT PRIMARY KEY, total BIGINT NOT NULL)"
        )
        conn.execute(
            "INSERT INTO visits (id, total) VALUES (1, 0) ON CONFLICT (id) DO NOTHING"
        )


@app.get("/")
def index():
    with get_conn() as conn:
        total = conn.execute(
            "UPDATE visits SET total = total + 1 WHERE id = 1 RETURNING total"
        ).fetchone()[0]
    return (
        "<!doctype html><title>Docker CI/CD demo</title>"
        "<body style='font-family:sans-serif;max-width:40em;margin:3em auto'>"
        "<h1>It works &#x1F433;</h1>"
        f"<p>Version <b>{APP_VERSION}</b>, deployed by GitHub Actions.</p>"
        f"<p>This page has been visited <b>{total}</b> times "
        "(stored in PostgreSQL).</p>"
        "<p>API: <code>/api/notes</code> &middot; health: <code>/health</code></p>"
    )


@app.get("/health")
def health():
    try:
        with get_conn() as conn:
            conn.execute("SELECT 1")
    except psycopg.Error:
        return jsonify(status="error", db="down"), 503
    return jsonify(status="ok", db="up", version=APP_VERSION)


@app.get("/api/notes")
def list_notes():
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT id, text, created_at FROM notes ORDER BY id"
        ).fetchall()
    return jsonify(
        [{"id": r[0], "text": r[1], "created_at": r[2].isoformat()} for r in rows]
    )


@app.post("/api/notes")
def create_note():
    data = request.get_json(silent=True) or {}
    text = str(data.get("text", "")).strip()
    if not text or len(text) > 500:
        return jsonify(error="'text' is required (max 500 characters)"), 400
    with get_conn() as conn:
        note_id = conn.execute(
            "INSERT INTO notes (text) VALUES (%s) RETURNING id", (text,)
        ).fetchone()[0]
    return jsonify(id=note_id, text=text), 201


init_db()
