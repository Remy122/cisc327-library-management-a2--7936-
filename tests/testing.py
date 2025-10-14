from library_service import (
    add_book_to_catalog,
    borrow_book_by_patron,
    return_book_by_patron,
    calculate_late_fee_for_book,
    search_books_in_catalog,
    get_patron_status_report
)
from database import (
    get_all_books
)

# R1 testcases:
def test_add_book_valid_input():
    """Test adding a book with valid input."""
    success, message = add_book_to_catalog("Test Book", "Test Author", "1234567890123", 5)

    assert success == True
    assert "successfully added" in message.lower()

def test_add_book_rejects_blank_title():
    success, message = add_book_to_catalog("   ", "Some Author", "1145618123222", 1)
    assert success == False
    assert "title" in message.lower()

def test_add_book_invalid_isbn_too_short():
    """Test adding a book with ISBN too short."""
    success, message = add_book_to_catalog("Test Book", "Test Author", "123456789", 5)
    assert success == False
    assert "isbn" in message.lower()

def test_add_book_no_input():
    success, message = add_book_to_catalog(" ", " ", " ", " ")
    assert success == False
    
    assert any(k in message.lower() for k in ["input", "invalid", "title", "isbn", "author"])

def test_add_book_total_copies_must_be_positive():
    success, message = add_book_to_catalog("Book", "Author", "2224561890122", -1)
    assert success == False
    assert "copies" in message.lower()  

# R2 testcases:
def test_display_catalog_with_books():
    """Test displaying the catalog when books are present."""
    add_book_to_catalog("Book 1", "Author 1", "1234567890123", 5)
    add_book_to_catalog("Book 2", "Author 2", "9876543210987", 3)

    books = get_all_books()
    assert len(books) >= 2, "Catalog should display at least two books."
    assert books[-2]['title'] == "Book 1"
    assert books[-1]['title'] == "Book 2"

def test_display_catalog_empty():
    """Test displaying the catalog when no books are present."""
    books = get_all_books()
    assert len(books) == 0, "Catalog should be empty when no books are added."

def test_display_catalog_order():
    """Test displaying the catalog to ensure books are ordered by title."""
    add_book_to_catalog("Zebra Book", "Author Z", "9999999999999", 2)
    add_book_to_catalog("Apple Book", "Author A", "1111111111111", 3)

    books = get_all_books()
    assert books[0]['title'] == "Apple Book"
    assert books[1]['title'] == "Zebra Book"

def test_borrow_button_functionality():
    """Test if the borrow button functionality works for available books."""
    add_book_to_catalog("Borrowable Book", "Author B", "5555555555555", 1)
    books = get_all_books()
    borrowable_book = next((book for book in books if book['title'] == "Borrowable Book"), None)

    assert borrowable_book is not None, "Borrowable Book should exist in the catalog."
    assert borrowable_book['available_copies'] > 0

    success, message = borrow_book_by_patron("654321", borrowable_book['id'])
    assert success is True, "Borrow works"
    assert "successfully borrowed" in message.lower()

# R3 testcases:
def test_borrow_book_valid():
    """Test borrowing a book with valid patron ID and book ID."""
    add_book_to_catalog("Borrow Test Book", "Author", "1234567890123", 2)
    books = get_all_books()
    book_id = books[-1]['id']

    success, message = borrow_book_by_patron("654321", book_id)
    assert success is True
    assert "successfully borrowed" in message.lower()

def test_borrow_book_invalid_patron():
    """Test borrowing a book with an invalid patron ID."""
    add_book_to_catalog("Invalid Patron Test", "Author", "9876543210987", 1)
    books = get_all_books()
    book_id = books[-1]['id']

    success, message = borrow_book_by_patron("12345", book_id)  # Invalid patron ID (not 6 digits)
    assert success is False
    assert "invalid patron" in message.lower()

def test_borrow_book_unavailable():
    """Test borrowing a book that is unavailable."""
    add_book_to_catalog("Unavailable Book", "Author", "1111111111111", 1)
    books = get_all_books()
    book_id = books[-1]['id']

    borrow_book_by_patron("654321", book_id)  # First borrow
    success, message = borrow_book_by_patron("123456", book_id)  # Attempt second borrow
    assert success is False
    assert "not available" in message.lower()

def test_borrow_book_exceeds_limit():
    """Test borrowing a book when patron exceeds borrowing limit."""
    for i in range(5):
        add_book_to_catalog(f"Limit Test Book {i}", "Author", f"222222222222{i}", 1)
    
    books = get_all_books()
    book_ids = [book['id'] for book in books[-5:]]  # Get last 5 books

    for book_id in book_ids:
        borrow_book_by_patron("654321", book_id)

    add_book_to_catalog("Limit Test Book 6", "Author", "2222222222226", 1)
    books = get_all_books()
    new_book_id = books[-1]['id']
    
    success, message = borrow_book_by_patron("654321", new_book_id)  # Attempt 6th borrow
    assert success is False
    assert "borrowing limit" in message.lower()

# R4 testcases:
def test_return_book_valid():
    """Test returning a book with valid patron ID and book ID."""
    add_book_to_catalog("Return Test Book", "Author", "3333333333333", 1)
    books = get_all_books()
    book_id = books[-1]['id']

    borrow_book_by_patron("654321", book_id)
    success, message = return_book_by_patron("654321", book_id)
    assert success is True
    assert "successfully returned" in message.lower()

def test_return_book_not_borrowed():
    """Test returning a book that was not borrowed by the patron."""
    add_book_to_catalog("Not Borrowed Book", "Author", "4444444444444", 1)
    books = get_all_books()
    book_id = books[-1]['id']

    success, message = return_book_by_patron("654321", book_id)
    assert success is False
    assert "not borrowed" in message.lower()

def test_return_book_invalid_patron():
    """Test returning a book with an invalid patron ID."""
    add_book_to_catalog("Invalid Patron Return", "Author", "5555555555555", 1)
    books = get_all_books()
    book_id = books[-1]['id']

    borrow_book_by_patron("654321", book_id)
    success, message = return_book_by_patron("12345", book_id)  # Invalid patron ID
    assert success is False
    assert "invalid patron" in message.lower()

def test_return_book_late_fee():
    """Test returning a book with a late fee."""
    add_book_to_catalog("Late Fee Book", "Author", "6666666666666", 1)
    books = get_all_books()
    book_id = books[-1]['id']

    borrow_book_by_patron("654321", book_id)
 
    success, message = return_book_by_patron("654321", book_id)
    assert success is True
    assert "late fee" in message.lower()

# R5 testcases:
def test_calculate_late_fee_no_fee():
    """Test calculating late fee for a book returned on time."""
    add_book_to_catalog("On Time Book", "Author", "7777777777777", 1)
    books = get_all_books()
    book_id = books[-1]['id']

    borrow_book_by_patron("654321", book_id)
    success = return_book_by_patron("654321", book_id)
    assert success is True

    fee_info = calculate_late_fee_for_book("654321", book_id)
    assert fee_info['fee_amount'] == 0.00
    assert fee_info['days_overdue'] == 0

def test_calculate_late_fee_one_day():
    """Test calculating late fee for a book returned 1 day late."""
    add_book_to_catalog("One Day Late Book", "Author", "8888888888888", 1)
    books = get_all_books()
    book_id = books[-1]['id']

    borrow_book_by_patron("654321", book_id)

    fee_info = calculate_late_fee_for_book("654321", book_id)
    assert fee_info['fee_amount'] > 0
    assert fee_info['days_overdue'] == 1

def test_calculate_late_fee_latest():
    """Test calculating late fee for a book with maximum fee."""
    add_book_to_catalog("Max Fee Book", "Author", "9999999999999", 1)
    books = get_all_books()
    book_id = books[-1]['id']

    borrow_book_by_patron("654321", book_id)
    fee_info = calculate_late_fee_for_book("654321", book_id)
    assert fee_info['fee_amount'] == 15.00  

def test_calculate_late_fee_no_borrow_record():
    """Test calculating late fee for a book not borrowed by the patron."""
    add_book_to_catalog("No Borrow Record Book", "Author", "1010101010101", 1)
    books = get_all_books()
    book_id = books[-1]['id']

    fee_info = calculate_late_fee_for_book("654321", book_id)
    assert fee_info['fee_amount'] == 0.00
    assert fee_info['days_overdue'] == 0

# R6 testcases:
def test_search_books_by_title_partial():
    """Test searching books by partial title match."""
    add_book_to_catalog("Searchable Book", "Author", "1111111111111", 1)
    add_book_to_catalog("Another Book", "Author", "2222222222222", 1)

    results = search_books_in_catalog("Search", "title")
    assert len(results) == 1
    assert results[0]['title'] == "Searchable Book"

def test_search_books_by_author_partial():
    """Test searching books by partial author match."""
    add_book_to_catalog("Book 1", "Unique Author", "3333333333333", 1)
    add_book_to_catalog("Book 2", "Common Author", "4444444444444", 1)

    results = search_books_in_catalog("Unique", "author")
    assert len(results) == 1
    assert results[0]['author'] == "Unique Author"

def test_search_books_by_isbn_exact():
    """Test searching books by exact ISBN match."""
    add_book_to_catalog("Book 1", "Author", "5555555555555", 1)
    add_book_to_catalog("Book 2", "Author", "6666666666666", 1)

    results = search_books_in_catalog("5555555555555", "isbn")
    assert len(results) == 1
    assert results[0]['isbn'] == "5555555555555"

def test_search_books_no_results():
    """Test searching books with no matching results."""
    add_book_to_catalog("Book 1", "Author", "7777777777777", 1)

    results = search_books_in_catalog("Nonexistent", "title")
    assert len(results) == 0


# R7 testcases:
def test_patron_status_with_borrowed_books():
    """Test generating a patron status report with borrowed books."""
    add_book_to_catalog("Borrowed Book", "Author", "1111111111111", 1)
    books = get_all_books()
    book_id = books[-1]['id']

    borrow_book_by_patron("654321", book_id)
    status = get_patron_status_report("654321")

    assert len(status['currently_borrowed']) == 1
    assert status['currently_borrowed'][0]['title'] == "Borrowed Book"

def test_patron_status_with_late_fees():
    """Test generating a patron status report with late fees."""
    add_book_to_catalog("Late Fee Book", "Author", "2222222222222", 1)
    books = get_all_books()
    book_id = books[-1]['id']

    borrow_book_by_patron("654321", book_id)
    status = get_patron_status_report("654321")

    assert status['total_late_fees'] > 0

def test_patron_status_with_no_borrowed_books():
    """Test generating a patron status report with no borrowed books."""
    status = get_patron_status_report("654321")

    assert len(status['currently_borrowed']) == 0
    assert status['total_late_fees'] == 0

def test_patron_status_with_borrowing_history():
    """Test generating a patron status report with borrowing history."""
    add_book_to_catalog("History Book", "Author", "3333333333333", 1)
    books = get_all_books()
    book_id = books[-1]['id']

    borrow_book_by_patron("654321", book_id)
    return_book_by_patron("654321", book_id)
    status = get_patron_status_report("654321")

    assert len(status['borrowing_history']) > 0
    assert status['borrowing_history'][0]['title'] == "History Book"

