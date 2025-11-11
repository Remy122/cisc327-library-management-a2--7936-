import os
import sys

# Ensure project root (parent of "tests") is on sys.path - without this, this file is not found for some reason 
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

import pytest
from unittest.mock import Mock
from services.library_service import pay_late_fees, refund_late_fee_payment
from services.payment_service import PaymentGateway


#Tests for pay_late_fees() function

def test_pay_late_successful_payment(mocker):

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
    
    mock_gateway = Mock(spec=PaymentGateway)
    mock_gateway.process_payment.return_value = (True, "txn_123456", "Payment processed successfully")
    
    success, message, transaction_id = pay_late_fees("123456", 1, mock_gateway)
    
    assert success is True
    assert transaction_id == "txn_123456"
    assert "Payment successful" in message
    
   
    mock_gateway.process_payment.assert_called_once_with(
        patron_id="123456",
        amount=5.00,
        description="Late fees for 'Test Book'"
    )


def test_pay_late_fees_payment_declined(mocker):
 
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
    
    
    mock_gateway = Mock(spec=PaymentGateway)
    mock_gateway.process_payment.return_value = (False, None, "Insufficient funds")
    
    success, message, transaction_id = pay_late_fees("654321", 2, mock_gateway)
    
    
    assert success is False
    assert transaction_id is None
    assert "Payment failed" in message
    assert "Insufficient funds" in message
    
   
    mock_gateway.process_payment.assert_called_once()


def test_pay_late_fees_invalid_patron_id_mock_not_called(mocker):

    mock_gateway = Mock(spec=PaymentGateway)
    
   
    success, message, transaction_id = pay_late_fees("123", 1, mock_gateway)
    
   
    assert success is False
    assert "Invalid patron ID" in message
    assert transaction_id is None
    
    mock_gateway.process_payment.assert_not_called()


def test_pay_late_fees_invalid_patron_id_with_letters(mocker):
 
    mock_gateway = Mock(spec=PaymentGateway)
    
    success, message, transaction_id = pay_late_fees("12a456", 1, mock_gateway)
    
    assert success is False
    assert "Invalid patron ID" in message
    assert transaction_id is None
    
    mock_gateway.process_payment.assert_not_called()


def test_pay_late_fees_zero_late_fees_mock_not_called(mocker):

    mocker.patch(
        'services.library_service.calculate_late_fee_for_book',
        return_value={
            'fee_amount': 0.00,
            'days_overdue': 0,
            'status': 'Not overdue'
        }
    )
    
    
    mock_gateway = Mock(spec=PaymentGateway)
    
    
    success, message, transaction_id = pay_late_fees("123456", 1, mock_gateway)
    
   
    assert success is False
    assert "No late fees" in message
    assert transaction_id is None
    
    
    mock_gateway.process_payment.assert_not_called()


def test_pay_late_fees_network_error_exception_handling(mocker):

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
    
    
    mock_gateway = Mock(spec=PaymentGateway)
    mock_gateway.process_payment.side_effect = Exception("Network timeout")
    
   
    success, message, transaction_id = pay_late_fees("123456", 3, mock_gateway)
    
    
    assert success is False
    assert "error" in message.lower()
    assert "Network timeout" in message
    assert transaction_id is None
    
    mock_gateway.process_payment.assert_called_once()


def test_pay_late_fees_book_not_found(mocker):

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
        return_value=None
    )
    
   
    mock_gateway = Mock(spec=PaymentGateway)
    
    success, message, transaction_id = pay_late_fees("123456", 999, mock_gateway)
    

    assert success is False
    assert "Book not found" in message
    assert transaction_id is None
    
   
    mock_gateway.process_payment.assert_not_called()


def test_pay_late_fees_maximum_fee_amount(mocker):

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
    
   
    mock_gateway = Mock(spec=PaymentGateway)
    mock_gateway.process_payment.return_value = (True, "txn_max_fee", "Success")
    
   
    success, message, transaction_id = pay_late_fees("123456", 4, mock_gateway)
    
   
    assert success is True
    assert transaction_id == "txn_max_fee"
    
    mock_gateway.process_payment.assert_called_once_with(
        patron_id="123456",
        amount=15.00,
        description="Late fees for 'Maximum Fee Book'"
    )



#Tests for refund_late_fee_payment() function


def test_refund_late_fee_successful(mocker):

    mock_gateway = Mock(spec=PaymentGateway)
    mock_gateway.refund_payment.return_value = (True, "Refund of $5.00 processed successfully")
    
    
    success, message = refund_late_fee_payment("txn_123456", 5.00, mock_gateway)
    
    assert success is True
    assert "Refund" in message or "refund" in message
    
    mock_gateway.refund_payment.assert_called_once_with("txn_123456", 5.00)


def test_refund_late_fee_invalid_transaction_id_no_prefix(mocker):

    mock_gateway = Mock(spec=PaymentGateway)
    
   
    success, message = refund_late_fee_payment("invalid_123", 5.00, mock_gateway)
    
    assert success is False
    assert "Invalid transaction ID" in message
    
    mock_gateway.refund_payment.assert_not_called()


def test_refund_late_fee_empty_transaction_id(mocker):

    mock_gateway = Mock(spec=PaymentGateway)
    
    
    success, message = refund_late_fee_payment("", 5.00, mock_gateway)
    
    
    assert success is False
    assert "Invalid transaction ID" in message
    
    
    mock_gateway.refund_payment.assert_not_called()


def test_refund_late_fee_negative_amount(mocker):

    mock_gateway = Mock(spec=PaymentGateway)
    
    success, message = refund_late_fee_payment("txn_123456", -5.00, mock_gateway)
    
    assert success is False
    assert "must be greater than 0" in message.lower() or "greater than 0" in message
    
    mock_gateway.refund_payment.assert_not_called()


def test_refund_late_fee_zero_amount(mocker):

    mock_gateway = Mock(spec=PaymentGateway)
    
  
    success, message = refund_late_fee_payment("txn_123456", 0.00, mock_gateway)
    
    
    assert success is False
    assert "must be greater than 0" in message.lower() or "greater than 0" in message
   
    mock_gateway.refund_payment.assert_not_called()


def test_refund_late_fee_exceeds_maximum(mocker):

    mock_gateway = Mock(spec=PaymentGateway)
    
    success, message = refund_late_fee_payment("txn_123456", 20.00, mock_gateway)
    
    
    assert success is False
    assert "exceeds maximum" in message.lower() or "maximum" in message.lower()
    
    
    mock_gateway.refund_payment.assert_not_called()


def test_refund_late_fee_exactly_maximum_allowed(mocker):

    mock_gateway = Mock(spec=PaymentGateway)
    mock_gateway.refund_payment.return_value = (True, "Refund of $15.00 processed successfully")
    
    success, message = refund_late_fee_payment("txn_123456", 15.00, mock_gateway)
    
    assert success is True
    
    mock_gateway.refund_payment.assert_called_once_with("txn_123456", 15.00)


def test_refund_late_fee_gateway_failure(mocker):

    mock_gateway = Mock(spec=PaymentGateway)
    mock_gateway.refund_payment.return_value = (False, "Refund window expired")
    
    success, message = refund_late_fee_payment("txn_123456", 5.00, mock_gateway)
    
    assert success is False
    assert "Refund failed" in message
    assert "Refund window expired" in message
    
    mock_gateway.refund_payment.assert_called_once()


def test_refund_late_fee_exception_handling(mocker):

    mock_gateway = Mock(spec=PaymentGateway)
    mock_gateway.refund_payment.side_effect = Exception("Connection lost")
    
    success, message = refund_late_fee_payment("txn_123456", 5.00, mock_gateway)
    
    assert success is False
    assert "error" in message.lower()
    assert "Connection lost" in message
    
    mock_gateway.refund_payment.assert_called_once()


def test_refund_late_fee_small_amount(mocker):
    """
    Test refund for small amount (boundary test).
    
    Verification:
    - Small amounts like $0.50 are processed correctly
    """
    mock_gateway = Mock(spec=PaymentGateway)
    mock_gateway.refund_payment.return_value = (True, "Refund of $0.50 processed successfully")
    
    success, message = refund_late_fee_payment("txn_123456", 0.50, mock_gateway)
    
    assert success is True
    
    mock_gateway.refund_payment.assert_called_once_with("txn_123456", 0.50)

