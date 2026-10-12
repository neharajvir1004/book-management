"""
app.py - Book Management Web App (Flask backend)

Responsibilities:
1. Configure Flask
2. Connect to SQLite (through BookRepository)
3. Create the table if needed
4. Provide the REST API
5. Validate input
6. Run CRUD / search / filter operations
7. Return JSON
8. Handle errors
9. Serve the frontend page
"""

import os

from flask import Flask, jsonify, render_template, request

from models.book import VALID_STATUSES, Book, BookRepository

# ---------- 1. Configure Flask ----------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
# BOOK_DB_PATH is optional (used by the automated tests); normally the default is used.
DB_PATH = os.environ.get(
    "BOOK_DB_PATH", os.path.join(BASE_DIR, "database", "book_management.db")
)

app = Flask(__name__)
app.json.sort_keys = False  # keep JSON keys in the order we write them (id first)

# ---------- 2 & 3. Connect to SQLite and create the table ----------
repo = BookRepository(DB_PATH)
repo.init_db()


# ---------- Small helpers ----------
def error_response(message, status_code):
    """Every error is returned as JSON like: {"error": "Book not found"}"""
    return jsonify({"error": message}), status_code


def parse_book_id(book_id):
    """Convert the id from the URL to an int. Raises ValueError if invalid."""
    if not book_id.isdigit() or int(book_id) < 1:
        raise ValueError("Invalid book ID")
    return int(book_id)


def get_status_filter():
    """Read ?status=... from the URL. Returns None when not given or 'All'."""
    status = request.args.get("status", "").strip()
    if status == "" or status.lower() == "all":
        return None
    if status not in VALID_STATUSES:
        raise ValueError("Status filter must be 'Available' or 'Issued'")
    return status


def get_json_body():
    """Read the JSON body. Raises ValueError if it is missing or invalid."""
    data = request.get_json(silent=True)
    if data is None:
        raise ValueError("Request body must be valid JSON")
    return data


# ---------- 9. Serve the frontend ----------
@app.route("/")
def index():
    return render_template("index.html")


# ---------- 4. REST API ----------

# GET /api/books            -> all books
# GET /api/books?status=Available
@app.route("/api/books", methods=["GET"])
def get_books():
    try:
        status = get_status_filter()
    except ValueError as error:
        return error_response(str(error), 400)
    books = repo.get_all(status)
    return jsonify([book.to_dict() for book in books]), 200


# GET /api/books/search?q=python
@app.route("/api/books/search", methods=["GET"])
def search_books():
    query = request.args.get("q", "").strip()
    if not query:
        return error_response("Search query 'q' is required", 400)
    try:
        status = get_status_filter()
    except ValueError as error:
        return error_response(str(error), 400)
    books = repo.search(query, status)
    return jsonify([book.to_dict() for book in books]), 200


# GET /api/books/<id>
@app.route("/api/books/<book_id>", methods=["GET"])
def get_book(book_id):
    try:
        book_id = parse_book_id(book_id)
    except ValueError as error:
        return error_response(str(error), 400)
    book = repo.get_by_id(book_id)
    if book is None:
        return error_response("Book not found", 404)
    return jsonify(book.to_dict()), 200


# POST /api/books
@app.route("/api/books", methods=["POST"])
def create_book():
    try:
        book = Book.from_payload(get_json_body())  # validates the input
    except ValueError as error:
        return error_response(str(error), 400)
    repo.create(book)
    return jsonify(book.to_dict()), 201


# PUT /api/books/<id>
@app.route("/api/books/<book_id>", methods=["PUT"])
def update_book(book_id):
    try:
        book_id = parse_book_id(book_id)
        data = get_json_body()
    except ValueError as error:
        return error_response(str(error), 400)

    existing = repo.get_by_id(book_id)
    if existing is None:
        return error_response("Book not found", 404)

    try:
        book = Book.from_payload(data, existing=existing)
    except ValueError as error:
        return error_response(str(error), 400)

    repo.update(book)
    return jsonify(book.to_dict()), 200


# DELETE /api/books/<id>
@app.route("/api/books/<book_id>", methods=["DELETE"])
def delete_book(book_id):
    try:
        book_id = parse_book_id(book_id)
    except ValueError as error:
        return error_response(str(error), 400)
    if not repo.delete(book_id):
        return error_response("Book not found", 404)
    return jsonify({"message": "Book deleted"}), 200


# ---------- 8. Error handling ----------
@app.errorhandler(404)
def handle_not_found(error):
    if request.path.startswith("/api/"):
        return error_response("Endpoint not found", 404)
    return "Page not found", 404


@app.errorhandler(405)
def handle_method_not_allowed(error):
    return error_response("Method not allowed for this endpoint", 405)


@app.errorhandler(500)
def handle_server_error(error):
    return error_response("Internal server error", 500)


if __name__ == "__main__":
    # debug=True reloads the server when you save a file (great while learning).
    # Turn it off before deploying anywhere public.
    app.run(host="127.0.0.1", port=5000, debug=True)
