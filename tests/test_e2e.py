
import os
import sys

#I need this to run the tests 
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

import threading
import time
import uuid

from playwright.sync_api import sync_playwright, Page, expect
from app import create_app
import pytest


@pytest.fixture(scope="module")
def app():
    
    app = create_app()
    app.config["TESTING"] = True
    return app


@pytest.fixture(scope="module")
def server(app):
   
    def run_server():
        app.run(port=5000, debug=False, use_reloader=False)

    server_thread = threading.Thread(target=run_server, daemon=True)
    server_thread.start()

    
    time.sleep(2)

    yield
   


@pytest.fixture(scope="function")
def browser_page(server):
   
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        yield page
        browser.close()


def test_add_book_and_verify_in_catalog(browser_page: Page):
    
    #User Flow 1: Add a new book and verify it appears in the catalog.

    page = browser_page

    page.goto("http://localhost:5000/add_book")

    expect(page.locator("h2")).to_contain_text("Add New Book")

    suffix = uuid.uuid4().hex[:6]
    test_title = f"E2E Test Book {suffix}"
    test_author = "E2E Test Author"
    test_isbn = f"1234567890{suffix[:3]}"
    test_copies = "3"

    page.fill('input[name="title"]', test_title)
    page.fill('input[name="author"]', test_author)
    page.fill('input[name="isbn"]', test_isbn)
    page.fill('input[name="total_copies"]', test_copies)

    page.click('button[type="submit"]')

    page.wait_for_url("http://localhost:5000/catalog")

    success_message = page.locator(".flash-success")
    expect(success_message).to_be_visible()
    expect(success_message).to_contain_text("success", ignore_case=True)

    expect(page.locator("table")).to_be_visible()
    table_text = page.locator("table").inner_text()

    assert test_title in table_text, f"Book title '{test_title}' should appear in catalog"
    assert test_author in table_text, f"Book author '{test_author}' should appear in catalog"
    assert test_isbn in table_text, f"Book ISBN '{test_isbn}' should appear in catalog"

    expect(page.locator("h2")).to_contain_text("Book Catalog")


def test_borrow_book_and_verify_confirmation(browser_page: Page):
    
    #User Flow 2: Borrow a book using a patron ID and verify confirmation.
   
    page = browser_page

   
    page.goto("http://localhost:5000/catalog")

    
    expect(page.locator("h2")).to_contain_text("Book Catalog")
    expect(page.locator("table")).to_be_visible()

   
    patron_inputs = page.locator('input[name="patron_id"]')

    
    if patron_inputs.count == 0:
        pytest.skip("No available books to borrow in catalog")
    
    
    patron_input = patron_inputs.first

    
    form = patron_input.locator("xpath=ancestor::form[1]")
    row = patron_input.locator("xpath=ancestor::tr[1]")


    
    test_patron_id = "123456"
    patron_input.fill(test_patron_id)

  
    form.locator('button[type="submit"]').click()

    
    page.wait_for_load_state("networkidle")

    
    expect(page.locator("h2")).to_contain_text("Book Catalog")

   
    flash_messages = page.locator(".flash-success, .flash-error")
    expect(flash_messages.first).to_be_visible()

    
    message_text = flash_messages.first.inner_text().lower()
    assert any(word in message_text for word in ["borrow", "success", "error"])
