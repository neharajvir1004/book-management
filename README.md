# Book Management Web App

## Overview

A small full-stack web application for managing a personal or small-library book collection. You can add, view, search, filter, edit and delete books, and mark each book as **Available** or **Issued**.

It is intentionally simple so it can be understood and explained in a Python Developer interview.

## Features

- Add a book (title, author, category, publication year, status; default status is `Available`)
- View all books as cards with an Available/Issued badge
- Search by title, author or category (case-insensitive)
- Filter by All / Available / Issued (works together with search)
- Edit a book
- Issue / Return a book with one click
- Delete a book after a confirmation dialog
- Empty states, success/error messages, responsive mobile-friendly layout
- Input validation and JSON error responses

## Tech Stack

Python 3, Flask, SQLite (built into Python), HTML, CSS, JavaScript (`fetch()`), REST API, JSON, Postman, Git/GitHub.

## Architecture

```text
                 User
                   |
                   v
          HTML / CSS / JavaScript
                   |
                   v
             Flask REST API   (app.py)
                   |
                   v
       Book / BookRepository  (models/book.py)
                   |
                   v
                SQLite
```

## Folder Structure

```text
book-management/
├── app.py                      # Flask app: routes, validation errors, JSON responses
├── requirements.txt            # Python dependencies (Flask)
├── README.md
├── .gitignore
├── database/
│   └── book_management.db      # created automatically on first run (not committed)
├── models/
│   ├── __init__.py
│   └── book.py                 # Book class + BookRepository (all SQL lives here)
├── templates/
│   └── index.html              # the single web page
├── static/
│   ├── css/style.css
│   └── js/script.js            # fetch() calls and page updates
├── tests/
│   └── test_api.py             # optional automated API tests
└── postman/
    └── BookManagement.postman_collection.json
```

## Database Structure

Table `books` (created automatically if it does not exist):

| Field | Type | Description |
|---|---|---|
| id | INTEGER (PK, auto) | Unique book ID |
| title | TEXT, required | Book title |
| author | TEXT, required | Author |
| category | TEXT, required | Category |
| publication_year | INTEGER, optional | Publication year |
| status | TEXT, required | `Available` (default) or `Issued` |

All SQL uses parameterized queries (`?` placeholders).

## API Endpoints

| Purpose | Method | Endpoint | Success code |
|---|---|---|---|
| Get all books | GET | `/api/books` | 200 |
| Filter by status | GET | `/api/books?status=Available` | 200 |
| Get one book | GET | `/api/books/<id>` | 200 |
| Create book | POST | `/api/books` | 201 |
| Update book | PUT | `/api/books/<id>` | 200 |
| Delete book | DELETE | `/api/books/<id>` | 200 |
| Search | GET | `/api/books/search?q=python` | 200 |

Notes:
- `PUT` accepts a full or partial JSON body; fields you leave out keep their old value.
- Search can be combined with a status filter: `/api/books/search?q=python&status=Issued`.
- Errors: `400` bad request, `404` not found, `405` wrong method, `500` server error. Format: `{"error": "Book not found"}`.

## Installation (Windows)

1. Install Python 3.9+ from python.org (tick **Add Python to PATH**).
2. Extract the project folder and open it in a terminal (or VS Code).

```bash
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
```

## Running

```bash
python app.py
```

Open <http://127.0.0.1:5000>. The SQLite database and `books` table are created automatically. Press `Ctrl + C` in the terminal to stop the server.

Optional: run the automated tests with `python -m unittest discover tests -v`.

## Postman Testing

Either create the requests below by hand, or import `postman/BookManagement.postman_collection.json` (Postman -> Import). Run the "Valid requests" folder in order, then the "Invalid requests" folder.

Test: `GET /api/books`, `GET /api/books/1`, `POST /api/books`, `PUT /api/books/1`, `DELETE /api/books/1`, `GET /api/books/search?q=python`, `GET /api/books?status=Available`, plus invalid input (empty title, bad year, bad status, missing body) and non-existent IDs.

For `POST` and `PUT`: Body -> raw -> JSON.

## Example Requests and Responses

**Create** - `POST /api/books`

```json
{
  "title": "Python Crash Course",
  "author": "Eric Matthes",
  "category": "Programming",
  "publication_year": 2023,
  "status": "Available"
}
```

Response `201 Created`:

```json
{
  "id": 1,
  "title": "Python Crash Course",
  "author": "Eric Matthes",
  "category": "Programming",
  "publication_year": 2023,
  "status": "Available"
}
```

**Search** - `GET /api/books/search?q=python` -> `200 OK`, a JSON list of matching books.

**Mark as issued** - `PUT /api/books/1` with `{"status": "Issued"}` -> `200 OK`, the updated book.

**Error** - `GET /api/books/999` -> `404 Not Found`

```json
{"error": "Book not found"}
```

**Validation error** - `POST /api/books` with an empty title -> `400 Bad Request`

```json
{"error": "Title is required"}
```

## Git/GitHub

```bash
git init
git add .
git commit -m "Initial commit"
git branch -M main
git remote add origin <YOUR_GITHUB_REPOSITORY_URL>
git push -u origin main
```

`.gitignore` already excludes `venv/`, `__pycache__/`, the local database and `.env`. Never commit passwords, tokens or API keys.

## Future Improvements

Login/registration, JWT authentication, book cover images, borrower/member management, issue/return dates, due-date reminders, fine calculation, pagination, PostgreSQL/MySQL, a categories table, deployment.
