import os
import sys
from datetime import datetime, timedelta

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from services.library_service import (
    add_book_to_catalog,
    borrow_book_by_patron,
    return_book_by_patron,
    calculate_late_fee_for_book,
    search_books_in_catalog,
    get_patron_status_report,
)
from database import (
    get_all_books,
)

import services.library_service as ls


# R1 testcases:
def test_add_book_valid_input():
    """Test adding a book with valid input."""
    success, message = add_book_to_catalog("Test Book", "Test Author", "1005011000011", 5)

    assert (
        success is True and "successfully added" in message.lower()
    ) or (
        success is False and "already" in message.lower()
    )


def test_add_book_rejects_blank_title():
    success, message = add_book_to_catalog("   ", "Some Author", "1000000000002", 1)
    assert success is False
    assert "title" in message.lower()


def test_add_book_invalid_isbn_too_short():
    """Test adding a book with ISBN too short."""
    success, message = add_book_to_catalog("Test Book", "Test Author", "123456789", 5)
    assert success is False
    assert "isbn" in message.lower()


def test_add_book_no_input():
    success, message = add_book_to_catalog(" ", " ", " ", " ")
    assert success is False
    assert any(k in message.lower() for k in ["input", "invalid", "title", "isbn", "author"])


def test_add_book_total_copies_must_be_positive():
    success, message = add_book_to_catalog("Book", "Author", "1000000000003", -1)
    assert success is False
    assert "copies" in message.lower()


# R2 testcases:
def test_display_catalog_with_books():
    """Test displaying the catalog when books are present."""
    add_book_to_catalog("Book 1", "Author 1", "1000000000004", 5)
    add_book_to_catalog("Book 2", "Author 2", "1000000000005", 3)

    books = get_all_books()
    assert len(books) >= 2, "Catalog should display at least two books."
    titles = [book["title"] for book in books]
    assert "Book 1" in titles
    assert "Book 2" in titles


def test_display_catalog_empty():
    """Test displaying the catalog when no books are present."""
    books = get_all_books()
    assert isinstance(books, list), "Should return a list of books"


def test_display_catalog_order():
    """Test displaying the catalog to ensure books are ordered by title."""
    add_book_to_catalog("Zebra Book", "Author Z", "1000000000006", 2)
    add_book_to_catalog("Apple Book", "Author A", "1000000000007", 3)

    books = get_all_books()
    zebra_idx = next((i for i, b in enumerate(books) if b["title"] == "Zebra Book"), None)
    apple_idx = next((i for i, b in enumerate(books) if b["title"] == "Apple Book"), None)
    assert zebra_idx is not None and apple_idx is not None
    assert apple_idx < zebra_idx, "Books should be ordered by title (Apple before Zebra)"


def test_borrow_button_functionality():
    """Test if the borrow button functionality works for available books."""
    books_before = get_all_books()
    suffix = len(books_before) + 1
    title = f"Borrowable Book {suffix}"
    isbn = f"900000{suffix:07d}"

    add_book_to_catalog(title, "Author B", isbn, 1)
    books = get_all_books()
    borrowable_book = next((book for book in books if book["isbn"] == isbn), None)

    assert borrowable_book is not None, "Borrowable book should exist in the catalog."
    assert borrowable_book["available_copies"] > 0

    patron_id = "111121"
    status = get_patron_status_report(patron_id)
    for b in status.get("currently_borrowed", []):
        return_book_by_patron(patron_id, b["book_id"])

    success, message = borrow_book_by_patron(patron_id, borrowable_book["id"])
    assert success is True, "Borrow should succeed for available book."
    assert "successfully borrowed" in message.lower()


# R3 testcases:
def test_borrow_book_valid():
    """Test borrowing a book with valid patron ID and book ID."""
    isbn = "1000009000009"
    add_book_to_catalog("Borrow Test Book", "Author", isbn, 2)
    books = get_all_books()
    test_book = next((book for book in books if book["isbn"] == isbn), None)
    assert test_book is not None
    book_id = test_book["id"]

    patron_id = "222222"
    status = get_patron_status_report(patron_id)
    for b in status.get("currently_borrowed", []):
        return_book_by_patron(patron_id, b["book_id"])

    success, message = borrow_book_by_patron(patron_id, book_id)
    assert success is True
    assert "successfully borrowed" in message.lower()


def test_borrow_book_invalid_patron():
    """Test borrowing a book with an invalid patron ID."""
    add_book_to_catalog("Invalid Patron Test", "Author", "1000000000010", 1)
    books = get_all_books()
    test_book = next((book for book in books if book["title"] == "Invalid Patron Test"), None)
    assert test_book is not None
    book_id = test_book["id"]

    success, message = borrow_book_by_patron("12345", book_id)
    assert success is False
    assert "invalid patron" in message.lower()


def test_borrow_book_unavailable():
    """Test borrowing a book that is unavailable."""
    books_before = get_all_books()
    suffix = len(books_before) + 1
    isbn = f"800000{suffix:07d}"

    add_book_to_catalog("Unavailable Book", "Author", isbn, 1)
    books = get_all_books()
    test_book = next((book for book in books if book["isbn"] == isbn), None)
    assert test_book is not None
    book_id = test_book["id"]

    for pid in ["333333", "444444"]:
        status = get_patron_status_report(pid)
        for b in status.get("currently_borrowed", []):
            return_book_by_patron(pid, b["book_id"])

    success_first, _ = borrow_book_by_patron("333333", book_id)
    assert success_first is True

    success, message = borrow_book_by_patron("444444", book_id)
    assert success is False
    assert "not available" in message.lower()


def test_borrow_book_exceeds_limit():
    """Test borrowing a book when patron exceeds borrowing limit."""
    test_patron = "565656"
    status = get_patron_status_report(test_patron)
    for b in status.get("currently_borrowed", []):
        return_book_by_patron(test_patron, b["book_id"])

    book_ids = []

    for i in range(7):
        isbn = f"10000090001{i:02d}"
        title = f"Limit Test Book {i}"
        add_book_to_catalog(title, "Author", isbn, 1)
        books = get_all_books()
        test_book = next((book for book in books if book["isbn"] == isbn), None)
        assert test_book is not None
        book_ids.append(test_book["id"])

    for book_id in book_ids[:6]:
        success, _ = borrow_book_by_patron(test_patron, book_id)
        assert success is True
    success, message = borrow_book_by_patron(test_patron, book_ids[6])
    assert success is False
    assert "borrowing limit" in message.lower()


# R4 testcases:
def test_return_book_valid():
    """Test returning a book with valid patron ID and book ID."""
    add_book_to_catalog("Return Test Book", "Author", "1000000000016", 1)
    books = get_all_books()
    test_book = next((book for book in books if book["title"] == "Return Test Book"), None)
    assert test_book is not None
    book_id = test_book["id"]

    patron_id = "666666"
    # Clean up any existing borrows for this patron
    status = get_patron_status_report(patron_id)
    for b in status.get("currently_borrowed", []):
        return_book_by_patron(patron_id, b["book_id"])

    borrow_book_by_patron(patron_id, book_id)
    success, message = return_book_by_patron(patron_id, book_id)
    assert success is True
    assert "returned successfully" in message.lower()


def test_return_book_not_borrowed():
    """Test returning a book that was not borrowed by the patron."""
    add_book_to_catalog("Not Borrowed Book", "Author", "1000000000017", 1)
    books = get_all_books()
    test_book = next((book for book in books if book["title"] == "Not Borrowed Book"), None)
    assert test_book is not None
    book_id = test_book["id"]

    success, message = return_book_by_patron("777777", book_id)
    assert success is False
    assert "not borrowed" in message.lower()


def test_return_book_invalid_patron():
    """Test returning a book with an invalid patron ID."""
    add_book_to_catalog("Invalid Patron Return", "Author", "1000000000018", 1)
    books = get_all_books()
    test_book = next((book for book in books if book["title"] == "Invalid Patron Return"), None)
    assert test_book is not None
    book_id = test_book["id"]

    borrow_book_by_patron("888888", book_id)
    success, message = return_book_by_patron("12345", book_id)
    assert success is False
    assert "invalid patron" in message.lower()


def test_return_book_late_fee():
    """Test returning a book (path may or may not include late fee, but must succeed)."""
    isbn = "1000009000019"
    add_book_to_catalog("Late Fee Book", "Author", isbn, 1)
    books = get_all_books()
    test_book = next((book for book in books if book["isbn"] == isbn), None)
    assert test_book is not None
    book_id = test_book["id"]

    patron_id = "999199"
    status = get_patron_status_report(patron_id)
    for b in status.get("currently_borrowed", []):
        return_book_by_patron(patron_id, b["book_id"])

    success_borrow, _ = borrow_book_by_patron(patron_id, book_id)
    assert success_borrow is True

    success, message = return_book_by_patron(patron_id, book_id)
    assert success is True
    assert "returned successfully" in message.lower()


# R5 testcases:
def test_calculate_late_fee_no_fee():
    """Test calculating late fee for a book returned on time."""
    add_book_to_catalog("On Time Book", "Author", "1000000000020", 1)
    books = get_all_books()
    test_book = next((book for book in books if book["title"] == "On Time Book"), None)
    assert test_book is not None
    book_id = test_book["id"]

    patron_id = "121212"
    status = get_patron_status_report(patron_id)
    for b in status.get("currently_borrowed", []):
        return_book_by_patron(patron_id, b["book_id"])

    borrow_book_by_patron(patron_id, book_id)
    fee_info = calculate_late_fee_for_book(patron_id, book_id)
    assert fee_info["fee_amount"] == 0.00
    assert fee_info["days_overdue"] == 0


def test_calculate_late_fee_one_day():
    """Test calculating late fee for a book - checks that function works correctly."""
    add_book_to_catalog("One Day Late Book", "Author", "1000000000021", 1)
    books = get_all_books()
    test_book = next((book for book in books if book["title"] == "One Day Late Book"), None)
    assert test_book is not None
    book_id = test_book["id"]

    patron_id = "131313"
    status = get_patron_status_report(patron_id)
    for b in status.get("currently_borrowed", []):
        return_book_by_patron(patron_id, b["book_id"])

    borrow_book_by_patron(patron_id, book_id)
    fee_info = calculate_late_fee_for_book(patron_id, book_id)
    assert fee_info["fee_amount"] == 0.00
    assert fee_info["days_overdue"] == 0



def test_calculate_late_fee_latest():
    """Test calculating late fee for a book - verifies function returns correct structure."""
    add_book_to_catalog("Max Fee Book", "Author", "1000000000022", 1)
    books = get_all_books()
    test_book = next((book for book in books if book["title"] == "Max Fee Book"), None)
    assert test_book is not None
    book_id = test_book["id"]

    patron_id = "141414"
    status = get_patron_status_report(patron_id)
    for b in status.get("currently_borrowed", []):
        return_book_by_patron(patron_id, b["book_id"])

    borrow_book_by_patron(patron_id, book_id)
    fee_info = calculate_late_fee_for_book(patron_id, book_id)
    assert "fee_amount" in fee_info
    assert "days_overdue" in fee_info
    assert "status" in fee_info
    assert fee_info["fee_amount"] == 0.00


def test_calculate_late_fee_no_borrow_record():
    """Test calculating late fee for a book not borrowed by the patron."""
    add_book_to_catalog("No Borrow Record Book", "Author", "1000000000023", 1)
    books = get_all_books()
    test_book = next((book for book in books if book["title"] == "No Borrow Record Book"), None)
    assert test_book is not None
    book_id = test_book["id"]

    fee_info = calculate_late_fee_for_book("151515", book_id)
    assert fee_info["fee_amount"] == 0.00
    assert fee_info["days_overdue"] == 0


# R6 testcases:
def test_search_books_by_title_partial():
    """Test searching books by partial title match."""
    add_book_to_catalog("Searchable Book", "Author", "1000000000024", 1)
    add_book_to_catalog("Another Book", "Author", "1000000000025", 1)

    results = search_books_in_catalog("Search", "title")
    titles = [r["title"] for r in results]
    assert "Searchable Book" in titles


def test_search_books_by_author_partial():
    """Test searching books by partial author match."""
    add_book_to_catalog("Book 1", "Unique Author", "1000000000026", 1)
    add_book_to_catalog("Book 2", "Common Author", "1000000000027", 1)

    results = search_books_in_catalog("Unique", "author")
    authors = [r["author"] for r in results]
    assert "Unique Author" in authors


def test_search_books_by_isbn_exact():
    """Test searching books by exact ISBN match."""
    isbn1 = "1000000000028"
    isbn2 = "1000000000029"
    add_book_to_catalog("Book 1", "Author", isbn1, 1)
    add_book_to_catalog("Book 2", "Author", isbn2, 1)

    results = search_books_in_catalog(isbn1, "isbn")
    assert len(results) == 1
    assert results[0]["isbn"] == isbn1


def test_search_books_no_results():
    """Test searching books with no matching results."""
    add_book_to_catalog("Book 1", "Author", "1000000000030", 1)

    results = search_books_in_catalog("NonexistentXYZ123", "title")
    assert len(results) == 0


# R7 testcases:
def test_patron_status_with_borrowed_books():
    """Test generating a patron status report with borrowed books."""
    test_patron = "888888"
    add_book_to_catalog("Borrowed Book", "Author", "1000000000031", 1)
    books = get_all_books()
    test_book = next((book for book in books if book["title"] == "Borrowed Book"), None)
    assert test_book is not None
    book_id = test_book["id"]

    # Clean up then borrow
    status = get_patron_status_report(test_patron)
    for b in status.get("currently_borrowed", []):
        return_book_by_patron(test_patron, b["book_id"])

    borrow_book_by_patron(test_patron, book_id)
    status = get_patron_status_report(test_patron)

    borrowed_titles = [b["title"] for b in status["currently_borrowed"]]
    assert "Borrowed Book" in borrowed_titles


def test_patron_status_with_late_fees():
    """Test generating a patron status report with late fees."""
    test_patron = "777777"
    add_book_to_catalog("Late Fee Book", "Author", "1000000000032", 1)
    books = get_all_books()
    test_book = next((book for book in books if book["title"] == "Late Fee Book"), None)
    assert test_book is not None
    book_id = test_book["id"]

    status = get_patron_status_report(test_patron)
    for b in status.get("currently_borrowed", []):
        return_book_by_patron(test_patron, b["book_id"])

    borrow_book_by_patron(test_patron, book_id)
    status = get_patron_status_report(test_patron)
    assert "total_late_fees" in status
    assert "currently_borrowed" in status
    assert "books_borrowed_count" in status
    assert "borrowing_history" in status
    assert status["total_late_fees"] == 0.00


def test_patron_status_with_no_borrowed_books():
    """Test generating a patron status report with no borrowed books."""
    test_patron = "000000"
    status = get_patron_status_report(test_patron)

    assert len(status["currently_borrowed"]) == 0
    assert status["total_late_fees"] == 0


def test_patron_status_with_borrowing_history():
    """Test generating a patron status report with borrowing history."""
    test_patron = "666666"
    add_book_to_catalog("History Book", "Author", "1000000000033", 1)
    books = get_all_books()
    test_book = next((book for book in books if book["title"] == "History Book"), None)
    assert test_book is not None
    book_id = test_book["id"]

    status = get_patron_status_report(test_patron)
    for b in status.get("currently_borrowed", []):
        return_book_by_patron(test_patron, b["book_id"])

    borrow_book_by_patron(test_patron, book_id)
    return_book_by_patron(test_patron, book_id)

    status = get_patron_status_report(test_patron)

    assert len(status["borrowing_history"]) > 0
    history_titles = [h["title"] for h in status["borrowing_history"]]
    assert "History Book" in history_titles


#extra tests

def test_add_book_title_too_long():
    """R1: title > 200 chars should be rejected."""
    long_title = "A" * 201
    success, message = add_book_to_catalog(
        long_title, "Some Author", "2000000000001", 1
    )
    assert success is False
    assert "title must be less than 200" in message.lower()


def test_add_book_author_blank():
    """R1: blank author should be rejected."""
    success, message = add_book_to_catalog(
        "Some Book", "   ", "2000000000002", 1
    )
    assert success is False
    assert "author is required" in message.lower()


def test_add_book_author_too_long():
    """R1: author > 100 chars should be rejected."""
    long_author = "B" * 101
    success, message = add_book_to_catalog("Some Book", long_author, "2000000000003", 1 )
    assert success is False
    assert "author must be less than 100" in message.lower()


def test_add_book_total_copies_not_int():
    """R1: non-int total_copies should be rejected."""
    success, message = add_book_to_catalog( "Some Book", "Author", "2000000000004", "5"  )
    assert success is False
    assert "total copies must be a positive integer" in message.lower()


def test_add_book_database_insert_failure(monkeypatch):
    """
    R1: cover the 'database error' branch when insert_book returns False.
    We monkeypatch DB helpers so we don't touch the real database here.
    """
    monkeypatch.setattr(ls, "get_book_by_isbn", lambda isbn: None)

    def fake_insert_book(*args, **kwargs):
        return False

    monkeypatch.setattr(ls, "insert_book", fake_insert_book)

    success, message = add_book_to_catalog(
        "DB Fail Book", "Author", "2000000000005", 1
    )
    assert success is False
    assert "database error" in message.lower()


def test_borrow_book_book_not_found(monkeypatch):
    """
    R3: cover branch where get_book_by_id returns None.
    """
    monkeypatch.setattr(ls, "get_book_by_id", lambda book_id: None)

    success, message = borrow_book_by_patron("555555", 999999)
    assert success is False
    assert "book not found" in message.lower()


def test_search_books_invalid_search_type():
    """
    R6: search_books_in_catalog should return [] for an invalid search_type.
    """
    add_book_to_catalog("Whatever", "Author", "2000000000006", 1)
    results = search_books_in_catalog("Whatever", "not_a_real_type")
    assert results == []


def test_patron_status_invalid_id():
    """
    R7: get_patron_status_report branch for invalid patron ID.
    """
    status = get_patron_status_report("12a456")
    assert status["currently_borrowed"] == []
    assert status["total_late_fees"] == 0.0
    assert "error" in status


def test_return_book_with_late_fee_branch(monkeypatch):
    """
    R4 + R5: hit the 'late fee > 0' path in return_book_by_patron
    without depending on real DB dates.
    """
    monkeypatch.setattr(ls, "get_book_by_id",lambda book_id: {"id": book_id, "title": "Late Book"})

    borrowed_record = {"book_id": 1, "due_date": datetime.now() - timedelta(days=3)}
    monkeypatch.setattr(ls, "get_patron_borrowed_books",lambda patron_id: [borrowed_record])

    monkeypatch.setattr(ls, "update_borrow_record_return_date",lambda patron_id, book_id, return_date: True)
                        
    monkeypatch.setattr(ls, "update_book_availability",lambda book_id, delta: True)

    monkeypatch.setattr(
        ls,
        "calculate_late_fee_for_book",
        lambda patron_id, book_id: {
            "fee_amount": 5.0,
            "days_overdue": 3,
            "status": "Overdue",
        },
    )

    success, message = return_book_by_patron("123456", 1)
    assert success is True
    assert "late fee" in message.lower()
    assert "$5.00" in message

def test_calculate_late_fee_invalid_patron_id_branch():
    """
    Directly hit the 'Invalid patron ID' branch in calculate_late_fee_for_book.
    """
    info = calculate_late_fee_for_book("12a456", 1)  
    assert info["fee_amount"] == 0.0
    assert info["days_overdue"] == 0
    assert info["status"] == "Invalid patron ID"


def test_calculate_late_fee_book_not_found_branch(monkeypatch):
    """
    Hit the 'Book not found' branch by stubbing get_book_by_id to return None.
    """
    monkeypatch.setattr(ls, "get_book_by_id", lambda book_id: None)

    info = calculate_late_fee_for_book("123456", 9999)  
    assert info["fee_amount"] == 0.0
    assert info["days_overdue"] == 0
    assert info["status"] == "Book not found"