"""
Automated API tests (optional, but a nice thing to show in an interview).

Run from the project folder with:
    python -m unittest discover tests -v

The tests use a temporary database, so your real data is never touched.
"""

import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Point the app at a temporary database BEFORE importing it.
TEMP_DIR = tempfile.mkdtemp()
os.environ["BOOK_DB_PATH"] = os.path.join(TEMP_DIR, "test_books.db")

from app import app, repo  # noqa: E402


class BookApiTests(unittest.TestCase):
    def setUp(self):
        self.client = app.test_client()
        # start every test with an empty table
        connection = repo._connect()
        connection.execute("DELETE FROM books")
        connection.execute("DELETE FROM sqlite_sequence WHERE name = 'books'")  # ids restart at 1
        connection.commit()
        connection.close()

    def add_book(self, **overrides):
        data = {"title": "Python Crash Course", "author": "Eric Matthes",
                "category": "Programming", "publication_year": 2023}
        data.update(overrides)
        return self.client.post("/api/books", json=data)

    # ---- Create / Read ----
    def test_create_returns_201_and_defaults_to_available(self):
        response = self.add_book()
        self.assertEqual(response.status_code, 201)
        body = response.get_json()
        self.assertEqual(body["status"], "Available")
        self.assertEqual(body["id"], 1)

    def test_get_all_and_get_one(self):
        self.add_book()
        self.assertEqual(len(self.client.get("/api/books").get_json()), 1)
        one = self.client.get("/api/books/1")
        self.assertEqual(one.status_code, 200)
        self.assertEqual(one.get_json()["title"], "Python Crash Course")

    # ---- Update / Delete ----
    def test_update_changes_fields(self):
        self.add_book()
        response = self.client.put("/api/books/1", json={"title": "Python Crash Course 3rd Ed", "status": "Issued"})
        self.assertEqual(response.status_code, 200)
        body = response.get_json()
        self.assertEqual(body["title"], "Python Crash Course 3rd Ed")
        self.assertEqual(body["status"], "Issued")
        self.assertEqual(body["author"], "Eric Matthes")  # untouched

    def test_delete_then_404(self):
        self.add_book()
        self.assertEqual(self.client.delete("/api/books/1").status_code, 200)
        self.assertEqual(self.client.get("/api/books/1").status_code, 404)
        self.assertEqual(self.client.delete("/api/books/1").status_code, 404)

    # ---- Search / filter ----
    def test_search_is_case_insensitive_across_fields(self):
        self.add_book()
        self.add_book(title="Clean Code", author="Robert Martin", category="Software")
        for q in ("python", "PYTHON", "matthes", "software"):
            result = self.client.get(f"/api/books/search?q={q}")
            self.assertEqual(result.status_code, 200, q)
            self.assertEqual(len(result.get_json()), 1, q)

    def test_search_treats_percent_as_plain_text(self):
        self.add_book()
        self.assertEqual(self.client.get("/api/books/search?q=%25").get_json(), [])

    def test_status_filter(self):
        self.add_book()
        self.add_book(title="Clean Code", status="Issued")
        available = self.client.get("/api/books?status=Available").get_json()
        issued = self.client.get("/api/books?status=Issued").get_json()
        self.assertEqual([b["title"] for b in available], ["Python Crash Course"])
        self.assertEqual([b["title"] for b in issued], ["Clean Code"])
        self.assertEqual(len(self.client.get("/api/books?status=All").get_json()), 2)

    def test_search_combined_with_status(self):
        self.add_book()
        self.add_book(title="Python Tricks", status="Issued")
        result = self.client.get("/api/books/search?q=python&status=Issued").get_json()
        self.assertEqual([b["title"] for b in result], ["Python Tricks"])

    # ---- Validation and errors ----
    def test_missing_required_fields_return_400(self):
        for field in ("title", "author", "category"):
            response = self.add_book(**{field: "   "})
            self.assertEqual(response.status_code, 400, field)
            self.assertIn("error", response.get_json())

    def test_invalid_year_and_status_return_400(self):
        self.assertEqual(self.add_book(publication_year="abc").status_code, 400)
        self.assertEqual(self.add_book(publication_year=-5).status_code, 400)
        self.assertEqual(self.add_book(publication_year=3000).status_code, 400)
        self.assertEqual(self.add_book(status="Lost").status_code, 400)

    def test_year_is_optional(self):
        self.assertEqual(self.add_book(publication_year=None).status_code, 201)

    def test_invalid_json_returns_400(self):
        response = self.client.post("/api/books", data="not json", content_type="application/json")
        self.assertEqual(response.status_code, 400)
        response = self.client.post("/api/books")
        self.assertEqual(response.status_code, 400)
        response = self.client.post("/api/books", json=["a", "list"])
        self.assertEqual(response.status_code, 400)

    def test_invalid_and_missing_ids(self):
        self.assertEqual(self.client.get("/api/books/abc").status_code, 400)
        self.assertEqual(self.client.get("/api/books/0").status_code, 400)
        self.assertEqual(self.client.get("/api/books/999").status_code, 404)
        self.assertEqual(self.client.put("/api/books/999", json={"title": "x"}).status_code, 404)

    def test_bad_filter_and_empty_search(self):
        self.assertEqual(self.client.get("/api/books?status=Lost").status_code, 400)
        self.assertEqual(self.client.get("/api/books/search").status_code, 400)

    def test_unknown_api_route_returns_json_404(self):
        response = self.client.get("/api/nothing")
        self.assertEqual(response.status_code, 404)
        self.assertIn("error", response.get_json())

    def test_sql_injection_text_is_stored_safely(self):
        self.add_book(title="x'); DROP TABLE books;--")
        self.assertEqual(len(self.client.get("/api/books").get_json()), 1)

    def test_home_page_loads(self):
        self.assertEqual(self.client.get("/").status_code, 200)


if __name__ == "__main__":
    unittest.main()
