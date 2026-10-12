/* Book Management - frontend logic.
   Talks to the Flask REST API using fetch() and JSON. */

const API_URL = "/api/books";

// ---------- Page elements ----------
const form = document.getElementById("bookForm");
const formTitle = document.getElementById("formTitle");
const formError = document.getElementById("formError");
const submitBtn = document.getElementById("submitBtn");
const cancelBtn = document.getElementById("cancelBtn");
const titleInput = document.getElementById("title");
const authorInput = document.getElementById("author");
const categoryInput = document.getElementById("category");
const yearInput = document.getElementById("year");
const statusInput = document.getElementById("status");

const searchInput = document.getElementById("searchInput");
const filterButtons = document.querySelectorAll(".filter-btn");
const resultCount = document.getElementById("resultCount");
const bookList = document.getElementById("bookList");
const emptyState = document.getElementById("emptyState");
const emptyTitle = document.getElementById("emptyTitle");
const emptyText = document.getElementById("emptyText");

const deleteDialog = document.getElementById("deleteDialog");
const deleteText = document.getElementById("deleteText");
const deleteCancel = document.getElementById("deleteCancel");
const deleteConfirm = document.getElementById("deleteConfirm");
const toast = document.getElementById("toast");

// ---------- State ----------
let currentStatus = "All";   // selected filter
let editingId = null;        // id of the book being edited (null = adding)
let pendingDelete = null;    // book waiting for delete confirmation
let latestRequest = 0;       // ignores out-of-date responses
let searchTimer = null;
let toastTimer = null;

yearInput.max = new Date().getFullYear() + 1;

// ---------- API helper ----------
async function apiRequest(url, options = {}) {
  let response;
  try {
    response = await fetch(url, {
      headers: { "Content-Type": "application/json" },
      ...options,
    });
  } catch (networkError) {
    throw new Error("Cannot reach the server. Is Flask running?");
  }

  let data = null;
  try {
    data = await response.json();
  } catch (parseError) {
    // response had no JSON body
  }

  if (!response.ok) {
    throw new Error((data && data.error) || `Request failed (status ${response.status})`);
  }
  return data;
}

// ---------- Messages ----------
function showToast(message, isError = false) {
  toast.textContent = message;
  toast.classList.toggle("is-error", isError);
  toast.hidden = false;
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => { toast.hidden = true; }, 3500);
}

function showFormError(message) {
  formError.textContent = message;
  formError.hidden = !message;
}

// ---------- Loading and showing books ----------
async function loadBooks() {
  const requestId = ++latestRequest;
  const query = searchInput.value.trim();

  const params = new URLSearchParams();
  if (currentStatus !== "All") params.set("status", currentStatus);

  let url = API_URL;
  if (query) {
    params.set("q", query);
    url = `${API_URL}/search`;
  }
  const queryString = params.toString();
  if (queryString) url += `?${queryString}`;

  try {
    const books = await apiRequest(url);
    if (requestId !== latestRequest) return; // a newer request replaced this one
    renderBooks(books, Boolean(query) || currentStatus !== "All");
  } catch (error) {
    if (requestId !== latestRequest) return;
    showToast(error.message, true);
  }
}

// Gives each category its own spine colour (same category = same colour).
function spineColor(category) {
  let hash = 0;
  for (const char of category.toLowerCase()) {
    hash = (hash * 31 + char.charCodeAt(0)) % 360;
  }
  return `hsl(${hash}, 45%, 38%)`;
}

function renderBooks(books, isFiltered) {
  bookList.replaceChildren();
  resultCount.textContent = `${books.length} ${books.length === 1 ? "book" : "books"}`;

  emptyState.hidden = books.length > 0;
  if (books.length === 0) {
    if (isFiltered) {
      emptyTitle.textContent = "No matching books";
      emptyText.textContent = "Try a different search or choose another status.";
    } else {
      emptyTitle.textContent = "Your shelf is empty";
      emptyText.textContent = "Add your first book using the form.";
    }
  }

  books.forEach((book) => bookList.appendChild(createBookCard(book)));
}

// Elements are built with textContent (not innerHTML) so book text can never run as HTML.
function createElement(tag, className, text) {
  const element = document.createElement(tag);
  if (className) element.className = className;
  if (text !== undefined) element.textContent = text;
  return element;
}

function createBookCard(book) {
  const card = createElement("li", "book-card");
  card.style.setProperty("--spine", spineColor(book.category));
  card.appendChild(createElement("div", "book-spine"));

  const body = createElement("div", "book-body");

  const top = createElement("div", "book-top");
  const heading = createElement("div");
  heading.appendChild(createElement("h3", "book-title", book.title));
  heading.appendChild(createElement("p", "book-author", book.author));
  top.appendChild(heading);
  const badgeClass = book.status === "Available" ? "badge-available" : "badge-issued";
  top.appendChild(createElement("span", `badge ${badgeClass}`, book.status));
  body.appendChild(top);

  const meta = createElement("ul", "book-meta");
  meta.appendChild(createElement("li", "", book.category));
  meta.appendChild(createElement("li", "", book.publication_year ? String(book.publication_year) : "Year not set"));
  body.appendChild(meta);

  const actions = createElement("div", "book-actions");

  const editBtn = createElement("button", "btn btn-ghost btn-small", "Edit");
  editBtn.type = "button";
  editBtn.setAttribute("aria-label", `Edit ${book.title}`);
  editBtn.addEventListener("click", () => startEdit(book.id));
  actions.appendChild(editBtn);

  const isAvailable = book.status === "Available";
  const statusBtn = createElement("button", "btn btn-ghost btn-small", isAvailable ? "Issue" : "Return");
  statusBtn.type = "button";
  statusBtn.setAttribute("aria-label", `${isAvailable ? "Issue" : "Return"} ${book.title}`);
  statusBtn.addEventListener("click", () => changeStatus(book, isAvailable ? "Issued" : "Available"));
  actions.appendChild(statusBtn);

  const deleteBtn = createElement("button", "btn btn-danger-outline btn-small", "Delete");
  deleteBtn.type = "button";
  deleteBtn.setAttribute("aria-label", `Delete ${book.title}`);
  deleteBtn.addEventListener("click", () => askDelete(book));
  actions.appendChild(deleteBtn);

  body.appendChild(actions);
  card.appendChild(body);
  return card;
}

// ---------- Add / Edit ----------
function resetForm() {
  form.reset();
  editingId = null;
  formTitle.textContent = "Add a new book";
  submitBtn.textContent = "Add book";
  cancelBtn.hidden = true;
  showFormError("");
}

async function startEdit(id) {
  try {
    const book = await apiRequest(`${API_URL}/${id}`);   // GET one book
    editingId = book.id;
    titleInput.value = book.title;
    authorInput.value = book.author;
    categoryInput.value = book.category;
    yearInput.value = book.publication_year ?? "";
    statusInput.value = book.status;

    formTitle.textContent = "Edit book";
    submitBtn.textContent = "Save changes";
    cancelBtn.hidden = false;
    showFormError("");
    form.scrollIntoView({ behavior: "smooth", block: "center" });
    titleInput.focus();
  } catch (error) {
    showToast(error.message, true);
    loadBooks(); // the book may have been deleted elsewhere
  }
}

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  showFormError("");

  const payload = {
    title: titleInput.value.trim(),
    author: authorInput.value.trim(),
    category: categoryInput.value.trim(),
    publication_year: yearInput.value === "" ? null : Number(yearInput.value),
    status: statusInput.value,
  };

  const isEditing = editingId !== null;
  submitBtn.disabled = true;
  try {
    if (isEditing) {
      await apiRequest(`${API_URL}/${editingId}`, { method: "PUT", body: JSON.stringify(payload) });
    } else {
      await apiRequest(API_URL, { method: "POST", body: JSON.stringify(payload) });
    }
    resetForm();
    showToast(isEditing ? "Changes saved" : "Book added");
    loadBooks();
  } catch (error) {
    showFormError(error.message);
  } finally {
    submitBtn.disabled = false;
  }
});

cancelBtn.addEventListener("click", resetForm);

// ---------- Issue / Return ----------
async function changeStatus(book, newStatus) {
  try {
    await apiRequest(`${API_URL}/${book.id}`, { method: "PUT", body: JSON.stringify({ status: newStatus }) });
    showToast(newStatus === "Issued" ? "Book issued" : "Book returned");
    loadBooks();
  } catch (error) {
    showToast(error.message, true);
    loadBooks();
  }
}

// ---------- Delete with confirmation ----------
function askDelete(book) {
  pendingDelete = book;
  deleteText.textContent = `"${book.title}" by ${book.author} will be removed permanently.`;
  if (typeof deleteDialog.showModal === "function") {
    deleteDialog.showModal();
  } else if (window.confirm(`Delete "${book.title}"?`)) {
    performDelete();
  }
}

async function performDelete() {
  const book = pendingDelete;
  pendingDelete = null;
  if (!book) return;
  try {
    await apiRequest(`${API_URL}/${book.id}`, { method: "DELETE" });
    if (editingId === book.id) resetForm();
    showToast("Book deleted");
  } catch (error) {
    showToast(error.message, true);
  }
  loadBooks();
}

deleteCancel.addEventListener("click", () => {
  pendingDelete = null;
  deleteDialog.close();
});
deleteConfirm.addEventListener("click", () => {
  deleteDialog.close();
  performDelete();
});
deleteDialog.addEventListener("cancel", () => { pendingDelete = null; }); // Esc key

// ---------- Search and filter ----------
searchInput.addEventListener("input", () => {
  clearTimeout(searchTimer);
  searchTimer = setTimeout(loadBooks, 250); // wait until the user pauses typing
});

filterButtons.forEach((button) => {
  button.addEventListener("click", () => {
    currentStatus = button.dataset.status;
    filterButtons.forEach((other) => {
      const active = other === button;
      other.classList.toggle("is-active", active);
      other.setAttribute("aria-pressed", String(active));
    });
    loadBooks();
  });
});

// ---------- Start ----------
loadBooks();
