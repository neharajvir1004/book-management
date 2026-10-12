"""
models/book.py

This file contains the two classes that deal with books:

1. Book           -> one book (data + validation + conversion to JSON-friendly dict)
2. BookRepository -> talks to SQLite (create, read, update, delete, search, filter)

Keeping database code here means app.py only has to handle web requests.
"""

import os
import sqlite3
from datetime import date

VALID_STATUSES = ("Available", "Issued")
MAX_TEXT_LENGTH = 200


class Book:
    """Represents a single book."""

    def __init__(self, title, author, category, publication_year=None,
                 status="Available", book_id=None):
        self.id = book_id
        self.title = title
        self.author = author
        self.category = category
        self.publication_year = publication_year
        self.status = status

    # ---------- conversion helpers ----------

    def to_dict(self):
        """Turn the object into a dictionary so Flask can send it as JSON."""
        return {
            "id": self.id,
            "title": self.title,
            "author": self.author,
            "category": self.category,
            "publication_year": self.publication_year,
            "status": self.status,
        }

    @classmethod
    def from_row(cls, row):
        """Build a Book object from a database row."""
        return cls(
            book_id=row["id"],
            title=row["title"],
            author=row["author"],
            category=row["category"],
            publication_year=row["publication_year"],
            status=row["status"],
        )

    # ---------- validation ----------

    @classmethod
    def from_payload(cls, data, existing=None):
        """
        Build a validated Book from JSON data sent by the client.

        - For a new book (POST) pass only `data`.
        - For an update (PUT) pass the `existing` Book: any field missing
          from `data` keeps its old value.

        Raises ValueError with a clear message when the input is invalid.
        """
        if not isinstance(data, dict):
            raise ValueError("Request body must be a JSON object")

        base = existing.to_dict() if existing else {
            "title": None, "author": None, "category": None,
            "publication_year": None, "status": "Available",
        }
        for field in ("title", "author", "category", "publication_year", "status"):
            if field in data:
                base[field] = data[field]

        title = cls._clean_text(base["title"], "Title")
        author = cls._clean_text(base["author"], "Author")
        category = cls._clean_text(base["category"], "Category")
        year = cls._clean_year(base["publication_year"])
        status = cls._clean_status(base["status"])

        return cls(title, author, category, year, status,
                   book_id=existing.id if existing else None)

    @staticmethod
    def _clean_text(value, label):
        if not isinstance(value, str) or not value.strip():
            raise ValueError(f"{label} is required")
        value = value.strip()
        if len(value) > MAX_TEXT_LENGTH:
            raise ValueError(f"{label} must be {MAX_TEXT_LENGTH} characters or fewer")
        return value

    @staticmethod
    def _clean_year(value):
        if value is None or (isinstance(value, str) and not value.strip()):
            return None  # year is optional
        if isinstance(value, bool):
            raise ValueError("Publication year must be a whole number")
        if isinstance(value, str) and value.strip().isdigit():
            value = int(value.strip())
        if not isinstance(value, int):
            raise ValueError("Publication year must be a whole number")
        max_year = date.today().year + 1
        if value < 1 or value > max_year:
            raise ValueError(f"Publication year must be between 1 and {max_year}")
        return value

    @staticmethod
    def _clean_status(value):
        if value not in VALID_STATUSES:
            raise ValueError("Status must be 'Available' or 'Issued'")
        return value


class BookRepository:
    """Handles every SQLite operation for books (a simple data-access layer)."""

    def __init__(self, db_path):
        self.db_path = db_path

    def _connect(self):
        connection = sqlite3.connect(self.db_path)
        connection.row_factory = sqlite3.Row  # access columns by name
        return connection

    def init_db(self):
        """Create the database folder and the books table if they don't exist."""
        folder = os.path.dirname(self.db_path)
        if folder:
            os.makedirs(folder, exist_ok=True)
        connection = self._connect()
        try:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS books (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    title TEXT NOT NULL,
                    author TEXT NOT NULL,
                    category TEXT NOT NULL,
                    publication_year INTEGER,
                    status TEXT NOT NULL DEFAULT 'Available'
                )
                """
            )
            connection.commit()
        finally:
            connection.close()

    # ---------- Read ----------

    def get_all(self, status=None):
        sql = "SELECT * FROM books"
        params = []
        if status:
            sql += " WHERE status = ?"
            params.append(status)
        sql += " ORDER BY id DESC"  # newest first
        return self._fetch_books(sql, params)

    def get_by_id(self, book_id):
        connection = self._connect()
        try:
            row = connection.execute(
                "SELECT * FROM books WHERE id = ?", (book_id,)
            ).fetchone()
        finally:
            connection.close()
        return Book.from_row(row) if row else None

    def search(self, query, status=None):
        """Case-insensitive search in title, author and category."""
        # Escape LIKE wildcards so a search for "%" or "_" is treated as text.
        escaped = (query.replace("\\", "\\\\")
                        .replace("%", "\\%")
                        .replace("_", "\\_"))
        pattern = f"%{escaped}%"
        sql = (
            "SELECT * FROM books WHERE ("
            "LOWER(title) LIKE LOWER(?) ESCAPE '\\' OR "
            "LOWER(author) LIKE LOWER(?) ESCAPE '\\' OR "
            "LOWER(category) LIKE LOWER(?) ESCAPE '\\')"
        )
        params = [pattern, pattern, pattern]
        if status:
            sql += " AND status = ?"
            params.append(status)
        sql += " ORDER BY id DESC"
        return self._fetch_books(sql, params)

    def _fetch_books(self, sql, params):
        connection = self._connect()
        try:
            rows = connection.execute(sql, params).fetchall()
        finally:
            connection.close()
        return [Book.from_row(row) for row in rows]

    # ---------- Create ----------

    def create(self, book):
        connection = self._connect()
        try:
            cursor = connection.execute(
                "INSERT INTO books (title, author, category, publication_year, status) "
                "VALUES (?, ?, ?, ?, ?)",
                (book.title, book.author, book.category,
                 book.publication_year, book.status),
            )
            connection.commit()
            book.id = cursor.lastrowid
        finally:
            connection.close()
        return book

    # ---------- Update ----------

    def update(self, book):
        connection = self._connect()
        try:
            connection.execute(
                "UPDATE books SET title = ?, author = ?, category = ?, "
                "publication_year = ?, status = ? WHERE id = ?",
                (book.title, book.author, book.category,
                 book.publication_year, book.status, book.id),
            )
            connection.commit()
        finally:
            connection.close()
        return book

    # ---------- Delete ----------

    def delete(self, book_id):
        """Delete a book. Returns True if a row was deleted."""
        connection = self._connect()
        try:
            cursor = connection.execute("DELETE FROM books WHERE id = ?", (book_id,))
            connection.commit()
            return cursor.rowcount > 0
        finally:
            connection.close()
