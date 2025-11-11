"""
Assignment 3 - Task 2.1: Stubbing and Mocking Tests
Test file for payment gateway functions using mocking and stubbing techniques.

This file tests:
- pay_late_fees() function with mocked PaymentGateway
- refund_late_fee_payment() function with mocked PaymentGateway

Stubbing: Used for database functions (calculate_late_fee_for_book, get_book_by_id)
Mocking: Used for PaymentGateway methods (process_payment, refund_payment)
"""

import pytest
from unittest.mock import Mock
from services.library_service import pay_late_fees, refund_late_fee_payment
from services.payment_service import PaymentGateway


# Tests for pay_late_fees() function


def test_pay_late_fees_successful_payment(mocker):
    """
    Test successful payment processing when patron has outstanding late fees.
    
    Stubs Used:
    - calculate_late_fee_for_book: Returns $5.00 fee (3 days overdue)
    - get_book_by_id: Returns book details
    
    Mocks Used:
    - PaymentGateway.process_payment: Returns successful transaction
    
    Verification:
    - Payment gateway called once with correct parameters
    - Returns success status and transaction ID
    """
    # Stub database functions to return fake data
    mocker.patch(
        'services.library_service.calculate_late_fee_for_book',
        return_value={
            'fee_amount': 5.00,
            'days_overdue': 3,
            'status': 'Overdue'
        }
    )
    
    mocker.patch(
        'services.library_service.get_book_by_id',
        return_value={
            'id': 1,
            'title': 'Test Book',
            'author': 'Test Author',
            'isbn': '1234567890123'
        }
    )
    
    # Mock the payment gateway
    mock_gateway = Mock(spec=PaymentGateway)
    mock_gateway.process_payment.return_value = (True, "txn_123456", "Payment processed successfully")
    
    # Execute the function
    success, message, transaction_id = pay_late_fees("123456", 1, mock_gateway)
    
    # Assertions
    assert success is True
    assert transaction_id == "txn_123456"
    assert "Payment successful" in message
    
    # Verify mock was called exactly once with correct parameters
    mock_gateway.process_payment.assert_called_once_with(
        patron_id="123456",
        amount=5.00,
        description="Late fees for 'Test Book'"
    )


def test_pay_late_fees_payment_declined(mocker):
    """
    Test payment processing when payment gateway declines the transaction.
    
    Stubs Used:
    - calculate_late_fee_for_book: Returns $7.50 fee
    - get_book_by_id: Returns book details
    
    Mocks Used:
    - PaymentGateway.process_payment: Returns declined status
    
    Verification:
    - Payment gateway called once
    - Returns failure status with appropriate message
    """
    # Stub database functions
    mocker.patch(
        'services.library_service.calculate_late_fee_for_book',
        return_value={
            'fee_amount': 7.50,
            'days_overdue': 5,
            'status': 'Overdue'
        }
    )
    
    mocker.patch(
        'services.library_service.get_book_by_id',
        return_value={
            'id': 2,
            'title': 'Another Book',
            'author': 'Another Author',
            'isbn': '9876543210987'
        }
    )
    
    # Mock payment gateway to return declined status
    mock_gateway = Mock(spec=PaymentGateway)
    mock_gateway.process_payment.return_value = (False, None, "Insufficient funds")
    
    # Execute the function
    success, message, transaction_id = pay_late_fees("654321", 2, mock_gateway)
    
    # Assertions
    assert success is False
    assert transaction_id is None
    assert "Payment failed" in message
    assert "Insufficient funds" in message
    
    # Verify mock was called
    mock_gateway.process_payment.assert_called_once()


def test_pay_late_fees_invalid_patron_id_mock_not_called(mocker):
    """
    Test that payment gateway is NOT called when patron ID is invalid.
    
    Stubs Used: None (validation happens before database calls)
    
    Mocks Used:
    - PaymentGateway.process_payment: Should NOT be called
    
    Verification:
    - Mock is never called (assert_not_called)
    - Returns failure status immediately
    """
    # Mock payment gateway
    mock_gateway = Mock(spec=PaymentGateway)
    
    # Execute with invalid patron ID (not 6 digits)
    success, message, transaction_id = pay_late_fees("123", 1, mock_gateway)
    
    # Assertions
    assert success is False
    assert "Invalid patron ID" in message
    assert transaction_id is None
    
    # CRITICAL: Verify payment gateway was NEVER called
    mock_gateway.process_payment.assert_not_called()


def test_pay_late_fees_invalid_patron_id_with_letters(mocker):
    """
    Test invalid patron ID with non-numeric characters.
    
    Verification:
    - Payment gateway not called for invalid input
    """
    mock_gateway = Mock(spec=PaymentGateway)
    
    # Execute with patron ID containing letters
    success, message, transaction_id = pay_late_fees("12a456", 1, mock_gateway)
    
    # Assertions
    assert success is False
    assert "Invalid patron ID" in message
    assert transaction_id is None
    
    # Verify no payment attempt was made
    mock_gateway.process_payment.assert_not_called()


def test_pay_late_fees_zero_late_fees_mock_not_called(mocker):
    """
    Test that payment gateway is NOT called when there are no late fees.
    
    Stubs Used:
    - calculate_late_fee_for_book: Returns $0.00 (no fees)
    
    Mocks Used:
    - PaymentGateway.process_payment: Should NOT be called
    
    Verification:
    - Mock is never called when fee is zero
    - Returns appropriate message about no fees
    """
    # Stub to return zero late fees
    mocker.patch(
        'services.library_service.calculate_late_fee_for_book',
        return_value={
            'fee_amount': 0.00,
            'days_overdue': 0,
            'status': 'Not overdue'
        }
    )
    
    # Mock payment gateway
    mock_gateway = Mock(spec=PaymentGateway)
    
    # Execute the function
    success, message, transaction_id = pay_late_fees("123456", 1, mock_gateway)
    
    # Assertions
    assert success is False
    assert "No late fees" in message
    assert transaction_id is None
    
    # CRITICAL: Verify payment gateway was NEVER called
    mock_gateway.process_payment.assert_not_called()


def test_pay_late_fees_network_error_exception_handling(mocker):
    """
    Test exception handling when payment gateway raises network error.
    
    Stubs Used:
    - calculate_late_fee_for_book: Returns valid fee
    - get_book_by_id: Returns book details
    
    Mocks Used:
    - PaymentGateway.process_payment: Raises Exception
    
    Verification:
    - Exception is caught and handled gracefully
    - Returns failure status with error message
    """
    # Stub database functions
    mocker.patch(
        'services.library_service.calculate_late_fee_for_book',
        return_value={
            'fee_amount': 10.00,
            'days_overdue': 8,
            'status': 'Overdue'
        }
    )
    
    mocker.patch(
        'services.library_service.get_book_by_id',
        return_value={
            'id': 3,
            'title': 'Network Test Book',
            'author': 'Test Author',
            'isbn': '1111111111111'
        }
    )
    
    # Mock payment gateway to raise exception
    mock_gateway = Mock(spec=PaymentGateway)
    mock_gateway.process_payment.side_effect = Exception("Network timeout")
    
    # Execute the function
    success, message, transaction_id = pay_late_fees("123456", 3, mock_gateway)
    
    # Assertions
    assert success is False
    assert "error" in message.lower()
    assert "Network timeout" in message
    assert transaction_id is None
    
    # Verify the mock was called (exception occurred during call)
    mock_gateway.process_payment.assert_called_once()


def test_pay_late_fees_book_not_found(mocker):
    """
    Test handling when book ID doesn't exist in database.
    
    Stubs Used:
    - calculate_late_fee_for_book: Returns valid fee
    - get_book_by_id: Returns None (book not found)
    
    Mocks Used:
    - PaymentGateway.process_payment: Should NOT be called
    
    Verification:
    - Payment not attempted when book doesn't exist
    """
    # Stub to return valid fee
    mocker.patch(
        'services.library_service.calculate_late_fee_for_book',
        return_value={
            'fee_amount': 5.00,
            'days_overdue': 3,
            'status': 'Overdue'
        }
    )
    
    # Stub to return None (book not found)
    mocker.patch(
        'services.library_service.get_book_by_id',
        return_value=None
    )
    
    # Mock payment gateway
    mock_gateway = Mock(spec=PaymentGateway)
    
    # Execute the function
    success, message, transaction_id = pay_late_fees("123456", 999, mock_gateway)
    
    # Assertions
    assert success is False
    assert "Book not found" in message
    assert transaction_id is None
    
    # Verify payment gateway was not called
    mock_gateway.process_payment.assert_not_called()


def test_pay_late_fees_maximum_fee_amount(mocker):
    """
    Test payment processing for maximum late fee amount ($15.00).
    
    Stubs Used:
    - calculate_late_fee_for_book: Returns maximum fee
    - get_book_by_id: Returns book details
    
    Mocks Used:
    - PaymentGateway.process_payment: Processes maximum amount
    
    Verification:
    - Payment gateway called with $15.00 (maximum fee)
    """
    # Stub to return maximum late fee
    mocker.patch(
        'services.library_service.calculate_late_fee_for_book',
        return_value={
            'fee_amount': 15.00,
            'days_overdue': 30,
            'status': 'Overdue'
        }
    )
    
    mocker.patch(
        'services.library_service.get_book_by_id',
        return_value={
            'id': 4,
            'title': 'Maximum Fee Book',
            'author': 'Test Author',
            'isbn': '2222222222222'
        }
    )
    
    # Mock payment gateway
    mock_gateway = Mock(spec=PaymentGateway)
    mock_gateway.process_payment.return_value = (True, "txn_max_fee", "Success")
    
    # Execute the function
    success, message, transaction_id = pay_late_fees("123456", 4, mock_gateway)
    
    # Assertions
    assert success is True
    assert transaction_id == "txn_max_fee"
    
    # Verify payment gateway called with maximum amount
    mock_gateway.process_payment.assert_called_once_with(
        patron_id="123456",
        amount=15.00,
        description="Late fees for 'Maximum Fee Book'"
    )


# ============================================================================
# Tests for refund_late_fee_payment() function
# ============================================================================

def test_refund_late_fee_successful(mocker):
    """
    Test successful refund processing for valid transaction.
    
    Stubs Used: None
    
    Mocks Used:
    - PaymentGateway.refund_payment: Returns successful refund
    
    Verification:
    - Refund gateway called once with correct parameters
    - Returns success status and message
    """
    # Mock payment gateway
    mock_gateway = Mock(spec=PaymentGateway)
    mock_gateway.refund_payment.return_value = (True, "Refund of $5.00 processed successfully")
    
    # Execute the function
    success, message = refund_late_fee_payment("txn_123456", 5.00, mock_gateway)
    
    # Assertions
    assert success is True
    assert "Refund" in message or "refund" in message
    
    # Verify mock was called exactly once with correct parameters
    mock_gateway.refund_payment.assert_called_once_with("txn_123456", 5.00)


def test_refund_late_fee_invalid_transaction_id_no_prefix(mocker):
    """
    Test rejection of transaction ID without 'txn_' prefix.
    
    Stubs Used: None
    
    Mocks Used:
    - PaymentGateway.refund_payment: Should NOT be called
    
    Verification:
    - Mock is never called for invalid transaction ID
    - Returns failure status immediately
    """
    # Mock payment gateway
    mock_gateway = Mock(spec=PaymentGateway)
    
    # Execute with invalid transaction ID (no "txn_" prefix)
    success, message = refund_late_fee_payment("invalid_123", 5.00, mock_gateway)
    
    # Assertions
    assert success is False
    assert "Invalid transaction ID" in message
    
    # CRITICAL: Verify refund was NEVER attempted
    mock_gateway.refund_payment.assert_not_called()


def test_refund_late_fee_empty_transaction_id(mocker):
    """
    Test rejection of empty transaction ID.
    
    Verification:
    - Refund gateway not called for empty transaction ID
    """
    # Mock payment gateway
    mock_gateway = Mock(spec=PaymentGateway)
    
    # Execute with empty transaction ID
    success, message = refund_late_fee_payment("", 5.00, mock_gateway)
    
    # Assertions
    assert success is False
    assert "Invalid transaction ID" in message
    
    # Verify no refund attempt
    mock_gateway.refund_payment.assert_not_called()


def test_refund_late_fee_negative_amount(mocker):
    """
    Test rejection of negative refund amount.
    
    Stubs Used: None
    
    Mocks Used:
    - PaymentGateway.refund_payment: Should NOT be called
    
    Verification:
    - Mock is never called for negative amount
    - Validation happens before gateway call
    """
    # Mock payment gateway
    mock_gateway = Mock(spec=PaymentGateway)
    
    # Execute with negative amount
    success, message = refund_late_fee_payment("txn_123456", -5.00, mock_gateway)
    
    # Assertions
    assert success is False
    assert "must be greater than 0" in message.lower() or "greater than 0" in message
    
    # CRITICAL: Verify refund was NEVER attempted
    mock_gateway.refund_payment.assert_not_called()


def test_refund_late_fee_zero_amount(mocker):
    """
    Test rejection of zero refund amount.
    
    Stubs Used: None
    
    Mocks Used:
    - PaymentGateway.refund_payment: Should NOT be called
    
    Verification:
    - Mock is never called for zero amount
    """
    # Mock payment gateway
    mock_gateway = Mock(spec=PaymentGateway)
    
    # Execute with zero amount
    success, message = refund_late_fee_payment("txn_123456", 0.00, mock_gateway)
    
    # Assertions
    assert success is False
    assert "must be greater than 0" in message.lower() or "greater than 0" in message
    
    # Verify no refund attempt
    mock_gateway.refund_payment.assert_not_called()


def test_refund_late_fee_exceeds_maximum(mocker):
    """
    Test rejection when refund amount exceeds $15.00 maximum.
    
    Stubs Used: None
    
    Mocks Used:
    - PaymentGateway.refund_payment: Should NOT be called
    
    Verification:
    - Mock is never called when amount exceeds limit
    - Validation prevents excessive refunds
    """
    # Mock payment gateway
    mock_gateway = Mock(spec=PaymentGateway)
    
    # Execute with amount exceeding maximum ($15.00)
    success, message = refund_late_fee_payment("txn_123456", 20.00, mock_gateway)
    
    # Assertions
    assert success is False
    assert "exceeds maximum" in message.lower() or "maximum" in message.lower()
    
    # CRITICAL: Verify refund was NEVER attempted
    mock_gateway.refund_payment.assert_not_called()


def test_refund_late_fee_exactly_maximum_allowed(mocker):
    """
    Test that exactly $15.00 refund is allowed (boundary test).
    
    Stubs Used: None
    
    Mocks Used:
    - PaymentGateway.refund_payment: Returns successful refund
    
    Verification:
    - Maximum amount of $15.00 is accepted and processed
    """
    # Mock payment gateway
    mock_gateway = Mock(spec=PaymentGateway)
    mock_gateway.refund_payment.return_value = (True, "Refund of $15.00 processed successfully")
    
    # Execute with exactly maximum amount
    success, message = refund_late_fee_payment("txn_123456", 15.00, mock_gateway)
    
    # Assertions
    assert success is True
    
    # Verify refund was processed
    mock_gateway.refund_payment.assert_called_once_with("txn_123456", 15.00)


def test_refund_late_fee_gateway_failure(mocker):
    """
    Test handling when payment gateway rejects the refund.
    
    Stubs Used: None
    
    Mocks Used:
    - PaymentGateway.refund_payment: Returns failure status
    
    Verification:
    - Gateway called but returns failure
    - Failure message propagated to user
    """
    # Mock payment gateway to return failure
    mock_gateway = Mock(spec=PaymentGateway)
    mock_gateway.refund_payment.return_value = (False, "Refund window expired")
    
    # Execute the function
    success, message = refund_late_fee_payment("txn_123456", 5.00, mock_gateway)
    
    # Assertions
    assert success is False
    assert "Refund failed" in message
    assert "Refund window expired" in message
    
    # Verify mock was called
    mock_gateway.refund_payment.assert_called_once()


def test_refund_late_fee_exception_handling(mocker):
    """
    Test exception handling when refund gateway raises error.
    
    Stubs Used: None
    
    Mocks Used:
    - PaymentGateway.refund_payment: Raises Exception
    
    Verification:
    - Exception caught and handled gracefully
    - Returns failure status with error message
    """
    # Mock payment gateway to raise exception
    mock_gateway = Mock(spec=PaymentGateway)
    mock_gateway.refund_payment.side_effect = Exception("Connection lost")
    
    # Execute the function
    success, message = refund_late_fee_payment("txn_123456", 5.00, mock_gateway)
    
    # Assertions
    assert success is False
    assert "error" in message.lower()
    assert "Connection lost" in message
    
    # Verify the mock was called (exception occurred during call)
    mock_gateway.refund_payment.assert_called_once()


def test_refund_late_fee_small_amount(mocker):
    """
    Test refund for small amount (boundary test).
    
    Verification:
    - Small amounts like $0.50 are processed correctly
    """
    # Mock payment gateway
    mock_gateway = Mock(spec=PaymentGateway)
    mock_gateway.refund_payment.return_value = (True, "Refund of $0.50 processed successfully")
    
    # Execute with small amount
    success, message = refund_late_fee_payment("txn_123456", 0.50, mock_gateway)
    
    # Assertions
    assert success is True
    
    # Verify refund was called with correct small amount
    mock_gateway.refund_payment.assert_called_once_with("txn_123456", 0.50)


# ============================================================================
# Additional Edge Case Tests
# ============================================================================

def test_pay_late_fees_with_decimal_fee_amount(mocker):
    """
    Test payment processing with decimal fee amount (e.g., $7.25).
    
    Verification:
    - Decimal amounts are handled correctly
    """
    # Stub database functions with decimal fee
    mocker.patch(
        'services.library_service.calculate_late_fee_for_book',
        return_value={
            'fee_amount': 7.25,
            'days_overdue': 5,
            'status': 'Overdue'
        }
    )
    
    mocker.patch(
        'services.library_service.get_book_by_id',
        return_value={
            'id': 5,
            'title': 'Decimal Fee Book',
            'author': 'Test Author',
            'isbn': '3333333333333'
        }
    )
    
    # Mock payment gateway
    mock_gateway = Mock(spec=PaymentGateway)
    mock_gateway.process_payment.return_value = (True, "txn_decimal", "Success")
    
    # Execute the function
    success, message, transaction_id = pay_late_fees("123456", 5, mock_gateway)
    
    # Assertions
    assert success is True
    
    # Verify payment gateway called with exact decimal amount
    mock_gateway.process_payment.assert_called_once_with(
        patron_id="123456",
        amount=7.25,
        description="Late fees for 'Decimal Fee Book'"
    )


def test_refund_late_fee_with_decimal_amount(mocker):
    """
    Test refund with decimal amount (e.g., $3.75).
    
    Verification:
    - Decimal refund amounts are processed correctly
    """
    # Mock payment gateway
    mock_gateway = Mock(spec=PaymentGateway)
    mock_gateway.refund_payment.return_value = (True, "Refund of $3.75 processed successfully")
    
    # Execute with decimal amount
    success, message = refund_late_fee_payment("txn_123456", 3.75, mock_gateway)
    
    # Assertions
    assert success is True
    
    # Verify correct decimal amount passed to gateway
    mock_gateway.refund_payment.assert_called_once_with("txn_123456", 3.75)